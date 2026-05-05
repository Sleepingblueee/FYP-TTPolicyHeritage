"""
HTML → Markdown 正文提取 v2
修复 v1 的 bug:
1. BeautifulSoup 不再来回转
2. 异常不再静默吞掉，记到日志
3. method B 加导航过滤
4. method C 改进
5. NEWS 加专门的 method D (pageProps.post)
6. 承认死文件，明确放弃
"""

import json
import re
import traceback
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

REPORT_PATH = Path("data/processed/11_extraction_report_v2.csv")
ERROR_LOG_PATH = Path("data/processed/11_extraction_errors_v2.txt")

NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg", "img"]
NOISE_CLASS_KEYWORDS = ["nav", "header", "footer", "sidebar", "cookie", "banner",
                        "consent", "skip-link", "skiplink", "language-selector",
                        "region-selector", "wb-autocheck", "wm-"]

# 导航关键词（如果文本主要由这些词组成，认为是侧边栏）
NAV_PHRASES = [
    "Skip to main content", "Overview", "Community Principles",
    "Youth Safety", "Safety and Civility", "Mental and Behavioral Health",
    "Sensitive and Mature Themes", "Integrity and Authenticity",
    "Regulated Goods", "Privacy and Security", "For You feed",
    "Eligibility Standards", "Accounts and Features", "Enforcement",
]


def soup_to_markdown(element):
    """把 BeautifulSoup element 转成 Markdown 文本（不重新解析）"""
    if element is None:
        return ""
    
    # 直接对原 soup 改造，避免来回 str/parse
    # 删除噪音标签
    for tag in element.find_all(NOISE_TAGS):
        tag.decompose()
    
    # 按 class 删除噪音
    for elem in element.find_all(attrs={"class": True}):
        cls = " ".join(elem.get("class", [])).lower()
        if any(kw in cls for kw in NOISE_CLASS_KEYWORDS):
            elem.decompose()
    
    # 转换标题
    for level in range(1, 7):
        for h in element.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            h.string = f"\n\n{'#' * level} {text}\n\n"
            h.unwrap() if hasattr(h, 'unwrap') else None
    
    # 转换列表项
    for li in element.find_all("li"):
        text = li.get_text(strip=True)
        new = f"\n- {text}"
        li.replace_with(NavigableString(new))
    
    # 转换段落
    for p in element.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            p.replace_with(NavigableString(f"\n\n{text}\n\n"))
    
    text = element.get_text(separator=" ", strip=False)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def is_mostly_nav(text):
    """判断一段文本是不是主要由导航词组成"""
    if not text or len(text) < 200:
        return False
    nav_hits = sum(1 for phrase in NAV_PHRASES if phrase in text)
    # 如果命中 5 个以上导航词，且总长度不超过 6000，判为导航
    return nav_hits >= 5 and len(text) < 6000


def try_method_a(soup):
    """A: __NEXT_DATA__ 的 pageProps.content (政策页 SPA)"""
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
        inner_soup = BeautifulSoup(content, "lxml")
        return soup_to_markdown(inner_soup)
    return None


def try_method_d_news(soup):
    """D: NEWS 专用 - __NEXT_DATA__ 的 pageProps.post"""
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
        # 找 content / body / html 等可能的字段
        for key in ["content", "body", "html", "rawContent", "richText"]:
            v = post.get(key)
            if isinstance(v, str) and len(v) > 200:
                inner_soup = BeautifulSoup(v, "lxml")
                text = soup_to_markdown(inner_soup)
                # 加上 title
                title = post.get("title", "")
                if title:
                    text = f"# {title}\n\n{text}"
                return text
    return None


def try_method_b(soup):
    """B: 找 <main> / <article> 但要过滤导航"""
    for tag_name in ["article", "main"]:
        tag = soup.find(tag_name)
        if tag:
            text_quick = tag.get_text(strip=True)
            if len(text_quick) > 500 and not is_mostly_nav(text_quick):
                # 用 copy 避免污染原 soup
                copied = BeautifulSoup(str(tag), "lxml")
                return soup_to_markdown(copied)
    return None


def try_method_c(soup):
    """C: body 里去除噪音后提取"""
    body = soup.find("body")
    if not body:
        return None
    
    # copy 一份避免污染
    body_copy = BeautifulSoup(str(body), "lxml")
    text = soup_to_markdown(body_copy)
    
    # 如果提取出来主要是导航，跳过
    if is_mostly_nav(text):
        return None
    
    if len(text) < 500:
        return None
    
    return text


def extract_one(filepath, is_news=False):
    """提取单个文件，返回 (text, method)；method 在 [A, B, C, D, FAILED, ERROR_xxx]"""
    try:
        html = filepath.read_text(encoding="utf-8", errors="ignore")
        if len(html.strip()) < 200:
            return None, "EMPTY_FILE"
        
        soup = BeautifulSoup(html, "lxml")
        
        # NEWS 优先用 D 方案
        if is_news:
            text = try_method_d_news(soup)
            if text:
                return text, "D_news_post"
        
        # 其他文档用 A → B → C 顺序
        text = try_method_a(soup)
        if text:
            return text, "A_next_data"
        
        text = try_method_b(soup)
        if text:
            return text, "B_semantic"
        
        text = try_method_c(soup)
        if text:
            return text, "C_body"
        
        # NEWS 兜底用 B、C
        if is_news:
            text = try_method_b(soup)
            if text:
                return text, "B_semantic"
            text = try_method_c(soup)
            if text:
                return text, "C_body"
        
        return None, "FAILED_no_content"
    
    except Exception as e:
        sig = f"ERROR_{type(e).__name__}"
        return None, sig


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
    print("第三步：HTML → Markdown 提取 v2")
    
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
    
    # 报告
    df = pd.DataFrame(all_records)
    df.to_csv(REPORT_PATH, index=False, encoding="utf-8-sig")
    
    if all_errors:
        ERROR_LOG_PATH.write_text("\n".join(all_errors), encoding="utf-8")
    
    print(f"\n{'='*60}")
    print("总报告")
    print(f"{'='*60}")
    
    print(f"\n按方法分布:")
    print(df["method"].value_counts().to_string())
    
    print(f"\n按 [类别 × 方法]:")
    pivot = df.groupby(["category", "method"]).size().unstack(fill_value=0)
    print(pivot.to_string())
    
    success = df[df["extracted_chars"] > 0]
    print(f"\n成功率: {len(success)}/{len(df)} ({len(success)/len(df)*100:.1f}%)")
    
    if len(success) > 0:
        print(f"\n提取字数分布（仅成功项）:")
        print(f"  平均: {success['extracted_chars'].mean():.0f}")
        print(f"  中位数: {success['extracted_chars'].median():.0f}")
        print(f"  最小: {success['extracted_chars'].min()}")
        print(f"  最大: {success['extracted_chars'].max()}")
        print(f"  <500 字符（可疑）: {(success['extracted_chars'] < 500).sum()}")
        print(f"  500-1500 字符: {((success['extracted_chars'] >= 500) & (success['extracted_chars'] < 1500)).sum()}")
        print(f"  >=1500 字符（合格）: {(success['extracted_chars'] >= 1500).sum()}")
    
    print(f"\n报告: {REPORT_PATH}")
    if all_errors:
        print(f"失败列表: {ERROR_LOG_PATH}")


if __name__ == "__main__":
    main()