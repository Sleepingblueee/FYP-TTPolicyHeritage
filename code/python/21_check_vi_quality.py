"""
扫描 VI 类（以及全部类）的提取质量
找出乱码、奇怪字符、异常文件
"""

import re
from pathlib import Path
import pandas as pd

EXTRACT_MAIN = Path("data/processed/extracted/main")
REPORT = Path("data/processed/11_extraction_report_v6.csv")

df = pd.read_csv(REPORT)
success = df[df["extracted_chars"] > 0].copy()

results = []
for _, row in success.iterrows():
    p = EXTRACT_MAIN / row["output_file"]
    if not p.exists():
        continue
    
    text = p.read_text(encoding="utf-8")
    
    # 计算几个质量指标
    total = len(text)
    if total == 0:
        continue
    
    # ASCII 占比（英文政策应该 > 95%）
    ascii_count = sum(1 for c in text if ord(c) < 128)
    ascii_ratio = ascii_count / total
    
    # 字母+常用标点占比
    alpha_punct = sum(1 for c in text if c.isalnum() or c in " .,;:!?'\"-()[]\n\t/")
    alpha_ratio = alpha_punct / total
    
    # 检测连续乱码：连续 10+ 个非字母非空格字符
    weird_runs = len(re.findall(r"[^\w\s.,;:!?'\"\-()\[\]/]{10,}", text))
    
    # 看是不是含有典型政策关键词
    policy_keywords = ["TikTok", "Community", "Policy", "Terms", "Guidelines", "users", "we", "platform"]
    keyword_hits = sum(1 for kw in policy_keywords if kw in text)
    
    results.append({
        "category": row["category"],
        "filename": row["output_file"],
        "length": total,
        "ascii_ratio": ascii_ratio,
        "alpha_ratio": alpha_ratio,
        "weird_runs": weird_runs,
        "keyword_hits": keyword_hits,
    })

rdf = pd.DataFrame(results)

print("=" * 70)
print("各类别质量统计")
print("=" * 70)
for cat, group in rdf.groupby("category"):
    print(f"\n[{cat}] 共 {len(group)} 个文件")
    print(f"  ASCII 占比: 平均 {group['ascii_ratio'].mean()*100:.1f}%, 最低 {group['ascii_ratio'].min()*100:.1f}%")
    print(f"  字母+标点占比: 平均 {group['alpha_ratio'].mean()*100:.1f}%, 最低 {group['alpha_ratio'].min()*100:.1f}%")
    print(f"  乱码段数 (连续10+异常字符): 总 {group['weird_runs'].sum()}, 含乱码文件 {(group['weird_runs']>0).sum()}")
    print(f"  典型关键词命中: 平均 {group['keyword_hits'].mean():.1f}/8")

print("\n" + "=" * 70)
print("最可疑的 10 个文件（按 ASCII 占比从低到高）")
print("=" * 70)
suspicious = rdf.sort_values("ascii_ratio").head(10)
for _, r in suspicious.iterrows():
    print(f"  [{r['category']}] {r['filename']}")
    print(f"    ASCII={r['ascii_ratio']*100:.1f}% alpha={r['alpha_ratio']*100:.1f}% weird_runs={r['weird_runs']} keywords={r['keyword_hits']}/8")

print("\n" + "=" * 70)
print("乱码段最多的 10 个文件")
print("=" * 70)
weird = rdf.sort_values("weird_runs", ascending=False).head(10)
for _, r in weird.iterrows():
    print(f"  [{r['category']}] {r['filename']}")
    print(f"    weird_runs={r['weird_runs']} length={r['length']} ASCII={r['ascii_ratio']*100:.1f}%")

# 保存
rdf.to_csv("data/processed/21_quality_metrics.csv", index=False, encoding="utf-8-sig")
print(f"\n详细指标保存至: data/processed/21_quality_metrics.csv")