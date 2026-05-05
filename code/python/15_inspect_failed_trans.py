"""看 TRANS 失败文件的真实情况"""
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

REPORT = Path("data/processed/11_extraction_report_v3.csv")
RAW = Path("data/raw/main")
df = pd.read_csv(REPORT)
trans = df[(df["category"] == "TRANS") & (df["method"] == "FAILED_no_content")].head(3)

for _, row in trans.iterrows():
    f = RAW / row["filename"]
    if not f.exists():
        continue
    print(f"\n{'='*60}")
    print(f"{row['filename']} ({row['html_size_kb']:.0f} KB)")
    print(f"{'='*60}")
    
    html = f.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    
    body = soup.find("body")
    if body:
        body_text = body.get_text(separator=' ', strip=True)
        print(f"body 文本长度: {len(body_text)}")
        print(f"body 前 500 字符:")
        print(body_text[:500])
    
    # 看 article 的 11 字符那个
    art = soup.find("article")
    if art:
        print(f"\n<article>: {len(art.get_text(strip=True))} 字符")