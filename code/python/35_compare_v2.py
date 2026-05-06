"""
v2 reliability report
- 三组对比:
  (1) v1 vs v2 在 pilot 30 个上(看 codebook v2 + 强化 prompt 是否修好了 v1 问题)
  (2) v2 在 heritage 30 个上(看 heritage codes 单独的 reliability)
  (3) v2 合并 60 个总对比(论文最终用)
"""

import pandas as pd
import numpy as np
import krippendorff
from pathlib import Path

# 输入
PILOT_HUMAN = Path("data/processed/30_pilot_sample.csv")
HERITAGE_HUMAN = Path("data/processed/33_heritage_targeted_sample.csv")
GEMINI_V1 = Path("data/processed/31_gemini_coded.csv")
GEMINI_V2 = Path("data/processed/34_gemini_coded_v2.csv")

# 输出
OUT_REPORT = Path("data/processed/35_reliability_report_v2.csv")
OUT_DISAGREE = Path("data/processed/35_disagreements_v2.csv")
OUT_COMPARE = Path("data/processed/35_v1_vs_v2_pilot.csv")

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B


def read_csv_robust(path):
    for enc in ["utf-8-sig", "utf-8", "gbk", "gb18030", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别 {path}")


def to_int_safe(x):
    if pd.isna(x):
        return 0
    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return 0
    try:
        return 1 if int(float(s)) == 1 else 0
    except ValueError:
        return 0


def compute_metrics(human_vec, gemini_vec, code_name):
    h = np.array(human_vec)
    g = np.array(gemini_vec)
    n = len(h)
    
    agree = (h == g).sum()
    agreement_rate = agree / n
    both_1 = ((h == 1) & (g == 1)).sum()
    h_pos = h.sum()
    g_pos = g.sum()
    
    if h_pos == 0 and g_pos == 0:
        alpha = float("nan")
        note = "ALL_ZERO"
    elif (h == g).all():
        alpha = 1.0
        note = "PERFECT"
    else:
        try:
            data = np.array([h, g])
            alpha = krippendorff.alpha(reliability_data=data, level_of_measurement="nominal")
            note = ""
        except Exception as e:
            alpha = float("nan")
            note = f"ERR:{e}"
    
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
        "human_only": int(((h == 1) & (g == 0)).sum()),
        "gemini_only": int(((h == 0) & (g == 1)).sum()),
        "agreement": round(agreement_rate, 3),
        "alpha": round(alpha, 3) if not np.isnan(alpha) else alpha,
        "f1": round(f1, 3) if not np.isnan(f1) else f1,
        "note": note,
    }


def flag(alpha, note):
    if note == "ALL_ZERO":
        return "ALL_0"
    if isinstance(alpha, float) and not np.isnan(alpha):
        if alpha >= 0.80:
            return "OK"
        elif alpha >= 0.67:
            return "BORDER"
        else:
            return "FAIL"
    return ""


def print_report(report_df, title):
    print(f"\n{'='*92}")
    print(f"{title}")
    print(f"{'='*92}")
    print(f"{'Code':<32} {'N':>3} {'H+':>3} {'G+':>3} {'Agree':>6} {'Alpha':>7} {'F1':>6} {'Status':<8}")
    print("-" * 92)
    for _, r in report_df.iterrows():
        a = f"{r['alpha']:.3f}" if isinstance(r['alpha'], float) and not np.isnan(r['alpha']) else "n/a"
        f = f"{r['f1']:.3f}" if isinstance(r['f1'], float) and not np.isnan(r['f1']) else "n/a"
        st = flag(r['alpha'], r['note'])
        print(f"{r['code']:<32} {r['n']:>3} {r['human_pos']:>3} {r['gemini_pos']:>3} {r['agreement']:>6.3f} {a:>7} {f:>6} {st:<8}")
    print("=" * 92)


def evaluate(human_df, gemini_df, gemini_prefix="gemini_", title=""):
    """计算并返回 reliability report"""
    merged = human_df[["sample_id"] + ALL_CODES].merge(
        gemini_df[["sample_id"] + [f"{gemini_prefix}{c}" for c in ALL_CODES]],
        on="sample_id", how="inner"
    )
    
    if len(merged) == 0:
        print(f"  [{title}] 没有匹配样本")
        return None, merged
    
    for code in ALL_CODES:
        merged[code] = merged[code].apply(to_int_safe)
        merged[f"{gemini_prefix}{code}"] = merged[f"{gemini_prefix}{code}"].apply(to_int_safe)
    
    rows = []
    for code in ALL_CODES:
        rows.append(compute_metrics(
            merged[code].tolist(),
            merged[f"{gemini_prefix}{code}"].tolist(),
            code
        ))
    return pd.DataFrame(rows), merged


