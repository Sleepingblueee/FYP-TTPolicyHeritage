"""
全量编码结果汇总
- 加载 41_full_coded.csv 和 40_sampled_sections.csv 合并
- 输出基础描述统计:每 code × year × category 的频率分布
- 输出合并后的完整数据集 42_full_dataset.csv
"""

import pandas as pd
from pathlib import Path

CODED = Path("data/processed/41_full_coded.csv")
SECTIONS = Path("data/processed/40_sampled_sections.csv")
OUTPUT_FULL = Path("data/processed/42_full_dataset.csv")
OUTPUT_BY_CODE = Path("data/processed/43_code_freq_by_year_category.csv")

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B


def read_csv_robust(path):
    for enc in ["utf-8-sig", "utf-8", "gbk"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别 {path}")


def main():
    print("=" * 70)
    print("Step 43: 全量编码结果汇总")
    print("=" * 70)
    
    coded = read_csv_robust(CODED)
    sections = read_csv_robust(SECTIONS)
    
    print(f"\n编码数据行数: {len(coded)}")
    print(f"原始 sections 行数: {len(sections)}")
    
    # 转换数值列
    for c in ALL_CODES:
        col = f"gemini_{c}"
        if col in coded.columns:
            coded[col] = pd.to_numeric(coded[col], errors="coerce")
    
    # 成功编码 = gemini_power 是 0 或 1(其他为 NaN 或空)
    ok_mask = coded["gemini_power"].isin([0, 1])
    ok = coded[ok_mask].copy()
    failed = coded[~ok_mask].copy()
    
    print(f"\n成功编码: {len(ok)}")
    print(f"失败/缺失: {len(failed)}")
    print(f"成功率: {len(ok)/len(coded)*100:.1f}%")
    
    # 合并文本和元数据
    full = ok.merge(sections, on="section_id", how="left")
    full.to_csv(OUTPUT_FULL, index=False, encoding="utf-8-sig")
    print(f"\n合并数据集: {OUTPUT_FULL}")
    
    # 每个 code 的总判 1 数
    print(f"\n{'='*70}")
    print("每个 code 在全量编码中的判 1 总数")
    print(f"{'='*70}")
    print(f"{'Code':<35} {'1 数':>6} {'占比':>8}")
    print("-" * 70)
    
    code_summary = []
    for c in ALL_CODES:
        col = f"gemini_{c}"
        n_ones = int(ok[col].sum())
        pct = n_ones / len(ok) * 100
        print(f"{c:<35} {n_ones:>6} {pct:>7.1f}%")
        code_summary.append({"code": c, "n_ones": n_ones, "pct": pct})
    
    # 按 year × category 的 cross-tab
    print(f"\n{'='*70}")
    print("全量编码 sections 按 year × category 分布")
    print(f"{'='*70}")
    pivot = full.pivot_table(index="year", columns="category", values="section_id", aggfunc="count", fill_value=0)
    print(pivot.to_string())
    
    # 保存每 code × year × category 的频率表
    rows = []
    for c in ALL_CODES:
        col = f"gemini_{c}"
        # 按 year × category 求和
        agg = full.groupby(["year", "category"])[col].sum().reset_index()
        agg.columns = ["year", "category", "n_ones"]
        agg["code"] = c
        # 加分母(每年每类的 sections 数)
        denom = full.groupby(["year", "category"]).size().reset_index(name="n_sections")
        agg = agg.merge(denom, on=["year", "category"])
        agg["pct"] = (agg["n_ones"] / agg["n_sections"] * 100).round(1)
        rows.append(agg)
    
    code_freq = pd.concat(rows, ignore_index=True)
    code_freq = code_freq[["code", "year", "category", "n_sections", "n_ones", "pct"]]
    code_freq.to_csv(OUTPUT_BY_CODE, index=False, encoding="utf-8-sig")
    print(f"\n每 code × year × category 频率表: {OUTPUT_BY_CODE}")
    
    # 几个关键时间序列示例
    print(f"\n{'='*70}")
    print("Power 在每年的频率(samples 数 / 1 数 / 占比)")
    print(f"{'='*70}")
    for year, grp in full.groupby("year"):
        n = len(grp)
        ones = int(grp["gemini_power"].sum())
        pct = ones / n * 100 if n > 0 else 0
        print(f"  {year}: {n:>4} sections, power=1: {ones:>4} ({pct:.1f}%)")
    
    print(f"\n{'='*70}")
    print("B3 indigenous 在每年的频率")
    print(f"{'='*70}")
    for year, grp in full.groupby("year"):
        n = len(grp)
        ones = int(grp["gemini_B3_indigenous_minority"].sum())
        pct = ones / n * 100 if n > 0 else 0
        print(f"  {year}: {n:>4} sections, B3=1: {ones:>4} ({pct:.1f}%)")


if __name__ == "__main__":
    main()