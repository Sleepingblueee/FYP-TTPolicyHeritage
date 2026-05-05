"""
HTML → Markdown 提取 v3
关键改进:
1. 加一条新规则: class="article-wrapper" 是 TikTok 政策正文的精确标记
   解决 348 个 FAILED CG 文件
2. 重写 markdown 转换核心函数，使用 .extract() 而非 .replace_with(NavigableString)
   解决 324 个 AttributeError
3. method 顺序调整: A → article_wrapper → B → C → D(news)
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

REPORT_PATH = Path("data/processed/11_extraction_report_v3.csv")
ERROR_LOG_PATH = Path("data/processed/11_extraction_errors_v3.txt")

NOISE_TAGS = ["script", "style", "nav", "footer", "header",
              "noscript", "iframe", "svg", "img", "aside"]
NOISE_CLASS_KEYWORDS = ["nav", "header", "footer", "sidebar", "cookie", "banner",
                        "consent", "skip-link", "skiplink", "language-selector",
                        "region-selector", "wb-autocheck", "wm-",
                        "side-list", "breadcrumb"]


def fresh_soup_from_element(element):
    """把 element 复制到一份新的、干净的 BeautifulSoup 树"""
    return BeautifulSoup(str(element), "lxml")


def remove_noise(soup):
    """从 soup 里删除噪音标签和噪音 class 元素"""
    # 删除噪音标签
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    
    # 按 class 关键词删除
    for elem in list(soup.find_all(attrs={"class": True})):
        if elem.parent is None:  # 已被 decompose 跳过
            continue
        cls = " ".join(elem.get("class", [])).lower()
        if any(kw in cls for kw in NOISE_CLASS_KEYWORDS):
            elem.decompose()


def soup_to_markdown(element):
    """把 soup element 转成 Markdown，使用安全的实现方式"""
    if element is None:
        return ""
    
    # 用一份独立的 soup 副本操作，避免污染原树
    soup = fresh_soup_from_element(element)
    remove_noise(soup)
    
    # 处理标题：在标题前后插入 markdown 标记
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            # 在标签前插入文本节点，用 insert_before 而非 replace_with
            text = h.get_text(strip=True)
            if text:
                h.insert_before(NavigableString(f"\n\n{'#' * level} {text}\n\n"))
                h.decompose()
    
    # 处理列表项
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        if text:
            li.insert_before(NavigableString(f"\n- {text}"))
            li.decompose()
    
    # 处理段落 - 不再修改 DOM，直接在最后做文本处理
    # 处理加粗
    for tag in soup.find_all(["b", "strong"]):
        text = tag.get_text(strip=True)
        if text:
            tag.insert_before(NavigableString(f"**{text}**"))
            tag.decompose()
    
    # 提取最终文本
    text = soup.get_text(separator=" ", strip=False)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def try_method_article_wrapper(soup):
    """新方法: 找 class="article-wrapper" 的 div，这是 TikTok 政策正文的精确标记"""
    wrappers = soup.find_all("div", class_=re.compile(r"article-wrapper"))
    for w in wrappers:
        text_quick = w.get_text(strip=True)
        if len(text_quick) > 500:
            return soup_to_markdown(w)
    return None


def try_method_a_nextdata(soup):
    """A: __NEXT_DATA__.pageProps.content"""
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
    """D: NEWS - __NEXT_DATA__.pageProps.post"""
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


def try_method_b_semantic(soup):
    """B: <article> / <main>"""
    for tag_name in ["article", "main"]:
        tag = soup.find(tag_name)
        if tag:
            text_quick = tag.get_text(strip=True)
            if len(text_quick) > 500:
                return soup_to_markdown(tag)
    return None


def try_method_c_body(soup):
    """C: <body> 兜底"""
    body = soup.find("body")
    if not body:
        return None
    text = soup_to_markdown(body)
    if len(text) < 500:
        return None
    return text


def extract_one(filepath, is_news=False):
    """提取一个文件，返回 (text, method)"""
    try:
        html = filepath.read_text(encoding="utf-8", errors="ignore")
        if len(html.strip()) < 200:
            return None, "EMPTY_FILE"
        
        soup = BeautifulSoup(html, "lxml")
        
        # NEWS 优先 D
        if is_news:
            text = try_method_d_news(soup)
            if text:
                return text, "D_news_post"
        
        # 优先级: article-wrapper > A > B > C
        text = try_method_article_wrapper(soup)
        if text:
            return text, "AW_article_wrapper"
        
        text = try_method_a_nextdata(soup)
        if text:
            return text, "A_next_data"
        
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
    print("第三步：HTML → Markdown 提取 v3")
    
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
    print("总报告 v3")
    print(f"{'='*60}")
    
    print(f"\n按方法分布:")
    print(df["method"].value_counts().to_string())
    
    print(f"\n按 [类别 × 方法]:")
    pivot = df.groupby(["category", "method"]).size().unstack(fill_value=0)
    print(pivot.to_string())
    
    success = df[df["extracted_chars"] > 0]
    print(f"\n成功率: {len(success)}/{len(df)} ({len(success)/len(df)*100:.1f}%)")
    
    if len(success) > 0:
        print(f"\n提取字数分布（成功项）:")
        print(f"  平均: {success['extracted_chars'].mean():.0f}")
        print(f"  中位数: {success['extracted_chars'].median():.0f}")
        print(f"  最小: {success['extracted_chars'].min()}")
        print(f"  最大: {success['extracted_chars'].max()}")
        print(f"  <500: {(success['extracted_chars'] < 500).sum()}")
        print(f"  500-1500: {((success['extracted_chars'] >= 500) & (success['extracted_chars'] < 1500)).sum()}")
        print(f"  >=1500: {(success['extracted_chars'] >= 1500).sum()}")


if __name__ == "__main__":
    main()