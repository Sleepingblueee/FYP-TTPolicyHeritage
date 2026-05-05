"""
处理异常文件
- <5KB: 多半是空壳，删除
- >1500KB: 可能含 IA 工具栏，先抽样检查再决定
"""

import pandas as pd
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
RAW_DIR = Path("data/raw")


def main():
    df = pd.read_csv(PROCESSED_DIR / "08_main_inventory.csv")
    
    # 1. 处理过小文件
    too_small = df[df["size_kb"] < 5]
    print(f"找到 {len(too_small)} 个过小文件 (<5KB):")
    for _, row in too_small.iterrows():
        fpath = RAW_DIR / "main" / row["filename"]
        print(f"  {row['filename']} ({row['size_kb']:.1f} KB) | {row['category']} {row['year']}")
        print(f"    内容预览（前 200 字符）:")
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            print(f"    {content[:200]}")
        except Exception as e:
            print(f"    无法读取: {e}")
        print()
    
    # 2. 处理过大文件
    too_large = df[df["size_kb"] > 1500]
    print(f"\n找到 {len(too_large)} 个过大文件 (>1500KB):")
    for _, row in too_large.iterrows():
        print(f"  {row['filename']} ({row['size_kb']:.1f} KB) | {row['category']} {row['year']}")
    print("\n大文件先不删除，等正文提取阶段再判断。")
    
    # 3. 询问是否删除小文件
    print("\n" + "=" * 60)
    print("建议操作:")
    print(f"  小文件 ({len(too_small)} 个): 检查上面的内容预览，如果都是错误页/空壳，建议删除")
    print(f"  大文件 ({len(too_large)} 个): 暂不处理，正文提取时再看")
    print("=" * 60)
    print("\n如果确认要删除小文件，运行:")
    print("  python code\\python\\09_remove_anomalies.py --delete")
    
    # 4. 如果带 --delete 参数，真删
    import sys
    if "--delete" in sys.argv:
        print("\n执行删除...")
        deleted = 0
        for _, row in too_small.iterrows():
            fpath = RAW_DIR / "main" / row["filename"]
            if fpath.exists():
                fpath.unlink()
                deleted += 1
                print(f"  删除: {row['filename']}")
        print(f"\n共删除 {deleted} 个过小文件")
        print("\n建议重新运行盘点脚本更新 inventory:")
        print("  python code\\python\\08_inventory_downloaded.py")


if __name__ == "__main__":
    main()