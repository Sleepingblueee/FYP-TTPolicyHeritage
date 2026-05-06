"""
对比人工编码 vs Gemini 编码
- 加载 30_pilot_sample.csv (人工) + 31_gemini_coded.csv (Gemini)
- 对每个 code 计算: 一致率、Krippendorff α、混淆矩阵
- 输出诊断报告: 哪些 code α >= 0.80 (通过)、哪些需要改进
- v2: 加 read_csv_robust 处理 Excel 保存的 GBK 编码
"""

import pandas as pd
import numpy as np
import krippendorff
from pathlib import Path

HUMAN = Path("data/processed/30_pilot_sample.csv")
GEMINI = Path("data/processed/31_gemini_coded.csv")
OUTPUT = Path("data/processed/32_reliability_report.csv")
OUTPUT_DETAIL = Path("data/processed/32_disagreements.csv")

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B


def read_csv_robust(path):
    """尝试多种编码读 CSV。Excel 在中文 Windows 上常存成 GBK。"""
    for enc in ["utf-8-sig", "utf-8", "gbk", "gb18030", "cp1252"]:
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"  [{path.name}] 用 {enc} 编码读取成功")
            return df
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别 {path} 的编码")


def to_int_safe(x):
    """把人工编码列里的值转成 int 0/1。空值/字符串/NaN 都按 0 处理。"""
    if pd.isna(x):
        return 0
    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return 0
    try:
        v = int(float(s))
        return 1 if v == 1 else 0
    except ValueError:
        return 0


def compute_metrics(human_vec, gemini_vec, code_name):
    """对一对编码向量计算各种 reliability 指标"""
    h = np.array(human_vec)
    g = np.array(gemini_vec)
    n = len(h)
    
    agree = (h == g).sum()
    agreement_rate = agree / n
    
    both_1 = ((h == 1) & (g == 1)).sum()
    both_0 = ((h == 0) & (g == 0)).sum()
    h1_g0 = ((h == 1) & (g == 0)).sum()
    h0_g1 = ((h == 0) & (g == 1)).sum()
    
    h_pos = h.sum()
    g_pos = g.sum()
    
    if h_pos == 0 and g_pos == 0:
        alpha = float("nan")
        alpha_note = "ALL_ZERO"
    elif (h == g).all():
        alpha = 1.0
        alpha_note = "PERFECT"
    else:
        try:
            data = np.array([h, g])
            alpha = krippendorff.alpha(reliability_data=data, level_of_measurement="nominal")
            alpha_note = ""
        except Exception as e:
            alpha = float("nan")
            alpha_note = f"ERROR: {e}"
    
    if g_pos == 0 and h_pos == 0:
        f1 = float("nan")
    elif both_1 == 0:
        f1 = 0.0
    else:
        precision = both_1 / g_pos if g_pos > 0 else 0
        recall = both_1 / h_pos if h_pos > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "code": code_name,
        "n": n,
        "human_pos": int(h_pos),
        "gemini_pos": int(g_pos),
        "both_1": int(both_1),
        "both_0": int(both_0),
        "human_only": int(h1_g0),
        "gemini_only": int(h0_g1),
        "agreement_rate": round(agreement_rate, 3),
        "krippendorff_alpha": round(alpha, 3) if not np.isnan(alpha) else alpha,
        "f1": round(f1, 3) if not np.isnan(f1) else f1,
        "alpha_note": alpha_note,
    }


def main():
    print("=" * 60)
    print("Step 32: 人工 vs Gemini 编码对比")
    print("=" * 60)
    
    print("\n加载 CSV:")
    human_df = read_csv_robust(HUMAN)
    gemini_df = read_csv_robust(GEMINI)
    
    merged = human_df[["sample_id", "category", "year", "section_text"] + ALL_CODES].merge(
        gemini_df[["sample_id"] + [f"gemini_{c}" for c in ALL_CODES] +
                  [f"gemini_reason_{c}" for c in ALL_CODES]],
        on="sample_id",
        how="inner",
    )
    print(f"\n合并后样本数: {len(merged)}")
    
    for code in ALL_CODES:
        merged[code] = merged[code].apply(to_int_safe)
        merged[f"gemini_{code}"] = merged[f"gemini_{code}"].apply(to_int_safe)
    
    results = []
    for code in ALL_CODES:
        h_vec = merged[code].tolist()
        g_vec = merged[f"gemini_{code}"].tolist()
        metrics = compute_metrics(h_vec, g_vec, code)
        results.append(metrics)
    
    report = pd.DataFrame(results)
    report.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    
    print("\n" + "=" * 90)
    print(f"{'Code':<32} {'N':>3} {'H+':>3} {'G+':>3} {'Agree':>6} {'Alpha':>7} {'F1':>6} {'Note':<10}")
    print("=" * 90)
    
    for _, r in report.iterrows():
        alpha_str = f"{r['krippendorff_alpha']:.3f}" if isinstance(r['krippendorff_alpha'], float) and not np.isnan(r['krippendorff_alpha']) else "n/a"
        f1_str = f"{r['f1']:.3f}" if isinstance(r['f1'], float) and not np.isnan(r['f1']) else "n/a"
        agree_str = f"{r['agreement_rate']:.3f}"
        flag = ""
        if isinstance(r['krippendorff_alpha'], float) and not np.isnan(r['krippendorff_alpha']):
            if r['krippendorff_alpha'] >= 0.80:
                flag = "OK"
            elif r['krippendorff_alpha'] >= 0.67:
                flag = "BORDERLINE"
            else:
                flag = "FAIL"
        elif r['alpha_note'] == "ALL_ZERO":
            flag = "ALL_0"
        print(f"{r['code']:<32} {r['n']:>3} {r['human_pos']:>3} {r['gemini_pos']:>3} {agree_str:>6} {alpha_str:>7} {f1_str:>6} {flag:<10}")
    
    print("=" * 90)
    print("\n图例:")
    print("  N: 总样本数")
    print("  H+: 人工编码判为 1 的数量")
    print("  G+: Gemini 判为 1 的数量")
    print("  Agree: 一致率")
    print("  Alpha: Krippendorff's α (>= 0.80 通过, 0.67-0.80 边缘, < 0.67 失败)")
    print("  F1: Gemini vs 人工 ground truth 的 F1")
    print("  ALL_0: 两边都没判 1 (这个 code 在 30 个样本里没出现)")
    
    print("\n" + "=" * 60)
    print("产出: 分歧明细")
    print("=" * 60)
    
    disagreements = []
    for _, row in merged.iterrows():
        for code in ALL_CODES:
            h = row[code]
            g = row[f"gemini_{code}"]
            if h != g:
                disagreements.append({
                    "sample_id": row["sample_id"],
                    "category": row["category"],
                    "code": code,
                    "human": h,
                    "gemini": g,
                    "gemini_reason": row.get(f"gemini_reason_{code}", ""),
                    "section_text": row["section_text"][:300],
                })
    
    if disagreements:
        dis_df = pd.DataFrame(disagreements)
        dis_df.to_csv(OUTPUT_DETAIL, index=False, encoding="utf-8-sig")
        print(f"分歧条目数: {len(dis_df)}")
        print(f"保存至: {OUTPUT_DETAIL}")
        
        print("\n按 code 分歧数(从高到低):")
        for code, count in dis_df["code"].value_counts().items():
            print(f"  {code}: {count}")
    else:
        print("没有分歧 (你和 Gemini 完全一致 — 这极不寻常,请检查数据)")
    
    print(f"\n报告: {OUTPUT}")


if __name__ == "__main__":
    main()