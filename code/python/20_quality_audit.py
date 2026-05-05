"""
质量审计：从每个类别抽 2 个 .md 文件，打印出来让你看
"""

import random
from pathlib import Path
import pandas as pd

EXTRACT_MAIN = Path("data/processed/extracted/main")
EXTRACT_NEWS = Path("data/processed/extracted/news")
REPORT = Path("data/processed/11_extraction_report_v6.csv")

random.seed(42)

df = pd.read_csv(REPORT)
success = df[df["extracted_chars"] > 0].copy()

# 每个类别抽 2 个：1 个最长、1 个最短
print(f"{'='*70}")
print(f"质量审计：每个类别抽样 2 个提取结果")
print(f"{'='*70}")

for cat in success["category"].unique():
    cat_df = success[success["category"] == cat].sort_values("extracted_chars")
    if len(cat_df) < 2:
        samples = cat_df
    else:
        # 抽中位数附近的 1 个 + 短的 1 个
        samples = pd.concat([cat_df.iloc[len(cat_df)//2:len(cat_df)//2+1], cat_df.head(1)])
    
    for _, row in samples.iterrows():
        # 找文件
        for d in [EXTRACT_MAIN, EXTRACT_NEWS]:
            p = d / row["output_file"]
            if p.exists():
                content = p.read_text(encoding="utf-8")
                
                print(f"\n{'='*70}")
                print(f"[{cat}] {row['filename']}")
                print(f"  方法: {row['method']} | 长度: {row['extracted_chars']} 字符")
                print(f"  文件: {p}")
                print(f"{'='*70}")
                print(content[:1500])
                if len(content) > 1500:
                    print(f"\n... [还有 {len(content) - 1500} 字符，省略]")
                break

print(f"\n\n{'='*70}")
print("审计完成")
print(f"{'='*70}")
print("\n你需要肉眼判断这些样本:")
print("  1. 是不是真的政策正文（不是侧边栏/导航/广告）")
print("  2. 有没有大段乱码或重复")
print("  3. 标题、列表结构是否合理")
print("\n如果都OK，告诉 Claude '审计通过'，就可以进入第四步")