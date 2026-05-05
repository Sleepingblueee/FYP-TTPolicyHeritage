"""
第三步：把两次 CDX 查询的结果合并，做全局去重 + 按月采样 + 关键词过滤
最终输出真正要下载的快照清单

筛选策略：
- A 类（高密度文档）：digest 全局去重 + 按月最多保留 5 个 + 跨年份均衡
- B 类（低密度文档）：digest 全局去重，全部保留
- C 类（Newsroom）：URL 关键词过滤 + digest 全局去重
- 已确认无快照的 URL 不处理
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import re

# ============================================================
# 配置
# ============================================================

INPUT_DIR = Path("data/processed")
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Newsroom 关键词过滤：URL 里包含这些词才保留
NEWSROOM_KEYWORDS = [
    "community-guidelines", "community-principles",
    "policy", "policies", "rules", "guidelines",
    "safety", "trust", "integrity",
    "live", "live-",
    "virtual-gifts", "virtual-items", "monetization", "rewards",
    "enforcement", "moderation", "transparency",
    "minors", "youth", "teen", "child",
    "ban", "remove", "violation",
    "update", "change", "announce",
]

# A 类高密度文档：每月最多保留多少个版本
A_CLASS_PER_MONTH_LIMIT = 5

# 高密度类别（需要降采样）
A_CLASS_CATEGORIES = ["CG", "CG_sub", "TOS", "TRANS"]
# 低密度类别（全部保留）
B_CLASS_CATEGORIES = ["LIVE", "VI", "CCC"]
# 专题筛选类别
C_CLASS_CATEGORIES = ["NEWS"]


# ============================================================
# 工具函数
# ============================================================

def log(msg, level=0):
    """打印日志，缩进表示层级"""
    prefix = "  " * level
    print(f"{prefix}{msg}")


def parse_timestamp(ts):
    """Wayback timestamp 是 14 位字符串 YYYYMMDDHHMMSS"""
    return datetime.strptime(str(ts), "%Y%m%d%H%M%S")


def load_inventory():
    """加载两次 CDX 查询的结果，合并"""
    file1 = INPUT_DIR / "01_snapshot_inventory.csv"
    file2 = INPUT_DIR / "02_snapshot_inventory_retry.csv"
    
    log(f"加载 {file1}")
    df1 = pd.read_csv(file1, dtype={"timestamp": str, "digest": str})
    log(f"  {len(df1)} 行", 1)
    
    log(f"加载 {file2}")
    df2 = pd.read_csv(file2, dtype={"timestamp": str, "digest": str})
    log(f"  {len(df2)} 行", 1)
    
    df = pd.concat([df1, df2], ignore_index=True)
    log(f"合并后: {len(df)} 行")
    
    # 解析时间戳
    df["datetime"] = df["timestamp"].apply(parse_timestamp)
    df["year_month"] = df["datetime"].dt.to_period("M")
    df["year"] = df["datetime"].dt.year
    
    return df


def filter_a_class(df):
    """A 类：高密度文档，digest 去重 + 按月最多 5 个"""
    log("\n[A 类] 处理高密度文档（CG, CG_sub, TOS, TRANS）")
    
    a = df[df["category"].isin(A_CLASS_CATEGORIES)].copy()
    log(f"原始数据: {len(a)} 个快照", 1)
    
    # 第一步：digest 全局去重（同一份内容只留最早的快照）
    a = a.sort_values("datetime")
    a_dedup = a.drop_duplicates(subset=["digest", "category"], keep="first")
    log(f"全局 digest 去重后: {len(a_dedup)} 个独立内容版本", 1)
    
    # 第二步：按月最多 5 个
    # 按 (category, year_month) 分组，每组最多 5 个，均匀采样
    def sample_within_month(group):
        if len(group) <= A_CLASS_PER_MONTH_LIMIT:
            return group
        # 均匀采样：取首尾和中间几个
        idx = [int(i * (len(group) - 1) / (A_CLASS_PER_MONTH_LIMIT - 1)) 
               for i in range(A_CLASS_PER_MONTH_LIMIT)]
        return group.iloc[idx]
    
    a_sampled = a_dedup.groupby(["category", "year_month"], group_keys=False).apply(sample_within_month)
    log(f"按月采样后（每月最多 {A_CLASS_PER_MONTH_LIMIT} 个）: {len(a_sampled)} 个", 1)
    
    # 按类别和年份打印分布
    log("按类别+年份分布:", 1)
    pivot = a_sampled.groupby(["category", "year"]).size().unstack(fill_value=0)
    for line in pivot.to_string().split("\n"):
        log(line, 2)
    
    return a_sampled


def filter_b_class(df):
    """B 类：低密度文档，digest 去重，全部保留"""
    log("\n[B 类] 处理低密度文档（LIVE, VI, CCC）")
    
    b = df[df["category"].isin(B_CLASS_CATEGORIES)].copy()
    log(f"原始数据: {len(b)} 个快照", 1)
    
    b = b.sort_values("datetime")
    b_dedup = b.drop_duplicates(subset=["digest", "category"], keep="first")
    log(f"全局 digest 去重后: {len(b_dedup)} 个独立内容版本", 1)
    
    # 按 query_url 打印
    log("按 URL 分布:", 1)
    for url, group in b_dedup.groupby("query_url"):
        log(f"{url}: {len(group)} 个", 2)
    
    return b_dedup


def filter_c_class(df):
    """C 类：Newsroom，URL 关键词过滤 + digest 去重"""
    log("\n[C 类] 处理 Newsroom（关键词过滤）")
    
    c = df[df["category"].isin(C_CLASS_CATEGORIES)].copy()
    log(f"原始数据: {len(c)} 个快照", 1)
    
    # URL 关键词过滤
    pattern = "|".join(NEWSROOM_KEYWORDS)
    c["url_lower"] = c["original"].str.lower()
    c_filtered = c[c["url_lower"].str.contains(pattern, regex=True, na=False)]
    log(f"关键词过滤后: {len(c_filtered)} 个", 1)
    
    # digest 去重
    c_filtered = c_filtered.sort_values("datetime")
    c_dedup = c_filtered.drop_duplicates(subset=["digest"], keep="first")
    log(f"digest 去重后: {len(c_dedup)} 个独立内容版本", 1)
    
    # 抽样看 10 个 URL，确认筛选合理
    log("筛选后样本（前 10 个 URL）:", 1)
    for url in c_dedup["original"].head(10):
        log(f"{url[:100]}", 2)
    
    return c_dedup.drop(columns=["url_lower"])


def main():
    log("=" * 60)
    log("Step 3: 精筛快照清单")
    log("=" * 60)
    
    df = load_inventory()
    
    # 三类分别处理
    a_result = filter_a_class(df)
    b_result = filter_b_class(df)
    c_result = filter_c_class(df)
    
    # 合并最终下载清单
    final = pd.concat([a_result, b_result, c_result], ignore_index=True)
    final = final.sort_values(["category", "datetime"]).reset_index(drop=True)
    
    log("\n" + "=" * 60)
    log("最终下载清单")
    log("=" * 60)
    log(f"总数: {len(final)} 个快照")
    log("\n按类别:")
    for cat, count in final.groupby("category").size().items():
        log(f"  {cat}: {count}")
    
    log(f"\n按年份:")
    for year, count in final.groupby("year").size().items():
        log(f"  {year}: {count}")
    
    # 保存
    output_path = OUTPUT_DIR / "03_download_queue.csv"
    final.to_csv(output_path, index=False, encoding="utf-8-sig")
    log(f"\n保存至: {output_path}")
    
    # 估算下载量
    avg_size_kb = final["length"].astype(float).mean() / 1024
    total_mb = final["length"].astype(float).sum() / 1024 / 1024
    log(f"\n预估下载: 平均 {avg_size_kb:.0f} KB/个，总计 {total_mb:.0f} MB")
    log(f"预估时间: ~{len(final) * 1.5 / 60:.0f} 分钟（按 1.5 秒/个礼貌爬）")


if __name__ == "__main__":
    main()