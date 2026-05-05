"""看 v5 还剩 154 个 FAILED 的 CG 是啥"""
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

REPORT = Path("data/processed/11_extraction_report_v5.csv")
RAW = Path("data/raw/main")
df = pd.read_csv(REPORT)
failed = df[(df["category"] == "CG") & (df["method"] == "FAILED_no_content")]
print(f"剩余 FAILED CG: {len(failed)}")
print(f"\n按年份:")
print(failed["year"].value_counts().sort_index())

# 抽样 5 个看
samples = failed.head(5)
for _, row in samples.iterrows():
    f = RAW / row["filename"]
    if not f.exists():
        continue
    print(f"\n{'='*70}")
    print(f"{row['filename']} ({row['html_size_kb']:.0f} KB)")
    print(f"{'='*70}")
    
    html = f.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    if body:
        body_text = body.get_text(strip=True)
        print(f"body 文本长度: {len(body_text)}")
        print(f"body 前 200 字符: {body_text[:200]}")
    
    # 看几种结构是不是真的不在
    import re
    aw = soup.find_all("div", class_=re.compile(r"article-wrapper"))
    mb = soup.find_all("div", class_=re.compile(r"main-body|tiktok-web-article|main-content"))
    nd = soup.find("script", id="__NEXT_DATA__")
    main_tag = soup.find("main")
    
    print(f"  article-wrapper div: {len(aw)}")
    print(f"  main-body div: {len(mb)}")
    print(f"  __NEXT_DATA__: {'有' if nd else '无'}")
    print(f"  <main>: {'有' if main_tag else '无'}", end="")
    if main_tag:
        print(f" 文本 {len(main_tag.get_text(strip=True))} 字符")
    else:
        print()