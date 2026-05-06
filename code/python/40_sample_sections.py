"""
全量降量切 sections
- 每个文件取 20% sections + 必含第一段
- 输出 data/processed/40_sampled_sections.csv
- 估计总量 ~6000
"""

import re
import random
import pandas as pd
from pathlib import Path
from tqdm import tqdm

EXTRACT_MAIN = Path("data/processed/extracted/main")
EXTRACT_NEWS = Path("data/processed/extracted/news")
REPORT = Path("data/processed/11_extraction_report_v6.csv")
OUTPUT = Path("data/processed/40_sampled_sections.csv")

MIN_SECTION_CHARS = 100
SAMPLE_RATIO = 0.20  # 每个文件保留 20% sections
random.seed(42)


def split_into_sentences(text):
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) >= 20]


def slice_into_sections(sentences):
    sections = []
    for start in range(0, len(sentences), 3):
        chunk = sentences[start:start+3]
        if len(chunk) < 2:
            continue
        text = " ".join(chunk)
        if len(text) < MIN_SECTION_CHARS:
            continue
        sections.append({
            "section_position": f"{start+1}-{start+len(chunk)}",
            "section_text": text,
            "n_sentences": len(chunk),
            "char_length": len(text),
        })
    return sections


def sample_sections(sections, ratio=SAMPLE_RATIO):
    """保留第一段 + 按比例从剩余里随机抽"""
    if len(sections) == 0:
        return []
    if len(sections) == 1:
        return sections
    # 第一段必含
    first = sections[0]
    # 剩余按比例抽
    remaining = sections[1:]
    n_keep = max(1, int(len(remaining) * ratio))
    sampled_rest = random.sample(remaining, min(n_keep, len(remaining)))
    return [first] + sampled_rest


def main():
    print("=" * 60)
    print("Step 40: 降量切 sections (每文件保留 20% + 首段)")
    print("=" * 60)
    
    df = pd.read_csv(REPORT)
    success = df[df["extracted_chars"] > 0].copy()
    print(f"\n候选文件: {len(success)}")
    
    all_sampled = []
    raw_total = 0
    
    for _, row in tqdm(success.iterrows(), total=len(success), desc="切分+抽样"):
        md_dir = EXTRACT_NEWS if row["category"] == "NEWS" else EXTRACT_MAIN
        md_path = md_dir / row["output_file"]
        if not md_path.exists():
            continue
        
        text = md_path.read_text(encoding="utf-8")
        sentences = split_into_sentences(text)
        sections = slice_into_sections(sentences)
        raw_total += len(sections)
        
        sampled = sample_sections(sections)
        for sec in sampled:
            sec["filename"] = row["filename"]
            sec["category"] = row["category"]
            sec["year"] = row["year"]
            sec["timestamp"] = str(row["timestamp"])
            all_sampled.append(sec)
    
    print(f"\n原始可切 sections 总数: {raw_total}")
    print(f"降量后 sections: {len(all_sampled)} (压缩比 {len(all_sampled)/raw_total*100:.1f}%)")
    
    out_df = pd.DataFrame(all_sampled)
    out_df.insert(0, "section_id", [f"S{i:06d}" for i in range(len(out_df))])
    out_df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    
    print(f"\n按 category:")
    print(out_df.groupby("category").size().to_string())
    print(f"\n按 year:")
    print(out_df.groupby("year").size().to_string())
    print(f"\n字数: 平均 {out_df['char_length'].mean():.0f}, 中位数 {out_df['char_length'].median():.0f}")
    print(f"\n保存: {OUTPUT}")


if __name__ == "__main__":
    main()