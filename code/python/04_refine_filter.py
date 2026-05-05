"""
第四步：在 03 的基础上做精细化筛选

主要改动：
1. NEWS 类从主样本拿掉，单独存为 process tracing 辅助语料
   - 按 URL 折叠：每个 unique URL 只保留最早的快照
   - 不进入 LLM 编码 pipeline
2. CG_sub 类改为"按每个具体 URL 每月最多 5 个"采样
   - 让每个子页面（safety-civility 等）独立纵向覆盖
3. TRANS 只保留 2020-2021 数据作为辅助
4. VI ROW 366 个全部保留，下载后做正文级去重
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

INPUT_PATH = Path("data/processed/03_download_queue.csv")
OUTPUT_DIR = Path("data/processed")


def log(msg, level=0):
    print(f"{'  ' * level}{msg}")


def main():
    log("=" * 60)
    log("Step 4: 精细化筛选")
    log("=" * 60)
    
    # 加载 03 的输出
    df = pd.read_csv(INPUT_PATH, dtype={"timestamp": str, "digest": str})
    df["datetime"] = pd.to_datetime(df["timestamp"], format="%Y%m%d%H%M%S")
    df["year_month"] = df["datetime"].dt.to_period("M")
    df["year"] = df["datetime"].dt.year
    log(f"加载 03 输出: {len(df)} 个快照")
    
    # ============================================================
    # 1. 把 NEWS 从主样本拿出来，单独处理
    # ============================================================
    log("\n[1] 处理 NEWS 类（拿出来单独存档）")
    news = df[df["category"] == "NEWS"].copy()
    log(f"原始 NEWS: {len(news)} 个", 1)
    
    # 按 URL 折叠：每个 unique URL 只保留最早的快照
    # 先把追踪参数去掉，让同一个 URL 不会因为参数不同被分成多份
    news["url_clean"] = news["original"].str.split("?").str[0].str.rstrip("/")
    news = news.sort_values("datetime")
    news_dedup = news.drop_duplicates(subset=["url_clean"], keep="first")
    log(f"按 unique URL 折叠后: {len(news_dedup)} 个", 1)
    
    log(f"按年份分布:", 1)
    for year, count in news_dedup.groupby("year").size().items():
        log(f"{year}: {count}", 2)
    
    # 单独保存
    news_path = OUTPUT_DIR / "04_news_corpus.csv"
    news_dedup.drop(columns=["url_clean"]).to_csv(news_path, index=False, encoding="utf-8-sig")
    log(f"NEWS 辅助语料保存至: {news_path}", 1)
    
    # ============================================================
    # 2. CG_sub 重新采样：按每个具体 URL 每月最多 5 个
    # ============================================================
    log("\n[2] 处理 CG_sub 类（按每个具体 URL 重新采样）")
    
    # 先从 03 输出里把 CG_sub 拿出来
    cg_sub_filtered = df[df["category"] == "CG_sub"].copy()
    log(f"03 输出中 CG_sub: {len(cg_sub_filtered)} 个", 1)
    log("但这是 03 阶段按 category 折叠后的结果，子页面分布可能不均", 1)
    
    # 我们需要回到 01 + 02 的原始数据重新采样 CG_sub
    log("回到原始数据重新采样...", 1)
    raw1 = pd.read_csv(OUTPUT_DIR / "01_snapshot_inventory.csv", dtype={"timestamp": str, "digest": str})
    raw2 = pd.read_csv(OUTPUT_DIR / "02_snapshot_inventory_retry.csv", dtype={"timestamp": str, "digest": str})
    raw = pd.concat([raw1, raw2], ignore_index=True)
    raw["datetime"] = pd.to_datetime(raw["timestamp"], format="%Y%m%d%H%M%S")
    raw["year_month"] = raw["datetime"].dt.to_period("M")
    raw["year"] = raw["datetime"].dt.year
    
    # 把追踪参数去掉，提取每个 unique 子页面 URL
    cg_sub_raw = raw[raw["category"] == "CG_sub"].copy()
    cg_sub_raw["url_clean"] = cg_sub_raw["original"].str.split("?").str[0].str.rstrip("/")
    log(f"原始 CG_sub: {len(cg_sub_raw)} 个", 1)
    log(f"unique 子页面 URL: {cg_sub_raw['url_clean'].nunique()} 个", 1)
    
    # 全局 digest 去重
    cg_sub_raw = cg_sub_raw.sort_values("datetime")
    cg_sub_dedup = cg_sub_raw.drop_duplicates(subset=["digest"], keep="first")
    log(f"全局 digest 去重后: {len(cg_sub_dedup)} 个", 1)
    
    # 按每个 url_clean 每月最多 5 个采样
    def sample_per_url_per_month(group, limit=5):
        if len(group) <= limit:
            return group
        idx = [int(i * (len(group) - 1) / (limit - 1)) for i in range(limit)]
        return group.iloc[idx]
    
    cg_sub_resampled = cg_sub_dedup.groupby(
        ["url_clean", "year_month"], group_keys=False
    ).apply(sample_per_url_per_month, limit=5)
    log(f"按 [URL × 月] 采样后: {len(cg_sub_resampled)} 个", 1)
    
    # 打印每个子页面的覆盖情况
    log("各子页面快照数:", 1)
    for url, count in cg_sub_resampled.groupby("url_clean").size().sort_values(ascending=False).items():
        log(f"{url[-60:]}: {count}", 2)
    
    cg_sub_resampled = cg_sub_resampled.drop(columns=["url_clean"])
    
    # ============================================================
    # 3. TRANS 只保留 2020-2021
    # ============================================================
    log("\n[3] 处理 TRANS 类（只保留 2020-2021）")
    trans = df[df["category"] == "TRANS"].copy()
    log(f"原始 TRANS: {len(trans)} 个", 1)
    trans_filtered = trans[trans["year"].isin([2020, 2021])]
    log(f"保留 2020-2021 后: {len(trans_filtered)} 个", 1)
    
    # ============================================================
    # 4. VI / LIVE / CCC / CG / TOS：从 03 输出里直接保留
    # ============================================================
    log("\n[4] 其他类别（CG, TOS, VI, LIVE, CCC）直接保留 03 的筛选结果")
    keep_categories = ["CG", "TOS", "VI", "LIVE", "CCC"]
    other = df[df["category"].isin(keep_categories)].copy()
    log(f"其他类别保留: {len(other)} 个", 1)
    for cat, count in other.groupby("category").size().items():
        log(f"{cat}: {count}", 2)
    
    # ============================================================
    # 5. 合并最终主样本下载清单（不含 NEWS）
    # ============================================================
    log("\n[5] 合并最终主样本下载清单")
    main_sample = pd.concat([
        other,
        cg_sub_resampled,
        trans_filtered,
    ], ignore_index=True)
    main_sample = main_sample.sort_values(["category", "datetime"]).reset_index(drop=True)
    
    log(f"主样本总数: {len(main_sample)} 个", 1)
    log("按类别:", 1)
    for cat, count in main_sample.groupby("category").size().items():
        log(f"{cat}: {count}", 2)
    log("按年份:", 1)
    for year, count in main_sample.groupby("year").size().items():
        log(f"{year}: {count}", 2)
    
    # 主样本保存
    main_path = OUTPUT_DIR / "04_main_download_queue.csv"
    main_sample.to_csv(main_path, index=False, encoding="utf-8-sig")
    log(f"\n主样本下载清单保存至: {main_path}")
    
    # 估算
    avg_kb = main_sample["length"].astype(float).mean() / 1024
    total_mb = main_sample["length"].astype(float).sum() / 1024 / 1024
    log(f"主样本预估下载: 平均 {avg_kb:.0f} KB/个，总计 {total_mb:.0f} MB")
    log(f"主样本预估时间: ~{len(main_sample) * 1.5 / 60:.0f} 分钟")
    
    log("\nNEWS 辅助语料另外存档（不进 LLM 编码）:")
    news_kb = news_dedup["length"].astype(float).mean() / 1024
    news_mb = news_dedup["length"].astype(float).sum() / 1024 / 1024
    log(f"NEWS 数: {len(news_dedup)} 个，平均 {news_kb:.0f} KB/个，总计 {news_mb:.0f} MB", 1)
    log(f"NEWS 预估时间: ~{len(news_dedup) * 1.5 / 60:.0f} 分钟", 1)
    
    log("\n" + "=" * 60)
    log("总下载预估")
    log("=" * 60)
    total = len(main_sample) + len(news_dedup)
    log(f"主样本 + NEWS 辅助 = {len(main_sample)} + {len(news_dedup)} = {total} 个")
    log(f"总时间: ~{total * 1.5 / 60:.0f} 分钟")
    log(f"总大小: ~{total_mb + news_mb:.0f} MB")


if __name__ == "__main__":
    main()