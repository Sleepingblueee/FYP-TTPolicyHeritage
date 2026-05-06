"""跑 41 时实时看进度,每 10 秒刷新"""
import time
import pandas as pd
from pathlib import Path

OUTPUT = Path("data/processed/41_full_coded.csv")
INPUT = Path("data/processed/40_sampled_sections.csv")

while True:
    try:
        total = pd.read_csv(INPUT, encoding="utf-8-sig", usecols=["section_id"]).shape[0]
        done = pd.read_csv(OUTPUT, encoding="utf-8-sig", usecols=["section_id"]).shape[0] if OUTPUT.exists() else 0
        pct = done / total * 100 if total > 0 else 0
        print(f"\r进度: {done}/{total} ({pct:.1f}%)", end="", flush=True)
    except Exception as e:
        print(f"\r等待数据... ({e})", end="", flush=True)
    time.sleep(10)