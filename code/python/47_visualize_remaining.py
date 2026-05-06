"""
用修复后数据 (42_full_dataset_fixed.csv) 重画剩余的图
- fig2: Part A 高频 code 趋势(分 category)
- fig3: Part B heritage codes 趋势(B3 不再断崖)
- fig4: 共现矩阵(数据微调)
- fig6: power-safety 共现(更新数据)
- fig7: B3 趋势(标题改成"稳定" narrative)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

INPUT = Path("data/processed/42_full_dataset_fixed.csv")
FIG_DIR = Path("figures")
FIG_DIR.mkdir(exist_ok=True)

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 100,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def read_csv_robust(path):
    for enc in ["utf-8-sig", "utf-8", "gbk"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue


def prepare_data(df):
    for c in ALL_CODES:
        col = f"gemini_{c}"
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["year"] = df["year"].astype(str)
    return df


# ============================================
# fig2: Part A 高频 code 趋势(分 category)— 修复版
# ============================================
def fig2_partA_trends(df):
    print("生成 fig2: Part A 高频 code 趋势(修复版)...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    focus_codes = ["power", "safety", "engagement", "community", "accountability"]
    cats = ["CG", "VI", "TOS", "NEWS"]
    
    fig, axes = plt.subplots(len(focus_codes), 1, figsize=(10, 14), sharex=True)
    colors = {"CG": "#1f77b4", "VI": "#ff7f0e", "TOS": "#2ca02c", "NEWS": "#d62728"}
    
    for idx, code in enumerate(focus_codes):
        col = f"gemini_{code}"
        ax = axes[idx]
        
        for cat in cats:
            sub = df_year[df_year["category"] == cat]
            if len(sub) == 0:
                continue
            yearly = sub.groupby("year_num").apply(lambda g: g[col].sum() / len(g) * 100 if len(g) > 0 else 0)
            yearly_n = sub.groupby("year_num").size()
            yearly = yearly[yearly_n >= 10]
            
            if len(yearly) > 0:
                ax.plot(yearly.index, yearly.values, marker="o", label=cat,
                        color=colors[cat], linewidth=2, markersize=6)
        
        ax.set_ylabel(f"{code}\n(% sections)", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        if idx == 0:
            ax.legend(loc="upper right", ncol=4)
        ax.set_title("" if idx > 0 else "Part A platform value codes: trends by document category (Fixed)", 
                     loc="left", pad=8)
    
    axes[-1].set_xlabel("Year")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig2_partA_trends_by_category.png")
    plt.close()
    print(f"  → fig2 saved")


# ============================================
# fig3: Part B heritage codes 趋势 — 修复版
# ============================================
def fig3_partB_trends(df):
    print("生成 fig3: Part B heritage trends(修复版)...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    palette = sns.color_palette("Set2", n_colors=6)
    
    low_freq = ["B5_commercialization_culture", "B6_ai_cultural_content", "B4_traditional_craftsmanship"]
    
    label_map = {
        "B1_authenticity_claims": "B1 Authenticity",
        "B2_religious_sensitivity": "B2 Religious",
        "B3_indigenous_minority": "B3 Indigenous/Minority",
        "B4_traditional_craftsmanship": "B4 Traditional Crafts",
        "B5_commercialization_culture": "B5 Cultural Commerce",
        "B6_ai_cultural_content": "B6 AI Cultural",
    }
    
    for i, code in enumerate(CODES_B):
        col = f"gemini_{code}"
        yearly = df_year.groupby("year_num").apply(lambda g: g[col].sum() / len(g) * 100 if len(g) > 0 else 0)
        linestyle = "--" if code in low_freq else "-"
        alpha = 0.5 if code in low_freq else 1.0
        linewidth = 1.5 if code in low_freq else 2.5
        ax.plot(yearly.index, yearly.values, marker="o", label=label_map[code],
                color=palette[i], linewidth=linewidth, markersize=6, 
                linestyle=linestyle, alpha=alpha)
    
    ax.set_xlabel("Year")
    ax.set_ylabel("% of sections")
    ax.set_title("Heritage Codes (B1-B6): Differentiated Trajectories, 2020-2025")
    ax.set_ylim(0, 10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", framealpha=0.95)
    
    # 标注 B3 稳定区间
    ax.axhspan(4, 9, alpha=0.08, color="purple")
    ax.text(2025.2, 6.5, "B3 stable\nrange", fontsize=8, color="purple", style="italic", ha="left", va="center")
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig3_partB_heritage_trends.png")
    plt.close()
    print(f"  → fig3 saved")


# ============================================
# fig4: 共现矩阵(修复版,数据应该几乎一样,但重跑一次更严谨)
# ============================================
def fig4_cooccurrence(df):
    print("生成 fig4: 共现矩阵(修复版)...")
    matrix = pd.DataFrame(0.0, index=ALL_CODES, columns=ALL_CODES)
    
    for c1 in ALL_CODES:
        for c2 in ALL_CODES:
            both = ((df[f"gemini_{c1}"] == 1) & (df[f"gemini_{c2}"] == 1)).sum()
            either = ((df[f"gemini_{c1}"] == 1) | (df[f"gemini_{c2}"] == 1)).sum()
            matrix.loc[c1, c2] = both / either if either > 0 else 0
    
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(matrix, annot=True, fmt=".2f", cmap="Blues", ax=ax,
                cbar_kws={"label": "Jaccard similarity"},
                linewidths=0.3, linecolor="white", square=True,
                annot_kws={"size": 7})
    ax.set_title("Code Co-occurrence Matrix (Jaccard Similarity) — Fixed", pad=12)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig4_cooccurrence_jaccard.png")
    plt.close()
    print(f"  → fig4 saved")


# ============================================
# fig6: power-safety 共现 — 修复版(关键修订)
# ============================================
def fig6_power_safety(df):
    print("生成 fig6: power-safety 共现(修复版)...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    rows = []
    for year, grp in df_year.groupby("year_num"):
        n = len(grp)
        power = (grp["gemini_power"] == 1).sum()
        safety = (grp["gemini_safety"] == 1).sum()
        both = ((grp["gemini_power"] == 1) & (grp["gemini_safety"] == 1)).sum()
        rows.append({
            "year": year,
            "power_pct": power / n * 100,
            "safety_pct": safety / n * 100,
            "both_pct": both / n * 100,
        })
    
    d = pd.DataFrame(rows)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(d["year"], d["power_pct"], marker="o", label="Power", linewidth=2, color="#1f77b4")
    ax.plot(d["year"], d["safety_pct"], marker="s", label="Safety", linewidth=2, color="#ff7f0e")
    ax.plot(d["year"], d["both_pct"], marker="^", label="Power AND Safety (co-occur)",
            linewidth=2.5, color="#d62728", linestyle="--")
    
    ax.set_xlabel("Year")
    ax.set_ylabel("% of sections")
    ax.set_title("Power-Safety Co-occurrence over Time (Fixed)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    ax.set_ylim(0, 80)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig6_power_safety_cooccur.png")
    plt.close()
    print(f"  → fig6 saved")


# ============================================
# fig7: B3 趋势 — 修复版,标题改成稳定 narrative
# ============================================
def fig7_b3_stable(df):
    print("生成 fig7: B3 indigenous 稳定趋势(修复版)...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    yearly = df_year.groupby("year_num").apply(lambda g: g["gemini_B3_indigenous_minority"].sum() / len(g) * 100)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(yearly.index, yearly.values, marker="o", linewidth=2.5, color="#2ca02c", markersize=10)
    ax.fill_between(yearly.index, 0, yearly.values, alpha=0.2, color="#2ca02c")
    
    # 标稳定区间(4-9%)
    ax.axhspan(4, 9, alpha=0.1, color="purple", label="Stable range (4-9%)")
    
    peak_year = yearly.idxmax()
    peak_val = yearly.max()
    min_year = yearly.idxmin()
    min_val = yearly.min()
    ax.annotate(f"Peak: {peak_val:.1f}% ({peak_year})",
                xy=(peak_year, peak_val),
                xytext=(peak_year + 0.3, peak_val + 0.8),
                fontsize=9, color="#2ca02c",
                arrowprops=dict(arrowstyle="->", color="#2ca02c"))
    ax.annotate(f"Min: {min_val:.1f}% ({min_year})",
                xy=(min_year, min_val),
                xytext=(min_year - 1.2, min_val - 1),
                fontsize=9, color="#2ca02c",
                arrowprops=dict(arrowstyle="->", color="#2ca02c"))
    
    ax.set_xlabel("Year")
    ax.set_ylabel("% of sections (B3 = 1)")
    ax.set_title("B3 Indigenous/Minority Cultural Protection: Sustained Presence over Time")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 11)
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig7_b3_indigenous_trend.png")
    plt.close()
    print(f"  → fig7 saved")


def main():
    print("=" * 70)
    print("Step 47: 用修复后数据重画剩余图表")
    print("=" * 70)
    
    df = read_csv_robust(INPUT)
    df = prepare_data(df)
    print(f"\n数据集: {len(df)} sections\n")
    
    fig2_partA_trends(df)
    fig3_partB_trends(df)
    fig4_cooccurrence(df)
    fig6_power_safety(df)
    fig7_b3_stable(df)
    
    print(f"\n{'='*70}")
    print(f"完成。所有图保存到: {FIG_DIR}/")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()