def main():
    print("=" * 92)
    print("Step 35: v2 reliability report")
    print("=" * 92)
    
    # 加载所有数据
    print("\n加载数据...")
    pilot_human = read_csv_robust(PILOT_HUMAN)
    heritage_human = read_csv_robust(HERITAGE_HUMAN)
    gemini_v1 = read_csv_robust(GEMINI_V1)
    gemini_v2 = read_csv_robust(GEMINI_V2)
    
    # v2 拆成 pilot 和 heritage
    gemini_v2_pilot = gemini_v2[gemini_v2["source"] == "pilot"].copy()
    gemini_v2_heritage = gemini_v2[gemini_v2["source"] == "heritage"].copy()
    
    print(f"  pilot human: {len(pilot_human)}")
    print(f"  heritage human: {len(heritage_human)}")
    print(f"  gemini v1 (pilot): {len(gemini_v1)}")
    print(f"  gemini v2 pilot: {len(gemini_v2_pilot)}")
    print(f"  gemini v2 heritage: {len(gemini_v2_heritage)}")
    
    # ============ 报告 1: v1 在 pilot 上的 reliability(基线) ============
    rep_v1, _ = evaluate(pilot_human, gemini_v1, "gemini_", "v1 baseline")
    print_report(rep_v1, "REPORT 1: v1 BASELINE (codebook v1 + Gemini v1) — 30 pilot")
    
    # ============ 报告 2: v2 在 pilot 上的 reliability ============
    rep_v2_pilot, _ = evaluate(pilot_human, gemini_v2_pilot, "gemini_", "v2 pilot")
    print_report(rep_v2_pilot, "REPORT 2: v2 (codebook v2 + Gemini v2) — 30 pilot")
    
    # ============ 报告 3: v2 在 heritage 上的 reliability ============
    rep_v2_heritage, _ = evaluate(heritage_human, gemini_v2_heritage, "gemini_", "v2 heritage")
    print_report(rep_v2_heritage, "REPORT 3: v2 — 30 heritage targeted")
    
    # ============ 报告 4: v2 合并 60 个 ============
    combined_human = pd.concat([
        pilot_human[["sample_id"] + ALL_CODES],
        heritage_human[["sample_id"] + ALL_CODES],
    ], ignore_index=True)
    combined_gemini = pd.concat([
        gemini_v2_pilot[["sample_id"] + [f"gemini_{c}" for c in ALL_CODES]],
        gemini_v2_heritage[["sample_id"] + [f"gemini_{c}" for c in ALL_CODES]],
    ], ignore_index=True)
    rep_v2_all, merged_all = evaluate(combined_human, combined_gemini, "gemini_", "v2 all 60")
    print_report(rep_v2_all, "REPORT 4: v2 COMBINED 60 (FINAL) — 30 pilot + 30 heritage")
    
    # ============ v1 vs v2 对比表 ============
    print(f"\n{'='*92}")
    print("v1 → v2 改善对比 (pilot 30 个)")
    print(f"{'='*92}")
    print(f"{'Code':<32} {'v1 α':>8} {'v2 α':>8} {'Δα':>8} {'v1 F1':>8} {'v2 F1':>8} {'verdict':<15}")
    print("-" * 92)
    
    compare_rows = []
    for code in ALL_CODES:
        v1_row = rep_v1[rep_v1["code"] == code].iloc[0]
        v2_row = rep_v2_pilot[rep_v2_pilot["code"] == code].iloc[0]
        a1 = v1_row["alpha"] if isinstance(v1_row["alpha"], float) and not np.isnan(v1_row["alpha"]) else None
        a2 = v2_row["alpha"] if isinstance(v2_row["alpha"], float) and not np.isnan(v2_row["alpha"]) else None
        f1_1 = v1_row["f1"] if isinstance(v1_row["f1"], float) and not np.isnan(v1_row["f1"]) else None
        f1_2 = v2_row["f1"] if isinstance(v2_row["f1"], float) and not np.isnan(v2_row["f1"]) else None
        
        if a1 is None and a2 is None:
            delta_str = "ALL_0"
            verdict = "no data"
        elif a1 is None or a2 is None:
            delta_str = "n/a"
            verdict = "partial"
        else:
            delta = a2 - a1
            delta_str = f"{delta:+.3f}"
            if a2 >= 0.80 and a1 < 0.80:
                verdict = "FIXED"
            elif a2 >= 0.80 and a1 >= 0.80:
                verdict = "STILL OK"
            elif a1 >= 0.80 and a2 < 0.80:
                verdict = "REGRESSION"
            elif delta > 0.10:
                verdict = "improved"
            elif delta < -0.10:
                verdict = "worsened"
            else:
                verdict = "stable"
        
        compare_rows.append({
            "code": code,
            "v1_alpha": a1, "v2_alpha": a2,
            "v1_f1": f1_1, "v2_f1": f1_2,
            "delta_alpha": (a2 - a1) if (a1 is not None and a2 is not None) else None,
            "verdict": verdict,
        })
        
        a1s = f"{a1:.3f}" if a1 is not None else "n/a"
        a2s = f"{a2:.3f}" if a2 is not None else "n/a"
        f1_1s = f"{f1_1:.3f}" if f1_1 is not None else "n/a"
        f1_2s = f"{f1_2:.3f}" if f1_2 is not None else "n/a"
        print(f"{code:<32} {a1s:>8} {a2s:>8} {delta_str:>8} {f1_1s:>8} {f1_2s:>8} {verdict:<15}")
    
    pd.DataFrame(compare_rows).to_csv(OUT_COMPARE, index=False, encoding="utf-8-sig")
    
    # 分歧明细(v2 合并 60 个)
    disagreements = []
    pilot_with_text = pilot_human[["sample_id", "section_text"]]
    heritage_with_text = heritage_human[["sample_id", "section_text"]]
    text_lookup = pd.concat([pilot_with_text, heritage_with_text], ignore_index=True).set_index("sample_id")["section_text"].to_dict()
    
    # 重新算 merged_all 的字段
    merged_all_full = combined_human.merge(combined_gemini, on="sample_id", how="inner")
    for code in ALL_CODES:
        merged_all_full[code] = merged_all_full[code].apply(to_int_safe)
        merged_all_full[f"gemini_{code}"] = merged_all_full[f"gemini_{code}"].apply(to_int_safe)
    
    # 加 source 标识
    pilot_ids = set(pilot_human["sample_id"])
    
    for _, row in merged_all_full.iterrows():
        for code in ALL_CODES:
            h = row[code]
            g = row[f"gemini_{code}"]
            if h != g:
                sid = row["sample_id"]
                # 找 Gemini 的 reason
                if sid in pilot_ids:
                    g_row = gemini_v2_pilot[gemini_v2_pilot["sample_id"] == sid]
                else:
                    g_row = gemini_v2_heritage[gemini_v2_heritage["sample_id"] == sid]
                reason = g_row[f"gemini_reason_{code}"].iloc[0] if len(g_row) > 0 else ""
                
                disagreements.append({
                    "sample_id": sid,
                    "source": "pilot" if sid in pilot_ids else "heritage",
                    "code": code,
                    "human": h,
                    "gemini": g,
                    "gemini_reason": reason,
                    "section_text": text_lookup.get(sid, "")[:300],
                })
    
    if disagreements:
        dis_df = pd.DataFrame(disagreements)
        dis_df.to_csv(OUT_DISAGREE, index=False, encoding="utf-8-sig")
        print(f"\n分歧条目: {len(dis_df)} → {OUT_DISAGREE}")
        print("\n按 code 分歧数:")
        for code, count in dis_df["code"].value_counts().items():
            print(f"  {code}: {count}")
    
    # 保存所有 report
    all_reports = pd.concat([
        rep_v1.assign(report="v1_pilot"),
        rep_v2_pilot.assign(report="v2_pilot"),
        rep_v2_heritage.assign(report="v2_heritage"),
        rep_v2_all.assign(report="v2_all_60"),
    ], ignore_index=True)
    all_reports.to_csv(OUT_REPORT, index=False, encoding="utf-8-sig")
    
    print(f"\n保存:")
    print(f"  完整 report: {OUT_REPORT}")
    print(f"  v1 vs v2 对比: {OUT_COMPARE}")
    print(f"  分歧明细: {OUT_DISAGREE}")


if __name__ == "__main__":
    main()