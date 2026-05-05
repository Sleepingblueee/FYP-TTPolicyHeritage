"""
盘点已下载的数据
确认我们手头有什么、按类别和年份的真实分布
"""

import pandas as pd
from pathlib import Path
import re

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def parse_filename(fname):
    """文件名格式: {category}_{timestamp}_{digest}.html"""
    m = re.match(r"^(\w+?)_(\d{14})_(\w+)\.html$", fname)
    if m:
        return {
            "category": m.group(1),
            "timestamp": m.group(2),
            "digest_short": m.group(3),
            "year": m.group(2)[:4],
        }
    return None


def inventory_dir(d, name):
    print(f"\n{'='*60}")
    print(f"{name}: {d}")
    print(f"{'='*60}")
    
    if not d.exists():
        print("目录不存在")
        return None
    
    files = list(d.glob("*.html"))
    if not files:
        print("没有文件")
        return None
    
    records = []
    for f in files:
        meta = parse_filename(f.name)
        if meta:
            meta["size_kb"] = f.stat().st_size / 1024
            meta["filename"] = f.name
            records.append(meta)
    
    df = pd.DataFrame(records)
    
    print(f"总文件数: {len(df)}")
    print(f"\n按类别:")
    for cat, count in df.groupby("category").size().sort_values(ascending=False).items():
        print(f"  {cat}: {count}")
    
    print(f"\n按年份:")
    for year, count in df.groupby("year").size().sort_index().items():
        print(f"  {year}: {count}")
    
    print(f"\n按 [类别 × 年份]:")
    pivot = df.groupby(["category", "year"]).size().unstack(fill_value=0)
    print(pivot.to_string())
    
    print(f"\n文件大小:")
    print(f"  平均: {df['size_kb'].mean():.0f} KB")
    print(f"  中位数: {df['size_kb'].median():.0f} KB")
    print(f"  最小: {df['size_kb'].min():.0f} KB")
    print(f"  最大: {df['size_kb'].max():.0f} KB")
    print(f"  <5 KB（异常小）: {(df['size_kb'] < 5).sum()} 个")
    print(f"  >1500 KB（异常大）: {(df['size_kb'] > 1500).sum()} 个")
    
    return df


def main():
    print("数据盘点")
    
    main_df = inventory_dir(RAW_DIR / "main", "主样本")
    news_df = inventory_dir(RAW_DIR / "news", "NEWS 辅助")
    
    # 保存盘点结果
    if main_df is not None:
        main_df.to_csv(PROCESSED_DIR / "08_main_inventory.csv", index=False, encoding="utf-8-sig")
        print(f"\n主样本盘点保存至: data/processed/08_main_inventory.csv")
    if news_df is not None:
        news_df.to_csv(PROCESSED_DIR / "08_news_inventory.csv", index=False, encoding="utf-8-sig")
        print(f"NEWS 盘点保存至: data/processed/08_news_inventory.csv")
    
    # 总结
    total = (len(main_df) if main_df is not None else 0) + (len(news_df) if news_df is not None else 0)
    print(f"\n{'='*60}")
    print(f"总下载数据: {total} 个 HTML 文件")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()