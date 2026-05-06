"""
Step 48: 一次性生成所有 9 张论文最终图表
基于修复后数据 data/processed/42_full_dataset_fixed.csv
输出 figures/ 目录下 fig1 - fig9

图清单:
  fig1: 16-code 逐年频率热力图(Part A / Part B 分隔)
  fig2: Part A 高频 codes 趋势(分 category)
  fig3: Part B heritage codes 趋势(B3 stable range 标注)
  fig4: 16x16 共现矩阵(Jaccard)
  fig5: 4 个核心 codes 在 7 个 category 上的频率(CG 拆 main/sub)
  fig6: Power-Safety co-occurrence 时间序列
  fig7: B3 单 code 时间序列(sustained presence narrative)
  fig8: CG-main vs CG-sub 全 16 codes 对比
  fig9: CG documentation architecture 演化(main vs sub 数量)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ============================================
# 路径配置
# ============================================
INPUT = Path("data/processed/42_full_dataset_fixed.csv")
FIG_DIR = Path("figures")
FIG_DIR.mkdir(exist_ok=True)

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B

LABEL_MAP = {
    "B1_authenticity_claims": "B1 Authenticity",
    "B2_religious_sensitivity": "B2 Religious",
    "B3_indigenous_minority": "B3 Indigenous/Minority",
    "B4_traditional_craftsmanship": "B4 Traditional Crafts",
    "B5_commercialization_culture": "B5 Cultural Commerce",
    "B6_ai_cultural_content": "B6 AI Cultural",
}

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


# ============================================
# 工具函数
# ============================================
def read_csv_robust(path):
    for enc in ["utf-8-sig", "utf-8", "gbk"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别 {path}")


def prepare_data(df):
    for c in ALL_CODES:
        col = f"gemini_{c}"
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["year"] = df["year"].astype(str)
    if "is_sub_page" in df.columns:
        df["is_sub_page"] = df["is_sub_page"].astype(bool)
    return df


# ============================================
# fig1: 16-code 逐年频率热力图
# ============================================
def fig1_heatmap(df):
    print("生成 fig1: 16-code 逐年频率热力图...")
    df_year = df[df["year"].isin(["2019", "2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    
    rows = []
    for c in ALL_CODES:
        col = f"gemini_{c}"
        for year, grp in df_year.groupby("year"):
            n = len(grp)
            ones = grp[col].sum()
            pct = ones / n * 100 if n > 0 else 0
            rows.append({"code": c, "year": year, "pct": pct})
    
    pivot = pd.DataFrame(rows).pivot(index="code", columns="year", values="pct")
    pivot = pivot.reindex(ALL_CODES)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlOrRd",
                cbar_kws={"label": "% of sections"}, ax=ax,
                linewidths=0.3, linecolor="white")
    ax.axhline(y=10, color="black", linewidth=2, linestyle="--", alpha=0.6)
    ax.set_title("Frequency of Each Code by Year (% of sections, 2019-2025)", pad=12)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig1_heatmap_code_by_year.png")
    plt.close()
    print(f"  → fig1 saved")


# ============================================
# fig2: Part A 高频 code 趋势(分 category)
# ============================================
def fig2_partA_trends(df):
    print("生成 fig2: Part A 高频 code 趋势(分 category)...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    focus_codes = ["power", "safety", "engagement", "community", "accountability"]
    cats = ["CG", "VI", "TOS", "NEWS"]
    colors = {"CG": "#1f77b4", "VI": "#ff7f0e", "TOS": "#2ca02c", "NEWS": "#d62728"}
    
    fig, axes = plt.subplots(len(focus_codes), 1, figsize=(10, 14), sharex=True)
    
    for idx, code in enumerate(focus_codes):
        col = f"gemini_{code}"
        ax = axes[idx]
        
        for cat in cats:
            sub = df_year[df_year["category"] == cat]
            if len(sub) == 0:
                continue
            yearly = sub.groupby("year_num").apply(
                lambda g: g[col].sum() / len(g) * 100 if len(g) > 0 else 0
            )
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
            ax.set_title("Part A platform value codes: trends by document category",
                         loc="left", pad=8)
    
    axes[-1].set_xlabel("Year")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig2_partA_trends_by_category.png")
    plt.close()
    print(f"  → fig2 saved")


# ============================================
# fig3: Part B heritage codes 趋势(B3 stable range)
# ============================================
def fig3_partB_trends(df):
    print("生成 fig3: Part B heritage codes 趋势...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    palette = sns.color_palette("Set2", n_colors=6)
    
    low_freq = ["B5_commercialization_culture", "B6_ai_cultural_content", "B4_traditional_craftsmanship"]
    
    for i, code in enumerate(CODES_B):
        col = f"gemini_{code}"
        yearly = df_year.groupby("year_num").apply(
            lambda g: g[col].sum() / len(g) * 100 if len(g) > 0 else 0
        )
        linestyle = "--" if code in low_freq else "-"
        alpha = 0.5 if code in low_freq else 1.0
        linewidth = 1.5 if code in low_freq else 2.5
        ax.plot(yearly.index, yearly.values, marker="o", label=LABEL_MAP[code],
                color=palette[i], linewidth=linewidth, markersize=6,
                linestyle=linestyle, alpha=alpha)
    
    ax.set_xlabel("Year")
    ax.set_ylabel("% of sections")
    ax.set_title("Heritage Codes (B1-B6): Differentiated Trajectories, 2020-2025")
    ax.set_ylim(0, 10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", framealpha=0.95)
    
    # B3 稳定区间
    ax.axhspan(4, 9, alpha=0.08, color="purple")
    ax.text(2025.2, 6.5, "B3 stable\nrange", fontsize=8, color="purple",
            style="italic", ha="left", va="center")
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig3_partB_heritage_trends.png")
    plt.close()
    print(f"  → fig3 saved")


# ============================================
# fig4: 16x16 共现矩阵
# ============================================
def fig4_cooccurrence(df):
    print("生成 fig4: 16x16 共现矩阵...")
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
    ax.set_title("Code Co-occurrence Matrix (Jaccard Similarity)", pad=12)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig4_cooccurrence_jaccard.png")
    plt.close()
    print(f"  → fig4 saved")


# ============================================
# fig5: 4 核心 codes × 7 categories(CG 拆 main/sub)
# ============================================
def fig5_codes_by_category(df):
    print("生成 fig5: 4 核心 codes × 7 categories(CG 拆 main/sub)...")
    
    df = df.copy()
    df["category_v2"] = df["category"].astype(str)
    df.loc[(df["category"] == "CG") & (df["is_sub_page"]), "category_v2"] = "CG-sub"
    df.loc[(df["category"] == "CG") & (~df["is_sub_page"]), "category_v2"] = "CG-main"
    
    cats = ["CG-main", "CG-sub", "VI", "TOS", "NEWS", "TRANS", "CCC"]
    color_map = {
        "CG-main": "#3a7ca5",
        "CG-sub": "#d62728",
        "VI": "#3a7ca5",
        "TOS": "#3a7ca5",
        "NEWS": "#3a7ca5",
        "TRANS": "#3a7ca5",
        "CCC": "#3a7ca5",
    }
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    focus = [
        ("power", "Power"),
        ("safety", "Safety"),
        ("B2_religious_sensitivity", "B2 Religious Sensitivity"),
        ("B3_indigenous_minority", "B3 Indigenous/Minority"),
    ]
    
    for ax, (code, title) in zip(axes, focus):
        col = f"gemini_{code}"
        rows = []
        for cat in cats:
            sub = df[df["category_v2"] == cat]
            if len(sub) > 0:
                pct = sub[col].sum() / len(sub) * 100
                rows.append({"category": cat, "pct": pct, "n": len(sub)})
        
        d = pd.DataFrame(rows)
        if len(d) == 0:
            continue
        colors = [color_map[c] for c in d["category"]]
        bars = ax.bar(d["category"], d["pct"], color=colors, edgecolor="white")
        ax.set_title(f"{title} by Document Category", fontsize=11)
        ax.set_ylabel("% of sections")
        max_y = max(d["pct"]) * 1.25 if max(d["pct"]) > 0 else 10
        ax.set_ylim(0, max_y)
        for bar, n in zip(bars, d["n"]):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_y*0.02,
                    f"n={n}", ha="center", fontsize=8, color="gray")
        ax.grid(True, alpha=0.3, axis="y")
        plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    
    fig.text(0.5, 0.01,
             "Note: CG-main = CG main pages; CG-sub = CG sub-pages (deeper-tier policy documents); "
             "CG-sub highlighted in red.",
             ha="center", fontsize=9, style="italic", color="gray")
    
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(FIG_DIR / "fig5_codes_by_category.png")
    plt.close()
    print(f"  → fig5 saved")


# ============================================
# fig6: Power-Safety co-occurrence 时间序列
# ============================================
def fig6_power_safety(df):
    print("生成 fig6: Power-Safety co-occurrence 时间序列...")
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
    ax.plot(d["year"], d["power_pct"], marker="o", label="Power",
            linewidth=2, color="#1f77b4")
    ax.plot(d["year"], d["safety_pct"], marker="s", label="Safety",
            linewidth=2, color="#ff7f0e")
    ax.plot(d["year"], d["both_pct"], marker="^", label="Power AND Safety (co-occur)",
            linewidth=2.5, color="#d62728", linestyle="--")
    
    ax.set_xlabel("Year")
    ax.set_ylabel("% of sections")
    ax.set_title("Power-Safety Co-occurrence over Time")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    ax.set_ylim(0, 80)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig6_power_safety_cooccur.png")
    plt.close()
    print(f"  → fig6 saved")


# ============================================
# fig7: B3 单 code 时间序列(sustained presence)
# ============================================
def fig7_b3_stable(df):
    print("生成 fig7: B3 indigenous 单 code 时间序列...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    yearly = df_year.groupby("year_num").apply(
        lambda g: g["gemini_B3_indigenous_minority"].sum() / len(g) * 100
    )
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(yearly.index, yearly.values, marker="o", linewidth=2.5,
            color="#2ca02c", markersize=10)
    ax.fill_between(yearly.index, 0, yearly.values, alpha=0.2, color="#2ca02c")
    
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


# ============================================
# fig8: CG-main vs CG-sub 全 16 codes 对比
# ============================================
def fig8_cg_main_vs_sub(df):
    print("生成 fig8: CG-main vs CG-sub 全 16 codes 对比...")
    
    cg = df[df["category"] == "CG"].copy()
    cg_main = cg[~cg["is_sub_page"]]
    cg_sub = cg[cg["is_sub_page"]]
    
    print(f"  CG-main: {len(cg_main)}")
    print(f"  CG-sub: {len(cg_sub)}")
    
    rows = []
    for c in ALL_CODES:
        col = f"gemini_{c}"
        main_pct = cg_main[col].sum() / len(cg_main) * 100 if len(cg_main) > 0 else 0
        sub_pct = cg_sub[col].sum() / len(cg_sub) * 100 if len(cg_sub) > 0 else 0
        rows.append({"code": c, "CG-main": main_pct, "CG-sub": sub_pct, "diff": sub_pct - main_pct})
    
    d = pd.DataFrame(rows)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    x = np.arange(len(ALL_CODES))
    width = 0.4
    
    ax.barh(x - width/2, d["CG-main"], width, label=f"CG-main (n={len(cg_main)})",
            color="#3a7ca5", edgecolor="white")
    ax.barh(x + width/2, d["CG-sub"], width, label=f"CG-sub (n={len(cg_sub)})",
            color="#d62728", edgecolor="white")
    
    ax.set_yticks(x)
    ax.set_yticklabels(ALL_CODES)
    ax.set_xlabel("% of sections")
    ax.set_title("CG Main Pages vs CG Sub-Pages: Comparison across 16 Codes")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3, axis="x")
    ax.invert_yaxis()
    
    ax.axhline(y=9.5, color="black", linewidth=1.5, linestyle="--", alpha=0.5)
    ax.text(ax.get_xlim()[1] * 0.95, 9.45, "Part A / Part B",
            ha="right", va="bottom", fontsize=9, style="italic", color="gray")
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig8_cg_main_vs_sub.png")
    plt.close()
    print(f"  → fig8 saved")
    
    # 打印对比表(供论文引用)
    print(f"\n  CG-main vs CG-sub 对比表:")
    print(f"  {'Code':<35} {'main %':>8} {'sub %':>8} {'diff':>7}")
    print(f"  " + "-" * 60)
    for _, r in d.iterrows():
        marker = " *" if abs(r["diff"]) > 5 else ""
        print(f"  {r['code']:<35} {r['CG-main']:>8.1f} {r['CG-sub']:>8.1f} "
              f"{r['diff']:>+7.1f}{marker}")


# ============================================
# fig9: CG documentation architecture 演化
# ============================================
def fig9_cg_sub_expansion(df):
    print("生成 fig9: CG documentation architecture 演化...")
    
    df_year = df[df["year"].isin(["2019", "2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    cg = df_year[df_year["category"] == "CG"]
    rows = []
    for year, grp in cg.groupby("year_num"):
        n_main = (~grp["is_sub_page"]).sum()
        n_sub = grp["is_sub_page"].sum()
        rows.append({"year": year, "CG-main": n_main, "CG-sub": n_sub})
    
    d = pd.DataFrame(rows)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(d))
    width = 0.4
    
    ax.bar(x - width/2, d["CG-main"], width, label="CG main pages",
           color="#3a7ca5", edgecolor="white")
    ax.bar(x + width/2, d["CG-sub"], width, label="CG sub-pages",
           color="#d62728", edgecolor="white")
    
    ax.set_xticks(x)
    ax.set_xticklabels(d["year"])
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of sections")
    ax.set_title("CG Documentation Architecture: Main Pages vs Sub-Pages, 2019-2025")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig9_cg_sub_expansion.png")
    plt.close()
    print(f"  → fig9 saved")


# ============================================
# 主函数
# ============================================
def main():
    print("=" * 70)
    print("Step 48: 生成所有 9 张论文最终图表")
    print("=" * 70)
    
    df = read_csv_robust(INPUT)
    df = prepare_data(df)
    print(f"\n数据集: {len(df)} sections")
    print(f"is_sub_page 分布: {df['is_sub_page'].value_counts().to_dict()}\n")
    
    fig1_heatmap(df)
    fig2_partA_trends(df)
    fig3_partB_trends(df)
    fig4_cooccurrence(df)
    fig5_codes_by_category(df)
    fig6_power_safety(df)
    fig7_b3_stable(df)
    fig8_cg_main_vs_sub(df)
    fig9_cg_sub_expansion(df)
    
    print(f"\n{'='*70}")
    print(f"完成!所有 9 张图保存到: {FIG_DIR}/")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()