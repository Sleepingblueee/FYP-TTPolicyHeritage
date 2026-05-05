"""
诊断下载失败的原因
不下载任何东西，只分析失败模式
"""

import pandas as pd
from pathlib import Path
from collections import Counter

INPUT_DIR = Path("data/processed")

def main():
    # 加载失败列表
    df = pd.read_csv(INPUT_DIR / "05_download_failures.csv")
    print(f"总失败数: {len(df)}")
    
    # 按失败原因分类
    print("\n按失败原因分布:")
    reason_counts = df["reason"].value_counts()
    for reason, count in reason_counts.items():
        print(f"  {count:5d}  {reason}")
    
    # 按类别分布
    print("\n按文档类别分布:")
    cat_counts = df["category"].value_counts()
    for cat, count in cat_counts.items():
        print(f"  {count:5d}  {cat}")
    
    # 按时间段分布
    df["year"] = df["timestamp"].astype(str).str[:4]
    print("\n按年份分布:")
    year_counts = df["year"].value_counts().sort_index()
    for year, count in year_counts.items():
        print(f"  {count:5d}  {year}")
    
    # 抽样 5 个失败的看看
    print("\n抽样 5 个失败的快照:")
    for i, row in df.sample(min(5, len(df))).iterrows():
        print(f"  [{row['category']}] {row['timestamp']} | {row['reason']}")
        print(f"    URL: {row['original'][:100]}")
    
    # 看看成功的快照分布对比
    main_df = pd.read_csv(INPUT_DIR / "05_main_download_final.csv")
    main_df["year"] = main_df["timestamp"].astype(str).str[:4]
    print("\n主样本原始分布（成功+失败）:")
    for year, count in main_df["year"].value_counts().sort_index().items():
        failed_in_year = year_counts.get(year, 0)
        rate = failed_in_year / count * 100
        print(f"  {year}: 总 {count:4d}, 失败 {failed_in_year:4d} ({rate:.0f}%)")
    
    print("\n" + "="*60)
    print("已下载文件目录检查:")
    print("="*60)
    main_dir = Path("data/raw/main")
    news_dir = Path("data/raw/news")
    if main_dir.exists():
        files = list(main_dir.glob("*.html"))
        sizes = [f.stat().st_size for f in files]
        print(f"main/: {len(files)} 个文件")
        print(f"  平均大小: {sum(sizes)/len(sizes)/1024:.1f} KB")
        print(f"  最小: {min(sizes)/1024:.1f} KB")
        print(f"  最大: {max(sizes)/1024:.1f} KB")
        # 检查异常小的文件
        too_small = [f for f in files if f.stat().st_size < 5000]
        print(f"  异常小（<5KB）: {len(too_small)} 个")
    if news_dir.exists():
        files = list(news_dir.glob("*.html"))
        sizes = [f.stat().st_size for f in files]
        print(f"news/: {len(files)} 个文件")
        print(f"  平均大小: {sum(sizes)/len(sizes)/1024:.1f} KB")
        print(f"  最小: {min(sizes)/1024:.1f} KB")

if __name__ == "__main__":
    main()