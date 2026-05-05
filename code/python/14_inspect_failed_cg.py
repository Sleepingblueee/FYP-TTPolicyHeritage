"""
专门看那 348 个 FAILED 的 CG 文件到底是什么结构
"""

import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

REPORT = Path("data/processed/11_extraction_report_v3.csv")
RAW_MAIN = Path("data/raw/main")

df = pd.read_csv(REPORT)
failed_cg = df[(df["category"] == "CG") & (df["method"] == "FAILED_no_content")]
print(f"FAILED CG 文件数: {len(failed_cg)}")
print(f"按年份分布:")
print(failed_cg["year"].value_counts().sort_index().to_string())

# 抽样 5 个不同年份的看看
samples = failed_cg.groupby("year").head(2)
print(f"\n抽样 {len(samples)} 个文件...")

for _, row in samples.iterrows():
    f = RAW_MAIN / row["filename"]
    if not f.exists():
        continue
    
    print(f"\n{'='*70}")
    print(f"文件: {row['filename']} ({row['html_size_kb']:.1f} KB) | 年份 {row['year']}")
    print(f"{'='*70}")
    
    html = f.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    
    # 1. article-wrapper
    aw = soup.find_all("div", class_=lambda c: c and "article-wrapper" in " ".join(c) if isinstance(c, list) else False)
    print(f"  article-wrapper: {len(aw)} 个")
    
    # 2. <main>
    m = soup.find("main")
    if m:
        print(f"  <main>: 文本 {len(m.get_text(strip=True))} 字符")
        print(f"    main 直接子元素:")
        for child in m.find_all(recursive=False)[:5]:
            cls = child.get("class", [])
            print(f"      <{child.name}> class={cls} text_len={len(child.get_text(strip=True))}")
    else:
        print(f"  <main>: 无")
    
    # 3. <article>
    a = soup.find("article")
    if a:
        print(f"  <article>: 文本 {len(a.get_text(strip=True))} 字符")
    
    # 4. <body>
    b = soup.find("body")
    if b:
        print(f"  <body>: 文本 {len(b.get_text(strip=True))} 字符")
        # 看 body 直接子元素
        print(f"    body 直接子元素 (前 6 个):")
        for child in b.find_all(recursive=False)[:6]:
            cls = child.get("class", [])
            print(f"      <{child.name}> class={cls} text_len={len(child.get_text(strip=True))}")
    
    # 5. 找最大文本块（>500 字符）
    print(f"\n  最大的几个有文本的 div:")
    divs = []
    for d in soup.find_all("div"):
        text_len = len(d.get_text(strip=True))
        if text_len > 500:
            cls = d.get("class", [])
            divs.append((text_len, cls, d.get("id", ""), d.get("role", "")))
    divs.sort(reverse=True)
    for t, c, i, r in divs[:5]:
        print(f"    text_len={t} class={c} id='{i}' role='{r}'")