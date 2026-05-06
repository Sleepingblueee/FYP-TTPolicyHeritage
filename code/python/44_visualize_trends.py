"""
全量编码可视化
- 每个 code 的逐年趋势线图
- 16 codes × 7 years heatmap
- co-occurrence matrix heatmap
- code × category 柱状图(v2: 加入 sub 类别)
- 输出 PNG 图到 figures/ 目录
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ============================================
# 路径配置
# ============================================
INPUT = Path("data/processed/42_full_dataset.csv")
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
    raise RuntimeError(f"无法识别 {path}")


def prepare_data(df):
    for c in ALL_CODES:
        col = f"gemini_{c}"
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["year"] = df["year"].astype(str)
    return df


# ============================================
# 图 1: 全样本每年频率热力图
# ============================================
def fig_overall_heatmap(df):
    print("生成图 1: 16-code 逐年频率热力图...")
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
    
    # 在 Part A 和 Part B 之间画分隔线(第 10 个 code 后)
    ax.axhline(y=10, color="black", linewidth=2, linestyle="--", alpha=0.6)
    
    ax.set_title("Frequency of Each Code by Year (% of sections, 2019-2025)", pad=12)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig1_heatmap_code_by_year.png")
    plt.close()
    print(f"  → {FIG_DIR / 'fig1_heatmap_code_by_year.png'}")


# ============================================
# 图 2: 高频 Part A code 的逐年趋势(分 category)
# ============================================
def fig_partA_trends_by_category(df):
    print("生成图 2: Part A 高频 code 逐年趋势(分 category)...")
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
        ax.set_title("" if idx > 0 else "Part A platform value codes: trends by document category", 
                     loc="left", pad=8)
    
    axes[-1].set_xlabel("Year")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig2_partA_trends_by_category.png")
    plt.close()
    print(f"  → {FIG_DIR / 'fig2_partA_trends_by_category.png'}")


# ============================================
# 图 3: Part B (Heritage) codes 逐年趋势
# ============================================
def fig_partB_trends(df):
    print("生成图 3: Part B heritage codes 逐年趋势...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    palette = sns.color_palette("Set2", n_colors=6)
    
    # B5 / B6 用虚线显示(频率太低)
    low_freq = ["B5_commercialization_culture", "B6_ai_cultural_content"]
    
    for i, code in enumerate(CODES_B):
        col = f"gemini_{code}"
        yearly = df_year.groupby("year_num").apply(lambda g: g[col].sum() / len(g) * 100 if len(g) > 0 else 0)
        label_map = {
            "B1_authenticity_claims": "B1 Authenticity",
            "B2_religious_sensitivity": "B2 Religious",
            "B3_indigenous_minority": "B3 Indigenous/Minority",
            "B4_traditional_craftsmanship": "B4 Traditional Crafts",
            "B5_commercialization_culture": "B5 Cultural Commerce",
            "B6_ai_cultural_content": "B6 AI Cultural",
        }
        label = label_map[code]
        linestyle = "--" if code in low_freq else "-"
        alpha = 0.6 if code in low_freq else 1.0
        ax.plot(yearly.index, yearly.values, marker="o", label=label,
                color=palette[i], linewidth=2, markersize=6, 
                linestyle=linestyle, alpha=alpha)
    
    ax.set_xlabel("Year")
    ax.set_ylabel("% of sections")
    ax.set_title("Heritage Codes (B1-B6): Frequency over Time, 2020-2025")
    ax.set_ylim(0, 10)  # 固定 y 轴让 0 线突出
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", framealpha=0.95)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig3_partB_heritage_trends.png")
    plt.close()
    print(f"  → {FIG_DIR / 'fig3_partB_heritage_trends.png'}")


# ============================================
# 图 4: Code co-occurrence matrix
# ============================================
def fig_cooccurrence(df):
    print("生成图 4: code 共现矩阵...")
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
    print(f"  → {FIG_DIR / 'fig4_cooccurrence_jaccard.png'}")


# ============================================
# 图 5: Code × Category 柱状图(v2: 加入 sub)
# ============================================
def fig_codes_by_category(df):
    print("生成图 5: 各 code 在不同 category 上的频率柱状图(v2: 含 sub)...")
    
    # v2 关键改动:把 sub 加进来,且突出显示
    cats = ["CG", "sub", "VI", "TOS", "NEWS", "TRANS", "CCC"]
    
    # sub 用不同颜色突出(sub 是 CG 的子页面,但治理特征独特)
    color_map = {
        "CG": "#3a7ca5",
        "sub": "#d62728",   # sub 突出红色
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
            sub = df[df["category"] == cat]
            if len(sub) > 0:
                pct = sub[col].sum() / len(sub) * 100
                rows.append({"category": cat, "pct": pct, "n": len(sub)})
        
        d = pd.DataFrame(rows)
        colors = [color_map[c] for c in d["category"]]
        bars = ax.bar(d["category"], d["pct"], color=colors, edgecolor="white")
        ax.set_title(f"{title} by Document Category", fontsize=11)
        ax.set_ylabel("% of sections")
        max_y = max(d["pct"]) * 1.25 if len(d) > 0 and max(d["pct"]) > 0 else 10
        ax.set_ylim(0, max_y)
        for bar, n in zip(bars, d["n"]):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_y*0.02,
                    f"n={n}", ha="center", fontsize=8, color="gray")
        ax.grid(True, alpha=0.3, axis="y")
    
    # 加图例说明 sub 是 CG sub-pages
    fig.text(0.5, 0.01, 
             "Note: 'sub' = CG sub-pages (deeper-tier policy documents); highlighted in red to indicate distinct governance role.",
             ha="center", fontsize=9, style="italic", color="gray")
    
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(FIG_DIR / "fig5_codes_by_category.png")
    plt.close()
    print(f"  → {FIG_DIR / 'fig5_codes_by_category.png'}")


# ============================================
# 图 6: Power-Safety 共现强度时间变化
# ============================================
def fig_power_safety_cooccur_over_time(df):
    print("生成图 6: power-safety 共现随时间变化...")
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
    ax.set_title("Power-Safety Co-occurrence over Time")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig6_power_safety_cooccur.png")
    plt.close()
    print(f"  → {FIG_DIR / 'fig6_power_safety_cooccur.png'}")


# ============================================
# 图 7: B3 Indigenous 趋势(标题改成更中性)
# ============================================
def fig_b3_special(df):
    print("生成图 7: B3 indigenous 趋势图...")
    df_year = df[df["year"].isin(["2020", "2021", "2022", "2023", "2024", "2025"])].copy()
    df_year["year_num"] = df_year["year"].astype(int)
    
    yearly = df_year.groupby("year_num").apply(lambda g: g["gemini_B3_indigenous_minority"].sum() / len(g) * 100)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(yearly.index, yearly.values, marker="o", linewidth=2.5, color="#2ca02c", markersize=10)
    ax.fill_between(yearly.index, 0, yearly.values, alpha=0.2, color="#2ca02c")
    
    peak_year = yearly.idxmax()
    peak_val = yearly.max()
    ax.annotate(f"Peak: {peak_val:.1f}% ({peak_year})",
                xy=(peak_year, peak_val),
                xytext=(peak_year + 0.5, peak_val + 1),
                fontsize=10, color="#2ca02c",
                arrowprops=dict(arrowstyle="->", color="#2ca02c"))
    
    ax.set_xlabel("Year")
    ax.set_ylabel("% of sections (B3 = 1)")
    # v2 标题改中性
    ax.set_title("B3 Indigenous/Minority Cultural Protection: Frequency over Time")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, max(yearly.values) * 1.3)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig7_b3_indigenous_trend.png")
    plt.close()
    print(f"  → {FIG_DIR / 'fig7_b3_indigenous_trend.png'}")


# ============================================
# 主函数
# ============================================
def main():
    print("=" * 70)
    print("Step 44 v2: 全量编码可视化(修复 fig5,优化 fig3/fig7)")
    print("=" * 70)
    
    df = read_csv_robust(INPUT)
    df = prepare_data(df)
    print(f"\n数据集: {len(df)} sections\n")
    
    fig_overall_heatmap(df)
    fig_partA_trends_by_category(df)
    fig_partB_trends(df)
    fig_cooccurrence(df)
    fig_codes_by_category(df)
    fig_power_safety_cooccur_over_time(df)
    fig_b3_special(df)
    
    print(f"\n{'='*70}")
    print(f"全部图表保存到: {FIG_DIR}/")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()