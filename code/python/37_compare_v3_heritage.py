"""
v3 reliability:Gemini v3 vs 你的 heritage 人工编码
"""

import pandas as pd
import numpy as np
import krippendorff
from pathlib import Path

HUMAN = Path("data/processed/33_heritage_targeted_sample.csv")
GEMINI_V2 = Path("data/processed/34_gemini_coded_v2.csv")
GEMINI_V3 = Path("data/processed/36_gemini_coded_v3_heritage.csv")
OUT_REPORT = Path("data/processed/37_v3_heritage_report.csv")
OUT_DISAGREE = Path("data/processed/37_v3_heritage_disagreements.csv")

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
            alpha = krippendorff.alpha(reliability_data=np.array([h, g]), level_of_measurement="nominal")
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
        "code": code_name, "n": n,
        "human_pos": int(h_pos), "gemini_pos": int(g_pos),
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


def evaluate(human_df, gemini_df, prefix="gemini_"):
    merged = human_df[["sample_id"] + ALL_CODES].merge(
        gemini_df[["sample_id"] + [f"{prefix}{c}" for c in ALL_CODES]],
        on="sample_id", how="inner"
    )
    for code in ALL_CODES:
        merged[code] = merged[code].apply(to_int_safe)
        merged[f"{prefix}{code}"] = merged[f"{prefix}{code}"].apply(to_int_safe)
    
    rows = []
    for code in ALL_CODES:
        rows.append(compute_metrics(merged[code].tolist(), merged[f"{prefix}{code}"].tolist(), code))
    return pd.DataFrame(rows), merged


def print_report(df, title):
    print(f"\n{'='*92}")
    print(title)
    print(f"{'='*92}")
    print(f"{'Code':<32} {'N':>3} {'H+':>3} {'G+':>3} {'Agree':>6} {'Alpha':>7} {'F1':>6} {'Status':<8}")
    print("-" * 92)
    for _, r in df.iterrows():
        a = f"{r['alpha']:.3f}" if isinstance(r['alpha'], float) and not np.isnan(r['alpha']) else "n/a"
        f = f"{r['f1']:.3f}" if isinstance(r['f1'], float) and not np.isnan(r['f1']) else "n/a"
        st = flag(r['alpha'], r['note'])
        print(f"{r['code']:<32} {r['n']:>3} {r['human_pos']:>3} {r['gemini_pos']:>3} {r['agreement']:>6.3f} {a:>7} {f:>6} {st:<8}")
    print("=" * 92)


def main():
    print("=" * 92)
    print("Step 37: v3 reliability vs heritage 人工编码")
    print("=" * 92)
    
    human = read_csv_robust(HUMAN)
    gemini_v2_all = read_csv_robust(GEMINI_V2)
    gemini_v2 = gemini_v2_all[gemini_v2_all["source"] == "heritage"].copy()
    gemini_v3 = read_csv_robust(GEMINI_V3)
    
    print(f"\nhuman: {len(human)}")
    print(f"gemini v2 heritage: {len(gemini_v2)}")
    print(f"gemini v3 heritage: {len(gemini_v3)}")
    
    rep_v2, _ = evaluate(human, gemini_v2)
    rep_v3, merged = evaluate(human, gemini_v3)
    
    print_report(rep_v2, "v2 baseline (heritage)")
    print_report(rep_v3, "v3 RESULT (heritage)")
    
    # 对比表
    print(f"\n{'='*92}")
    print("v2 → v3 对比 (heritage 30 个)")
    print(f"{'='*92}")
    print(f"{'Code':<32} {'v2 α':>8} {'v3 α':>8} {'Δα':>8} {'v2 F1':>8} {'v3 F1':>8} {'verdict':<15}")
    print("-" * 92)
    
    rows = []
    for code in ALL_CODES:
        v2_row = rep_v2[rep_v2["code"] == code].iloc[0]
        v3_row = rep_v3[rep_v3["code"] == code].iloc[0]
        a2 = v2_row["alpha"] if isinstance(v2_row["alpha"], float) and not np.isnan(v2_row["alpha"]) else None
        a3 = v3_row["alpha"] if isinstance(v3_row["alpha"], float) and not np.isnan(v3_row["alpha"]) else None
        f2 = v2_row["f1"] if isinstance(v2_row["f1"], float) and not np.isnan(v2_row["f1"]) else None
        f3 = v3_row["f1"] if isinstance(v3_row["f1"], float) and not np.isnan(v3_row["f1"]) else None
        
        if a2 is None and a3 is None:
            delta_str = "ALL_0"; verdict = "no data"
        elif a2 is None or a3 is None:
            delta_str = "n/a"; verdict = "partial"
        else:
            delta = a3 - a2
            delta_str = f"{delta:+.3f}"
            if a3 >= 0.80 and a2 < 0.80:
                verdict = "FIXED"
            elif a3 >= 0.80 and a2 >= 0.80:
                verdict = "STILL OK"
            elif a2 >= 0.80 and a3 < 0.80:
                verdict = "REGRESSION"
            elif delta > 0.10:
                verdict = "improved"
            elif delta < -0.10:
                verdict = "worsened"
            else:
                verdict = "stable"
        
        a2s = f"{a2:.3f}" if a2 is not None else "n/a"
        a3s = f"{a3:.3f}" if a3 is not None else "n/a"
        f2s = f"{f2:.3f}" if f2 is not None else "n/a"
        f3s = f"{f3:.3f}" if f3 is not None else "n/a"
        print(f"{code:<32} {a2s:>8} {a3s:>8} {delta_str:>8} {f2s:>8} {f3s:>8} {verdict:<15}")
        rows.append({"code": code, "v2_alpha": a2, "v3_alpha": a3, "delta": (a3-a2) if (a2 is not None and a3 is not None) else None, "verdict": verdict})
    
    rep_v3.to_csv(OUT_REPORT, index=False, encoding="utf-8-sig")
    
    # 分歧
    text_lookup = human.set_index("sample_id")["section_text"].to_dict()
    disagree = []
    for _, row in merged.iterrows():
        for code in ALL_CODES:
            h = row[code]
            g = row[f"gemini_{code}"]
            if h != g:
                g_row = gemini_v3[gemini_v3["sample_id"] == row["sample_id"]]
                reason = g_row[f"gemini_reason_{code}"].iloc[0] if len(g_row) > 0 else ""
                disagree.append({
                    "sample_id": row["sample_id"], "code": code,
                    "human": h, "gemini": g,
                    "gemini_reason": reason,
                    "section_text": text_lookup.get(row["sample_id"], "")[:300],
                })
    
    if disagree:
        pd.DataFrame(disagree).to_csv(OUT_DISAGREE, index=False, encoding="utf-8-sig")
        print(f"\n分歧条目: {len(disagree)} → {OUT_DISAGREE}")
        for code, count in pd.DataFrame(disagree)["code"].value_counts().items():
            print(f"  {code}: {count}")


if __name__ == "__main__":
    main()