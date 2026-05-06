"""
基于修复后的数据集 42_full_dataset_fixed.csv 重画所有可视化
- 新增维度:CG 主页面 vs CG 子页面 (is_sub_page)
- 新增 fig8:CG-main vs CG-sub 全 16 codes 对比
- fig5 改造:把 CG 拆成 CG-main 和 CG-sub
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
    if "is_sub_page" in df.columns:
        df["is_sub_page"] = df["is_sub_page"].astype(bool)
    return df


# ========== fig1: 16-code 逐年频率热力图(修复后) ==========
def fig1_heatmap(df):
    print("生成 fig1: 16-code 逐年频率热力图(修复版)...")
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
    ax.set_title("Frequency of Each Code by Year (% of sections, 2019-2025) — Fixed", pad=12)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig1_heatmap_code_by_year.png")
    plt.close()
    print(f"  → fig1 saved")


# ========== fig5 改造:CG 拆成 main/sub ==========
def fig5_codes_by_category_v2(df):
    print("生成 fig5 v2: 各 code 在不同 category 上,CG 拆成 main/sub...")
    
    # 创建增强 category 列
    df = df.copy()
    df["category_v2"] = df["category"].astype(str)
    df.loc[(df["category"] == "CG") & (df["is_sub_page"]), "category_v2"] = "CG-sub"
    df.loc[(df["category"] == "CG") & (~df["is_sub_page"]), "category_v2"] = "CG-main"
    
    cats = ["CG-main", "CG-sub", "VI", "TOS", "NEWS", "TRANS", "CCC"]
    color_map = {
        "CG-main": "#3a7ca5",
        "CG-sub": "#d62728",   # CG 子页面突出红色
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


# ========== fig8 NEW: CG-main vs CG-sub 全 16 codes 对比 ==========
def fig8_cg_main_vs_sub(df):
    print("生成 fig8 NEW: CG 主页面 vs CG 子页面全 16 codes 对比...")
    
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
    
    bars1 = ax.barh(x - width/2, d["CG-main"], width, label=f"CG-main (n={len(cg_main)})",
                    color="#3a7ca5", edgecolor="white")
    bars2 = ax.barh(x + width/2, d["CG-sub"], width, label=f"CG-sub (n={len(cg_sub)})",
                    color="#d62728", edgecolor="white")
    
    ax.set_yticks(x)
    ax.set_yticklabels(ALL_CODES)
    ax.set_xlabel("% of sections")
    ax.set_title("CG Main Pages vs CG Sub-Pages: Comparison across 16 Codes")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3, axis="x")
    ax.invert_yaxis()
    
    # 加 Part A / Part B 分隔线
    ax.axhline(y=9.5, color="black", linewidth=1.5, linestyle="--", alpha=0.5)
    ax.text(ax.get_xlim()[1] * 0.95, 9.45, "Part A / Part B", ha="right", va="bottom",
            fontsize=9, style="italic", color="gray")
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig8_cg_main_vs_sub.png")
    plt.close()
    print(f"  → fig8 saved")
    
    # 同时打印数据表(供论文引用)
    print(f"\nCG 主页面 vs CG 子页面对比表:")
    print(f"{'Code':<35} {'CG-main %':>10} {'CG-sub %':>10} {'差值':>8}")
    print("-" * 70)
    for _, r in d.iterrows():
        marker = " ★" if abs(r["diff"]) > 5 else ""
        print(f"{r['code']:<35} {r['CG-main']:>10.1f} {r['CG-sub']:>10.1f} {r['diff']:>+8.1f}{marker}")


# ========== fig9 NEW: CG-sub 在时间上的扩张(2023-2025) ==========
def fig9_cg_sub_expansion(df):
    print("生成 fig9 NEW: CG 子页面体系扩张趋势...")
    
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


def main():
    print("=" * 70)
    print("Step 46: 重画可视化(基于修复后数据)")
    print("=" * 70)
    
    df = read_csv_robust(INPUT)
    df = prepare_data(df)
    print(f"\n数据集: {len(df)} sections\n")
    
    fig1_heatmap(df)
    fig5_codes_by_category_v2(df)
    fig8_cg_main_vs_sub(df)
    fig9_cg_sub_expansion(df)
    
    print(f"\n{'='*70}")
    print(f"完成。图保存到: {FIG_DIR}/")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()