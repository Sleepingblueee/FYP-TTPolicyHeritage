"""
重试上次失败的 6 个 URL
- 修复 Clash 端口 (7897)
- 自动重试 3 次
- timeout 延长到 120 秒
- 重试间隔逐渐加长
"""

import requests
import pandas as pd
from pathlib import Path
import time
import os

# 强制设置代理（防止环境变量没生效）
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"

# 上次失败的 6 个 URL
TARGETS = [
    {"url": "tiktok.com/legal/page/us/terms-of-service/en", "category": "TOS", "note": "美国版"},
    {"url": "tiktok.com/legal/page/eea/terms-of-service-nov/en", "category": "TOS", "note": "EEA 11月版"},
    {"url": "tiktok.com/legal/page/us/virtual-items/en", "category": "VI", "note": "美国版"},
    {"url": "tiktok.com/legal/page/global/rewards-policy-eea/en", "category": "VI", "note": "EEA Rewards"},
    {"url": "tiktok.com/live/studio/help/article/Before-you-go-LIVE/Community-Guidelines", "category": "LIVE", "note": "LIVE Studio CG"},
    {"url": "tiktok.com/creator-academy/en/article/creator-code-of-conduct", "category": "CCC", "note": "Academy 版"},
    {"url": "newsroom.tiktok.com/en-us/*", "category": "NEWS", "note": "Newsroom 全部"},
    {"url": "tiktok.com/transparency", "category": "TRANS", "note": "透明度"},
    {"url": "tiktok.com/safety/en/policies-and-engagement", "category": "SAFETY", "note": "Safety Hub"},
]

FROM_DATE = "20191201"
TO_DATE = "20251231"
CDX_API = "http://web.archive.org/cdx/search/cdx"
MAX_RETRIES = 3


def query_cdx_with_retry(url, from_date=FROM_DATE, to_date=TO_DATE):
    """
    带重试机制的 CDX 查询
    """
    params = {
        "url": url,
        "from": from_date,
        "to": to_date,
        "output": "json",
        "fl": "timestamp,original,statuscode,digest,length,mimetype",
        "filter": "statuscode:200",
        "collapse": "digest",
    }
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  尝试 {attempt}/{MAX_RETRIES}...")
            response = requests.get(CDX_API, params=params, timeout=120)
            response.raise_for_status()
            data = response.json()
            if not data or len(data) < 2:
                print(f"  返回空结果")
                return []
            headers = data[0]
            return [dict(zip(headers, row)) for row in data[1:]]
        except Exception as e:
            print(f"  失败: {type(e).__name__}: {str(e)[:100]}")
            if attempt < MAX_RETRIES:
                wait = attempt * 5  # 5秒、10秒、15秒
                print(f"  等待 {wait} 秒后重试...")
                time.sleep(wait)
            else:
                print(f"  达到最大重试次数，放弃")
                return None  # 用 None 区分"真的失败"和"返回空"


def main():
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_snapshots = []
    failures = []
    
    for i, target in enumerate(TARGETS, 1):
        print(f"\n[{i}/{len(TARGETS)}] {target['url']}")
        print(f"  类别: {target['category']} | 备注: {target['note']}")
        
        snapshots = query_cdx_with_retry(target["url"])
        
        if snapshots is None:
            failures.append(target)
            print(f"  最终失败，加入 failures 清单")
        else:
            print(f"  找到 {len(snapshots)} 个快照")
            for snap in snapshots:
                snap["category"] = target["category"]
                snap["note"] = target["note"]
                snap["query_url"] = target["url"]
                all_snapshots.append(snap)
        
        # 重试间隔
        time.sleep(3)
    
    # 保存
    if all_snapshots:
        df = pd.DataFrame(all_snapshots)
        output_path = output_dir / "02_snapshot_inventory_retry.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\n{'='*60}")
        print(f"成功获取 {len(df)} 个快照")
        print(f"保存至: {output_path}")
        print(f"\n按类别统计:")
        print(df.groupby("category").size().to_string())
        print(f"\n按 query_url 统计:")
        print(df.groupby("query_url").size().to_string())
    
    if failures:
        print(f"\n以下 {len(failures)} 个 URL 仍然失败:")
        for f in failures:
            print(f"  - {f['url']}")


if __name__ == "__main__":
    main()