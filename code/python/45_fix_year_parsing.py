"""
修复 40_sampled_sections.csv 里 year='sub' 的 1783 行
- 文件名格式:CG_sub_YYYYMMDDHHMMSS_*.html → 提取 YYYY
- 输出新文件:42_full_dataset_fixed.csv
- 同时加一个新列 is_sub_page = True/False(标记 CG 主页面 vs CG 子页面)
"""

import re
import pandas as pd
from pathlib import Path

INPUT_SECTIONS = Path("data/processed/40_sampled_sections.csv")
INPUT_CODED = Path("data/processed/41_full_coded.csv")
OUTPUT = Path("data/processed/42_full_dataset_fixed.csv")


def read_csv_robust(path):
    for enc in ["utf-8-sig", "utf-8", "gbk"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue


def extract_year_from_filename(filename):
    """从 'CG_sub_20230321122525_*.html' 提取 2023"""
    m = re.search(r"_(\d{4})\d{10}_", str(filename))
    if m:
        return m.group(1)
    # fallback: 任何 _YYYY 开头的串
    m = re.search(r"_(\d{4})", str(filename))
    if m:
        return m.group(1)
    return None


def main():
    print("=" * 60)
    print("Step 45: 修复 year='sub' 解析问题")
    print("=" * 60)
    
    sections = read_csv_robust(INPUT_SECTIONS)
    coded = read_csv_robust(INPUT_CODED)
    
    print(f"\nsections: {len(sections)}")
    print(f"coded: {len(coded)}")
    
    # 标记 sub 页面
    sections["is_sub_page"] = sections["filename"].astype(str).str.startswith("CG_sub_")
    
    # 修复 year='sub' 的行
    bad_year_mask = sections["year"].astype(str) == "sub"
    n_bad = bad_year_mask.sum()
    print(f"\nyear='sub' 的行数: {n_bad}")
    
    if n_bad > 0:
        # 从文件名提取 year
        fixed_years = sections.loc[bad_year_mask, "filename"].apply(extract_year_from_filename)
        n_fixed = fixed_years.notna().sum()
        n_failed = fixed_years.isna().sum()
        print(f"成功从文件名提取 year: {n_fixed}")
        print(f"提取失败: {n_failed}")
        
        sections.loc[bad_year_mask, "year"] = fixed_years
    
    # 转换数值列
    coded_cols = [c for c in coded.columns if c.startswith("gemini_") and not c.startswith("gemini_reason_")]
    for c in coded_cols:
        coded[c] = pd.to_numeric(coded[c], errors="coerce")
    
    # 只保留成功编码的
    ok = coded[coded["gemini_power"].isin([0, 1])].copy()
    print(f"\n成功编码: {len(ok)}")
    
    # 合并
    full = ok.merge(sections, on="section_id", how="left")
    full.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    
    print(f"\n合并后: {len(full)}")
    print(f"\n修复后 year 分布:")
    print(full["year"].value_counts(dropna=False).sort_index())
    
    print(f"\nis_sub_page 分布:")
    print(full["is_sub_page"].value_counts())
    
    print(f"\nCG 子页面 vs CG 主页面分布:")
    cg_only = full[full["category"] == "CG"]
    print(f"  CG 总数: {len(cg_only)}")
    print(f"  CG 主页面 (is_sub_page=False): {(~cg_only['is_sub_page']).sum()}")
    print(f"  CG 子页面 (is_sub_page=True): {cg_only['is_sub_page'].sum()}")
    
    print(f"\nCG 子页面按修复后的 year 分布:")
    cg_sub = cg_only[cg_only["is_sub_page"]]
    print(cg_sub["year"].value_counts().sort_index())
    
    print(f"\n保存: {OUTPUT}")


if __name__ == "__main__":
    main()