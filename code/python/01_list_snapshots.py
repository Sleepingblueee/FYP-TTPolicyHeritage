"""
第一步爬虫：用 Wayback Machine 的 CDX API 列出所有政策文档的历史快照
不下载 HTML 内容，只列元数据（时间戳、状态码、内容哈希）
输出一个 CSV，让我们看到整体数据规模

CDX API 文档: https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server-webapp
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import time

# 我们要爬的所有 URL 清单
TARGETS = [
    # 主站 Community Guidelines
    {"url": "tiktok.com/community-guidelines", "category": "CG", "note": "主站根页面"},
    {"url": "tiktok.com/community-guidelines/en", "category": "CG", "note": "主站英文版"},
    {"url": "tiktok.com/community-guidelines/en/*", "category": "CG_sub", "note": "所有子页面"},
    
    # Terms of Service
    {"url": "tiktok.com/legal/page/us/terms-of-service/en", "category": "TOS", "note": "美国版"},
    {"url": "tiktok.com/legal/page/row/terms-of-service/en", "category": "TOS", "note": "ROW 版"},
    {"url": "tiktok.com/legal/page/eea/terms-of-service-nov/en", "category": "TOS", "note": "EEA 11月版"},
    
    # Virtual Items / Coins / Rewards
    {"url": "tiktok.com/legal/virtual-items", "category": "VI", "note": "通用版"},
    {"url": "tiktok.com/legal/page/row/virtual-items/en", "category": "VI", "note": "ROW 版"},
    {"url": "tiktok.com/legal/page/us/virtual-items/en", "category": "VI", "note": "美国版"},
    {"url": "tiktok.com/legal/page/global/coin-policy-eea-archive/en", "category": "VI", "note": "EEA Coin 存档"},
    {"url": "tiktok.com/legal/page/global/rewards-policy-eea/en", "category": "VI", "note": "EEA Rewards"},
    
    # 直播专属
    {"url": "tiktok.com/live/creators/en-US/rules_and_guidance/live_monetization_guidelines", "category": "LIVE", "note": "LIVE Monetization"},
    {"url": "tiktok.com/live/studio/help/article/Before-you-go-LIVE/Community-Guidelines", "category": "LIVE", "note": "LIVE Studio CG"},
    
    # Creator Code of Conduct
    {"url": "tiktok.com/creator-academy/en/article/creator-code-of-conduct", "category": "CCC", "note": "Academy 版"},
    {"url": "support.tiktok.com/en/safety-hc/account-and-user-safety/creator-code-of-conduct", "category": "CCC", "note": "Safety Hub 版"},
    
    # 辅助材料
    {"url": "newsroom.tiktok.com/en-us/*", "category": "NEWS", "note": "Newsroom 全部"},
    {"url": "tiktok.com/transparency", "category": "TRANS", "note": "透明度"},
    {"url": "tiktok.com/safety/en/policies-and-engagement", "category": "SAFETY", "note": "Safety Hub"},
]

# 时间窗口：2019-12 到 2025-12
FROM_DATE = "20191201"
TO_DATE = "20251231"

# CDX API 端点
CDX_API = "http://web.archive.org/cdx/search/cdx"


def query_cdx(url, from_date=FROM_DATE, to_date=TO_DATE):
    """
    向 CDX API 查询某个 URL 的所有历史快照
    返回每条快照的元数据
    """
    params = {
        "url": url,
        "from": from_date,
        "to": to_date,
        "output": "json",
        "fl": "timestamp,original,statuscode,digest,length,mimetype",
        "filter": "statuscode:200",  # 只要成功的快照
        "collapse": "digest",  # 用内容哈希自动去重
    }
    
    try:
        response = requests.get(CDX_API, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        if not data or len(data) < 2:
            return []
        # 第一行是表头，后面是数据
        headers = data[0]
        return [dict(zip(headers, row)) for row in data[1:]]
    except Exception as e:
        print(f"  错误: {e}")
        return []


def main():
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_snapshots = []
    
    for i, target in enumerate(TARGETS, 1):
        print(f"\n[{i}/{len(TARGETS)}] {target['url']}")
        print(f"  类别: {target['category']} | 备注: {target['note']}")
        
        snapshots = query_cdx(target["url"])
        print(f"  找到 {len(snapshots)} 个去重后的快照")
        
        for snap in snapshots:
            snap["category"] = target["category"]
            snap["note"] = target["note"]
            snap["query_url"] = target["url"]
            all_snapshots.append(snap)
        
        # 礼貌等待，不要把 IA 服务器打爆
        time.sleep(1.5)
    
    # 存成 CSV
    df = pd.DataFrame(all_snapshots)
    output_path = output_dir / "01_snapshot_inventory.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print(f"\n{'='*60}")
    print(f"完成！共 {len(df)} 个去重后的快照")
    print(f"保存至: {output_path}")
    print(f"\n按类别统计:")
    print(df.groupby("category").size().to_string())
    print(f"\n按 query_url 统计:")
    print(df.groupby("query_url").size().to_string())


if __name__ == "__main__":
    main()