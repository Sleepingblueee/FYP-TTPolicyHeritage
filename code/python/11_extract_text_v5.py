"""
HTML → Markdown 提取 v5
最终修复:
- 大幅收窄噪音 class 过滤范围，只保留 100% 确定是噪音的 class 名
- 不再用通用模式（-header$ 等）误删正文 div
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
import pandas as pd
from tqdm import tqdm

RAW_MAIN = Path("data/raw/main")
RAW_NEWS = Path("data/raw/news")
EXTRACT_MAIN = Path("data/processed/extracted/main")
EXTRACT_NEWS = Path("data/processed/extracted/news")
EXTRACT_MAIN.mkdir(parents=True, exist_ok=True)
EXTRACT_NEWS.mkdir(parents=True, exist_ok=True)

REPORT_PATH = Path("data/processed/11_extraction_report_v5.csv")
ERROR_LOG_PATH = Path("data/processed/11_extraction_errors_v5.txt")

# 噪音标签：直接删（HTML5 语义化标签，含义明确）
NOISE_TAGS = ["script", "style", "nav", "footer", "header",
              "noscript", "iframe", "svg", "img", "aside"]

# 噪音 class：只保留 100% 确定的，宁可漏删也不误删
# 每条都是完整词级别的精确匹配
NOISE_CLASS_EXACT = {
    "cookie-banner", "cookie-consent", "cookie-notice",
    "skip-link", "skiplink", "skip-to-content",
    "language-selector", "region-selector",
    "wb-autocheck", "side-list-container",
    "breadcrumb", "breadcrumbs",
    "header-container", "footer-container",
    "site-header", "site-footer",
}

# CSR-only 检测
CSR_NAV_PHRASES = [
    "Skip to main content", "Community Principles", "Youth Safety",
    "Safety and Civility", "Mental and Behavioral Health",
    "Sensitive and Mature Themes", "Integrity and Authenticity",
    "Regulated Goods", "Privacy and Security", "For You feed",
    "Eligibility Standards", "Accounts and Features",
]


def is_csr_only(html, soup):
    body = soup.find("body")
    if not body:
        return False
    body_text = body.get_text(strip=True)
    if len(body_text) > 6500:
        return False
    nav_hits = sum(1 for p in CSR_NAV_PHRASES if p in body_text)
    if nav_hits < 5:
        return False
    has_big_js = any(
        s.string and len(s.string) > 100000
        for s in soup.find_all("script")
    )
    return has_big_js


def remove_noise(soup):
    """温和地删除噪音"""
    # 1. 删除噪音标签
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    
    # 2. 删除明确噪音 class（精确匹配每个 class 名）
    for elem in list(soup.find_all(attrs={"class": True})):
        if elem.parent is None:
            continue
        cls_set = set(elem.get("class", []))
        if cls_set & NOISE_CLASS_EXACT:
            elem.decompose()


def fresh_soup_from_element(element):
    return BeautifulSoup(str(element), "lxml")


def soup_to_markdown(element):
    if element is None:
        return ""
    soup = fresh_soup_from_element(element)
    remove_noise(soup)
    
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            if text:
                h.insert_before(NavigableString(f"\n\n{'#' * level} {text}\n\n"))
                h.decompose()
    
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        if text:
            li.insert_before(NavigableString(f"\n- {text}"))
            li.decompose()
    
    for tag in soup.find_all(["b", "strong"]):
        text = tag.get_text(strip=True)
        if text:
            tag.insert_before(NavigableString(f"**{text}**"))
            tag.decompose()
    
    text = soup.get_text(separator=" ", strip=False)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def try_method_a_nextdata(soup):
    nd = soup.find("script", id="__NEXT_DATA__")
    if not nd or not nd.string:
        return None
    try:
        data = json.loads(nd.string)
    except json.JSONDecodeError:
        return None
    pp = data.get("props", {}).get("pageProps", {})
    content = pp.get("content")
    if isinstance(content, str) and len(content) > 500:
        inner = BeautifulSoup(content, "lxml")
        return soup_to_markdown(inner)
    return None


def try_method_d_news(soup):
    nd = soup.find("script", id="__NEXT_DATA__")
    if not nd or not nd.string:
        return None
    try:
        data = json.loads(nd.string)
    except json.JSONDecodeError:
        return None
    pp = data.get("props", {}).get("pageProps", {})
    post = pp.get("post")
    if isinstance(post, dict):
        for key in ["content", "body", "html", "rawContent", "richText"]:
            v = post.get(key)
            if isinstance(v, str) and len(v) > 200:
                inner = BeautifulSoup(v, "lxml")
                text = soup_to_markdown(inner)
                title = post.get("title", "")
                if title:
                    text = f"# {title}\n\n{text}"
                return text
    return None


def try_method_article_wrapper(soup):
    wrappers = soup.find_all("div", class_=re.compile(r"article-wrapper"))
    for w in wrappers:
        if len(w.get_text(strip=True)) > 500:
            return soup_to_markdown(w)
    return None


def try_method_main_body(soup):
    candidates = soup.find_all(
        "div",
        class_=re.compile(r"(main-body|tiktok-web-article|main-content)"),
    )
    for c in candidates:
        if len(c.get_text(strip=True)) > 500:
            return soup_to_markdown(c)
    return None


def try_method_b_semantic(soup):
    for tag_name in ["article", "main"]:
        tag = soup.find(tag_name)
        if tag and len(tag.get_text(strip=True)) > 500:
            return soup_to_markdown(tag)
    return None


def try_method_c_body(soup):
    body = soup.find("body")
    if not body:
        return None
    text = soup_to_markdown(body)
    if len(text) < 500:
        return None
    return text


def extract_one(filepath, is_news=False):
    try:
        html = filepath.read_text(encoding="utf-8", errors="ignore")
        if len(html.strip()) < 200:
            return None, "EMPTY_FILE"
        
        soup = BeautifulSoup(html, "lxml")
        
        if is_csr_only(html, soup):
            return None, "CSR_NO_CONTENT"
        
        if is_news:
            text = try_method_d_news(soup)
            if text:
                return text, "D_news_post"
        
        text = try_method_a_nextdata(soup)
        if text:
            return text, "A_next_data"
        
        text = try_method_article_wrapper(soup)
        if text:
            return text, "AW_article_wrapper"
        
        text = try_method_main_body(soup)
        if text:
            return text, "MB_main_body"
        
        text = try_method_b_semantic(soup)
        if text:
            return text, "B_semantic"
        
        text = try_method_c_body(soup)
        if text:
            return text, "C_body"
        
        return None, "FAILED_no_content"
    
    except Exception as e:
        return None, f"ERROR_{type(e).__name__}"


def process_directory(input_dir, output_dir, name, is_news=False):
    print(f"\n{'='*60}")
    print(f"处理 {name}: {input_dir}")
    print(f"{'='*60}")
    
    files = sorted(input_dir.glob("*.html"))
    print(f"待处理: {len(files)} 个文件")
    
    records = []
    error_lines = []
    
    for f in tqdm(files, desc=name):
        text, method = extract_one(f, is_news=is_news)
        
        if text:
            out_path = output_dir / (f.stem + ".md")
            out_path.write_text(text, encoding="utf-8")
            length = len(text)
            out_file = f.stem + ".md"
        else:
            length = 0
            out_file = ""
            error_lines.append(f"[{method}] {f.name}")
        
        records.append({
            "filename": f.name,
            "category": f.name.split("_")[0],
            "timestamp": f.name.split("_")[1],
            "year": f.name.split("_")[1][:4],
            "method": method,
            "html_size_kb": f.stat().st_size / 1024,
            "extracted_chars": length,
            "output_file": out_file,
        })
    
    return records, error_lines


def main():
    print("第三步：HTML → Markdown 提取 v5（最终版）")
    
    all_records = []
    all_errors = []
    
    main_records, main_errors = process_directory(
        RAW_MAIN, EXTRACT_MAIN, "主样本", is_news=False
    )
    all_records.extend(main_records)
    all_errors.extend(main_errors)
    
    news_records, news_errors = process_directory(
        RAW_NEWS, EXTRACT_NEWS, "NEWS", is_news=True
    )
    all_records.extend(news_records)
    all_errors.extend(news_errors)
    
    df = pd.DataFrame(all_records)
    df.to_csv(REPORT_PATH, index=False, encoding="utf-8-sig")
    
    if all_errors:
        ERROR_LOG_PATH.write_text("\n".join(all_errors), encoding="utf-8")
    
    print(f"\n{'='*60}")
    print("总报告 v5")
    print(f"{'='*60}")
    
    print(f"\n按方法分布:")
    print(df["method"].value_counts().to_string())
    
    print(f"\n按 [类别 × 方法]:")
    pivot = df.groupby(["category", "method"]).size().unstack(fill_value=0)
    print(pivot.to_string())
    
    success = df[df["extracted_chars"] > 0]
    csr_only = df[df["method"] == "CSR_NO_CONTENT"]
    other_failed = df[(df["extracted_chars"] == 0) & (df["method"] != "CSR_NO_CONTENT")]
    
    print(f"\n样本最终状态:")
    print(f"  成功提取: {len(success)} ({len(success)/len(df)*100:.1f}%)")
    print(f"  CSR 无正文 (研究发现): {len(csr_only)} ({len(csr_only)/len(df)*100:.1f}%)")
    print(f"  其他失败: {len(other_failed)} ({len(other_failed)/len(df)*100:.1f}%)")
    
    if len(success) > 0:
        print(f"\n提取字数分布（成功项）:")
        print(f"  平均: {success['extracted_chars'].mean():.0f}")
        print(f"  中位数: {success['extracted_chars'].median():.0f}")
        print(f"  最小: {success['extracted_chars'].min()}")
        print(f"  最大: {success['extracted_chars'].max()}")
        print(f"  >=1500 字符（合格）: {(success['extracted_chars'] >= 1500).sum()}")


if __name__ == "__main__":
    main()