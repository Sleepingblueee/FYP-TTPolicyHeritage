"""
第五步：清理主样本 + 下载 HTML

清理：
- 去掉拼写错误 URL (authencity, commerical, 锚点)
- 去掉 en-GB 版本
- 去掉 http://（保留 https://）
- 去掉父页面被重复算成子页面的情况

下载：
- 主样本 + NEWS 辅助语料
- 断点续传（已下载的不重下）
- 每个间隔 1.5 秒
- 失败的写到失败日志，最后统一报告
"""

import pandas as pd
from pathlib import Path
import requests
import time
import os
import re
from datetime import datetime

# 强制代理
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"

INPUT_DIR = Path("data/processed")
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WAIT_BETWEEN_REQUESTS = 1.5
DOWNLOAD_TIMEOUT = 120
MAX_RETRIES = 2

# Wayback Machine 历史快照的 URL 模板
# id_ 修饰符表示要原始 HTML，不要 IA 注入的工具栏
WAYBACK_URL_TEMPLATE = "http://web.archive.org/web/{timestamp}id_/{original}"


# ============================================================
# 清理函数
# ============================================================

def clean_main_sample():
    """清理主样本，应用所有过滤规则"""
    df = pd.read_csv(
        INPUT_DIR / "04_main_download_queue.csv",
        dtype={"timestamp": str, "digest": str},
    )
    print(f"原始主样本: {len(df)}")
    
    # 规则 1: 去掉拼写错误的 URL
    typo_patterns = [
        "authencity",     # authenticity 拼错
        "commerical",     # commercial 拼错
    ]
    typo_pattern = "|".join(typo_patterns)
    typo_mask = df["original"].str.contains(typo_pattern, case=False, na=False)
    print(f"  去掉拼写错误 URL: {typo_mask.sum()} 个")
    df = df[~typo_mask]
    
    # 规则 2: 去掉 URL 锚点
    anchor_mask = df["original"].str.contains("#", na=False)
    print(f"  去掉带锚点 URL: {anchor_mask.sum()} 个")
    df = df[~anchor_mask]
    
    # 规则 3: 去掉 en-GB 版本
    engb_mask = df["original"].str.contains("/en-GB", case=False, na=False)
    print(f"  去掉 en-GB 版本: {engb_mask.sum()} 个")
    df = df[~engb_mask]
    
    # 规则 4: 去掉 http:// 版本（保留 https://）
    # 同一份内容如果同时有 http 和 https，留 https
    df["url_clean"] = df["original"].str.replace("^http://", "https://", regex=True)
    df = df.sort_values(["url_clean", "datetime"] if "datetime" in df.columns else ["url_clean", "timestamp"])
    df = df.drop_duplicates(subset=["digest"], keep="first")
    print(f"  http/https 去重后: {len(df)}")
    
    # 规则 5: TRANS 类已经只保留 2020-2021，但有些是过期跳转，再做一次 length > 5KB 过滤
    # （太小的页面通常是空壳跳转）
    df["length_int"] = pd.to_numeric(df["length"], errors="coerce").fillna(0)
    too_small = (df["length_int"] < 3000) & (df["category"].isin(["TRANS", "VI", "TOS"]))
    print(f"  去掉过小（<3KB）的法律/透明度类: {too_small.sum()} 个")
    df = df[~too_small]
    
    df = df.drop(columns=["url_clean", "length_int"])
    print(f"清理后主样本: {len(df)}")
    return df


def load_news():
    """加载 NEWS 辅助语料"""
    df = pd.read_csv(
        INPUT_DIR / "04_news_corpus.csv",
        dtype={"timestamp": str, "digest": str},
    )
    print(f"NEWS 辅助语料: {len(df)}")
    return df


# ============================================================
# 下载函数
# ============================================================

def safe_filename(timestamp, digest, category):
    """生成安全的文件名"""
    digest_short = re.sub(r"[^a-zA-Z0-9]", "", str(digest))[:12]
    return f"{category}_{timestamp}_{digest_short}.html"


def download_one(row, target_dir):
    """下载单个快照"""
    fname = safe_filename(row["timestamp"], row["digest"], row["category"])
    fpath = target_dir / fname
    
    if fpath.exists() and fpath.stat().st_size > 1000:
        return "skipped"  # 已存在
    
    url = WAYBACK_URL_TEMPLATE.format(
        timestamp=row["timestamp"],
        original=row["original"],
    )
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
            r.raise_for_status()
            fpath.write_bytes(r.content)
            return "success"
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(3)
            else:
                return f"failed: {type(e).__name__}"


def download_corpus(df, name, sub_dir):
    """下载一组快照"""
    target = OUTPUT_DIR / sub_dir
    target.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"开始下载 {name}: {len(df)} 个文件 → {target}")
    print(f"预估时间: {len(df) * WAIT_BETWEEN_REQUESTS / 60:.0f} 分钟")
    print(f"{'='*60}")
    
    stats = {"success": 0, "skipped": 0, "failed": 0}
    failures = []
    start = time.time()
    
    for i, row in df.reset_index(drop=True).iterrows():
        result = download_one(row, target)
        
        if result == "success":
            stats["success"] += 1
        elif result == "skipped":
            stats["skipped"] += 1
        else:
            stats["failed"] += 1
            failures.append({
                "timestamp": row["timestamp"],
                "original": row["original"],
                "category": row["category"],
                "reason": result,
            })
        
        # 每 50 个打印一次进度
        if (i + 1) % 50 == 0 or (i + 1) == len(df):
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(df) - i - 1) / rate / 60 if rate > 0 else 0
            print(f"  [{i+1}/{len(df)}] 成功 {stats['success']} 跳过 {stats['skipped']} 失败 {stats['failed']} | 剩余约 {remaining:.0f} 分钟")
        
        time.sleep(WAIT_BETWEEN_REQUESTS)
    
    print(f"\n{name} 完成:")
    print(f"  成功: {stats['success']}")
    print(f"  跳过（已存在）: {stats['skipped']}")
    print(f"  失败: {stats['failed']}")
    
    return failures


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("Step 5: 清理主样本 + 下载 HTML")
    print("=" * 60)
    
    # 清理主样本
    main_df = clean_main_sample()
    main_path = INPUT_DIR / "05_main_download_final.csv"
    main_df.to_csv(main_path, index=False, encoding="utf-8-sig")
    print(f"\n清理后主样本保存至: {main_path}")
    
    # 加载 NEWS
    news_df = load_news()
    
    # 下载主样本
    main_failures = download_corpus(main_df, "主样本", "main")
    
    # 下载 NEWS
    news_failures = download_corpus(news_df, "NEWS 辅助", "news")
    
    # 失败日志
    all_failures = main_failures + news_failures
    if all_failures:
        fail_path = INPUT_DIR / "05_download_failures.csv"
        pd.DataFrame(all_failures).to_csv(fail_path, index=False, encoding="utf-8-sig")
        print(f"\n失败列表保存至: {fail_path}")
        print(f"如需重试，重新运行此脚本（会自动跳过已下载的）")
    
    print("\n" + "=" * 60)
    print("第二步全部完成")
    print("=" * 60)
    print(f"主样本下载到: data/raw/main/")
    print(f"NEWS 辅助下载到: data/raw/news/")


if __name__ == "__main__":
    main()