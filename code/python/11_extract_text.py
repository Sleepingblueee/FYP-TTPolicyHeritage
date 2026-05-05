"""
第三步第二小步：HTML → Markdown 正文提取
针对 TikTok 政策页面的 3 种架构分别处理:
  架构 A: __NEXT_DATA__ 里的 pageProps.content (Next.js SPA)
  架构 B: <main> / <article> 标签 (语义化 SSR)
  架构 C: 直接 <body> 提取（去除 nav/footer 噪音）

输出:
  data/processed/extracted/main/*.md
  data/processed/extracted/news/*.md
  data/processed/11_extraction_report.csv  (每个文件的提取详情)
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

RAW_MAIN = Path("data/raw/main")
RAW_NEWS = Path("data/raw/news")
EXTRACT_MAIN = Path("data/processed/extracted/main")
EXTRACT_NEWS = Path("data/processed/extracted/news")
EXTRACT_MAIN.mkdir(parents=True, exist_ok=True)
EXTRACT_NEWS.mkdir(parents=True, exist_ok=True)

REPORT_PATH = Path("data/processed/11_extraction_report.csv")

# 噪音标签 - 这些标签的内容会被全部去除
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "iframe"]

# 噪音类名/id 的关键词（出现这些字样的元素会被去除）
NOISE_SELECTORS = [
    "nav", "navigation", "header", "footer", "sidebar",
    "cookie", "banner", "consent", "promo",
    "skip-link", "skip-to", "skiplink",
    "language-selector", "region-selector",
    "wb-autocheck", "wm-",  # Wayback Machine 注入
]


def remove_noise(soup):
    """从 soup 里去掉噪音元素"""
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    
    # 按 class 和 id 去除
    for elem in soup.find_all(attrs={"class": True}):
        cls = " ".join(elem.get("class", [])).lower()
        if any(kw in cls for kw in NOISE_SELECTORS):
            elem.decompose()
    
    for elem in soup.find_all(attrs={"id": True}):
        eid = elem.get("id", "").lower()
        if any(kw in eid for kw in NOISE_SELECTORS):
            elem.decompose()
    
    return soup


def html_to_markdown(html_string):
    """
    把一段 HTML 转成 Markdown 风格的纯文本
    保留标题层级、列表、加粗
    """
    soup = BeautifulSoup(html_string, "lxml")
    soup = remove_noise(soup)
    
    # 转换标题
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            prefix = "#" * level
            h.replace_with(f"\n\n{prefix} {h.get_text(strip=True)}\n\n")
    
    # 转换列表
    for ul in soup.find_all(["ul", "ol"]):
        items = []
        for li in ul.find_all("li", recursive=False):
            items.append(f"- {li.get_text(strip=True)}")
        ul.replace_with("\n" + "\n".join(items) + "\n")
    
    # 转换加粗
    for tag in soup.find_all(["b", "strong"]):
        tag.replace_with(f"**{tag.get_text(strip=True)}**")
    
    # 转换段落（每个 p 后加换行）
    for p in soup.find_all("p"):
        p.append("\n\n")
    
    text = soup.get_text(separator=" ", strip=False)
    
    # 清理多余空白
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    
    return text


def try_method_a(soup):
    """架构 A: 从 __NEXT_DATA__ 提取 pageProps.content"""
    next_data = soup.find("script", id="__NEXT_DATA__")
    if not next_data or not next_data.string:
        return None
    
    try:
        data = json.loads(next_data.string)
    except Exception:
        return None
    
    page_props = data.get("props", {}).get("pageProps", {})
    
    # 直接的 content 字段
    content = page_props.get("content")
    if isinstance(content, str) and len(content) > 500:
        # content 通常是 HTML 字符串，转成 Markdown
        return html_to_markdown(content)
    
    # 嵌套字段：尝试从 webapp、page 等字段提取
    for key in ["webapp", "page", "data", "article"]:
        nested = page_props.get(key)
        if isinstance(nested, dict):
            for k, v in nested.items():
                if isinstance(v, str) and len(v) > 1000:
                    return html_to_markdown(v)
    
    return None


def try_method_b(soup):
    """架构 B: 找 <main> 或 <article>"""
    for tag_name in ["article", "main"]:
        tag = soup.find(tag_name)
        if tag and len(tag.get_text(strip=True)) > 500:
            return html_to_markdown(str(tag))
    return None


def try_method_c(soup):
    """架构 C: 直接从 <body> 提取，去除噪音"""
    body = soup.find("body")
    if not body:
        return None
    
    body_copy = BeautifulSoup(str(body), "lxml")
    body_copy = remove_noise(body_copy)
    
    text = html_to_markdown(str(body_copy))
    if len(text) > 500:
        return text
    return None


def extract_one(filepath):
    """提取单个 HTML，返回 (text, method, length)"""
    html = filepath.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    
    # 按优先级尝试
    text = try_method_a(soup)
    if text:
        return text, "A_next_data", len(text)
    
    text = try_method_b(soup)
    if text:
        return text, "B_semantic", len(text)
    
    text = try_method_c(soup)
    if text:
        return text, "C_body", len(text)
    
    return None, "FAILED", 0


def process_directory(input_dir, output_dir, name):
    print(f"\n{'='*60}")
    print(f"处理 {name}: {input_dir} → {output_dir}")
    print(f"{'='*60}")
    
    files = sorted(input_dir.glob("*.html"))
    print(f"待处理: {len(files)} 个文件")
    
    records = []
    method_count = {"A_next_data": 0, "B_semantic": 0, "C_body": 0, "FAILED": 0}
    
    for f in tqdm(files, desc=name):
        try:
            text, method, length = extract_one(f)
            method_count[method] += 1
            
            if text:
                # 保存 Markdown 文件
                out_path = output_dir / (f.stem + ".md")
                out_path.write_text(text, encoding="utf-8")
            
            records.append({
                "filename": f.name,
                "category": f.name.split("_")[0],
                "timestamp": f.name.split("_")[1],
                "year": f.name.split("_")[1][:4],
                "method": method,
                "html_size_kb": f.stat().st_size / 1024,
                "extracted_chars": length,
                "output_file": (f.stem + ".md") if text else "",
            })
        except Exception as e:
            print(f"\n  错误处理 {f.name}: {e}")
            records.append({
                "filename": f.name,
                "category": f.name.split("_")[0],
                "timestamp": f.name.split("_")[1],
                "year": f.name.split("_")[1][:4],
                "method": "ERROR",
                "html_size_kb": f.stat().st_size / 1024,
                "extracted_chars": 0,
                "output_file": "",
            })
    
    print(f"\n方法分布:")
    for m, c in method_count.items():
        print(f"  {m}: {c}")
    
    return records


def main():
    print("第三步：HTML → Markdown 正文提取")
    
    all_records = []
    all_records.extend(process_directory(RAW_MAIN, EXTRACT_MAIN, "主样本"))
    all_records.extend(process_directory(RAW_NEWS, EXTRACT_NEWS, "NEWS 辅助"))
    
    df = pd.DataFrame(all_records)
    df.to_csv(REPORT_PATH, index=False, encoding="utf-8-sig")
    
    print(f"\n{'='*60}")
    print("总报告")
    print(f"{'='*60}")
    print(f"\n按方法分布:")
    print(df["method"].value_counts().to_string())
    
    print(f"\n按类别 × 方法:")
    pivot = df.groupby(["category", "method"]).size().unstack(fill_value=0)
    print(pivot.to_string())
    
    print(f"\n提取字数分布:")
    success = df[df["method"] != "FAILED"]
    if len(success) > 0:
        print(f"  平均: {success['extracted_chars'].mean():.0f}")
        print(f"  中位数: {success['extracted_chars'].median():.0f}")
        print(f"  最小: {success['extracted_chars'].min()}")
        print(f"  最大: {success['extracted_chars'].max()}")
        print(f"  <500 字符（可疑）: {(success['extracted_chars'] < 500).sum()}")
        print(f"  <1500 字符: {(success['extracted_chars'] < 1500).sum()}")
    
    print(f"\n报告保存: {REPORT_PATH}")
    print(f"提取文件: {EXTRACT_MAIN} 和 {EXTRACT_NEWS}")


if __name__ == "__main__":
    main()