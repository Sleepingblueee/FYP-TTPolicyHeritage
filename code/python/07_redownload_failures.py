"""
重下载失败的快照
关键改进：
1. 自动从主样本/NEWS CSV 关联回 digest
2. 详细记录 HTTP 状态码
3. 503/429 限速时指数退避
4. 加 User-Agent
5. 串行下载、间隔加大到 3 秒
6. 已下载的跳过
"""

import pandas as pd
from pathlib import Path
import requests
import time
import os
import re

os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"

INPUT_DIR = Path("data/processed")
RAW_DIR = Path("data/raw")

WAIT_BASE = 3.0
TIMEOUT = 180
MAX_RETRIES = 3
RATE_LIMIT_WAIT = 60

WAYBACK_URL = "http://web.archive.org/web/{timestamp}id_/{original}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Academic Research; FYP TikTok Policy Study; contact@bnbu.edu)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def safe_filename(timestamp, digest, category):
    digest_short = re.sub(r"[^a-zA-Z0-9]", "", str(digest))[:12]
    return f"{category}_{timestamp}_{digest_short}.html"


def load_failures_with_digest():
    """加载失败列表，并从主样本/NEWS 关联回 digest"""
    fail_df = pd.read_csv(INPUT_DIR / "05_download_failures.csv", dtype={"timestamp": str})
    print(f"原始失败列表: {len(fail_df)}")
    
    # 加载主样本和 NEWS，准备关联 digest
    main_df = pd.read_csv(INPUT_DIR / "05_main_download_final.csv", dtype={"timestamp": str, "digest": str})
    news_df = pd.read_csv(INPUT_DIR / "04_news_corpus.csv", dtype={"timestamp": str, "digest": str})
    
    # 主样本 + NEWS 合并成查询表
    lookup = pd.concat([
        main_df[["timestamp", "original", "category", "digest"]],
        news_df[["timestamp", "original", "category", "digest"]],
    ], ignore_index=True)
    
    # 用 timestamp + original 关联
    fail_df = fail_df.merge(
        lookup,
        on=["timestamp", "original", "category"],
        how="left",
    )
    
    # 检查关联结果
    missing = fail_df["digest"].isna().sum()
    if missing > 0:
        print(f"  警告: {missing} 个失败项无法关联到 digest（可能是上次重复记录）")
        fail_df = fail_df.dropna(subset=["digest"])
    
    # 失败列表里同一项可能因为重试出现多次，去重
    fail_df = fail_df.drop_duplicates(subset=["timestamp", "original", "category"])
    print(f"去重后实际待重下载: {len(fail_df)}")
    
    return fail_df


def download_one(row, target_dir):
    fname = safe_filename(row["timestamp"], row["digest"], row["category"])
    fpath = target_dir / fname
    
    if fpath.exists() and fpath.stat().st_size > 5000:
        return "skipped", "exists"
    
    url = WAYBACK_URL.format(timestamp=row["timestamp"], original=row["original"])
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            
            if r.status_code == 200:
                fpath.write_bytes(r.content)
                return "success", f"size={len(r.content)}"
            
            elif r.status_code in (429, 503):
                if attempt < MAX_RETRIES:
                    wait = RATE_LIMIT_WAIT * attempt
                    print(f"      [{r.status_code}] 限速，等 {wait} 秒...")
                    time.sleep(wait)
                else:
                    return f"failed_{r.status_code}", str(r.status_code)
            
            elif r.status_code == 404:
                return "failed_404", "404"
            
            elif r.status_code == 403:
                return "failed_403", "403"
            
            else:
                if attempt < MAX_RETRIES:
                    time.sleep(5 * attempt)
                else:
                    return f"failed_{r.status_code}", str(r.status_code)
                    
        except requests.Timeout:
            if attempt < MAX_RETRIES:
                time.sleep(10 * attempt)
            else:
                return "failed_timeout", "timeout"
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(5 * attempt)
            else:
                return "failed_other", type(e).__name__


def main():
    print("=" * 60)
    print("重下载失败的快照（修复版）")
    print("=" * 60)
    
    fail_df = load_failures_with_digest()
    
    main_categories = ["CG", "CG_sub", "TOS", "VI", "LIVE", "CCC", "TRANS"]
    
    stats = {"success": 0, "skipped": 0}
    failure_log = []
    start = time.time()
    
    for i, row in fail_df.reset_index(drop=True).iterrows():
        target_dir = RAW_DIR / ("main" if row["category"] in main_categories else "news")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        status, detail = download_one(row, target_dir)
        
        if status == "success":
            stats["success"] += 1
        elif status == "skipped":
            stats["skipped"] += 1
        else:
            stats[status] = stats.get(status, 0) + 1
            failure_log.append({
                "timestamp": row["timestamp"],
                "original": row["original"],
                "category": row["category"],
                "digest": row["digest"],
                "status": status,
                "detail": detail,
            })
        
        if (i + 1) % 30 == 0 or (i + 1) == len(fail_df):
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(fail_df) - i - 1) / rate / 60 if rate > 0 else 0
            stat_str = " ".join(f"{k}={v}" for k, v in stats.items())
            print(f"  [{i+1}/{len(fail_df)}] {stat_str} | 剩余约 {remaining:.0f} 分钟")
        
        time.sleep(WAIT_BASE)
    
    print("\n" + "=" * 60)
    print("最终统计:")
    print("=" * 60)
    for status, count in sorted(stats.items()):
        print(f"  {status}: {count}")
    
    if failure_log:
        out_path = INPUT_DIR / "07_redownload_failures.csv"
        pd.DataFrame(failure_log).to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\n仍然失败的列表保存至: {out_path}")
        print(f"如需第三轮重试，重新运行此脚本（已下载的会跳过）")
    
    main_files = list((RAW_DIR / "main").glob("*.html"))
    news_files = list((RAW_DIR / "news").glob("*.html")) if (RAW_DIR / "news").exists() else []
    print(f"\n当前 data/raw/main/: {len(main_files)} 个文件")
    print(f"当前 data/raw/news/: {len(news_files)} 个文件")


if __name__ == "__main__":
    main()