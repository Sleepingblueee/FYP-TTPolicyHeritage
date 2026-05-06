"""
Heritage codes 靶向抽样
从 1245 个 .md 文件里搜含文化/宗教/传统/原住民关键词的 sections
专门抽 30 个出来,用于第二轮预试验验证 B1-B6
"""

import re
import random
from pathlib import Path
import pandas as pd

EXTRACT_MAIN = Path("data/processed/extracted/main")
EXTRACT_NEWS = Path("data/processed/extracted/news")
REPORT = Path("data/processed/11_extraction_report_v6.csv")
OUTPUT = Path("data/processed/33_heritage_targeted_sample.csv")

random.seed(42)
N_SAMPLES = 30

# 关键词分组(每组对应可能触发的 heritage codes)
KEYWORDS = {
    "religious": [
        r"\breligio", r"\breligi", r"\bsacred\b", r"\bfaith\b",
        r"\bworship", r"\britual", r"\bceremon", r"\bspiritual",
        r"\bblasphem", r"\bclergy", r"\bgod\b", r"\bdeity",
    ],
    "indigenous": [
        r"\bindigenous", r"\btribal", r"\baboriginal",
        r"\bnative\s+(?:people|community|culture|tradition)",
        r"\bethnic\s+minority", r"\bethnic\s+group",
        r"\bmarginali[sz]ed", r"\bappropriation",
    ],
    "traditional": [
        r"\btradition", r"\bheritage\b", r"\bfolklore\b",
        r"\bancestral", r"\bcustom\s+", r"\bcraftsman",
        r"\bartisan", r"\bcalligraph", r"\bopera\b",
        r"\bweav", r"\bembroid",
    ],
    "cultural": [
        r"\bcultural\s+(?:practice|expression|tradition|content|heritage|identity|sensitiv)",
        r"\bcultural\s+appropriation",
    ],
}

ALL_PATTERNS = []
for cat, patterns in KEYWORDS.items():
    for p in patterns:
        ALL_PATTERNS.append((cat, re.compile(p, re.IGNORECASE)))


def split_into_sentences(text):
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) >= 20]


def extract_heritage_sections(md_path):
    """从一个文件里找出含 heritage 关键词的 sections (3 句)"""
    text = md_path.read_text(encoding="utf-8")
    sentences = split_into_sentences(text)
    if len(sentences) < 3:
        return []
    
    found = []
    for start in range(len(sentences) - 2):
        section = " ".join(sentences[start:start+3])
        if len(section) < 200:
            continue
        
        # 检查是否命中关键词
        matched_categories = set()
        matched_keywords = []
        for cat, pattern in ALL_PATTERNS:
            if pattern.search(section):
                matched_categories.add(cat)
                m = pattern.search(section)
                matched_keywords.append(m.group(0))
        
        if matched_categories:
            found.append({
                "section_text": section,
                "section_position": f"{start+1}-{start+3}",
                "matched_categories": "|".join(sorted(matched_categories)),
                "matched_keywords": ", ".join(matched_keywords[:5]),
            })
    
    return found


def main():
    print("=" * 60)
    print("Step 33: Heritage codes 靶向抽样")
    print("=" * 60)
    
    df = pd.read_csv(REPORT)
    success = df[df["extracted_chars"] > 0].copy()
    print(f"\n候选文件总数: {len(success)}")
    
    # 扫描所有文件,收集含 heritage 关键词的 sections
    print(f"\n扫描中...")
    all_candidates = []
    
    for _, row in success.iterrows():
        md_dir = EXTRACT_NEWS if row["category"] == "NEWS" else EXTRACT_MAIN
        md_path = md_dir / row["output_file"]
        if not md_path.exists():
            continue
        
        sections = extract_heritage_sections(md_path)
        for s in sections:
            s["filename"] = row["filename"]
            s["category"] = row["category"]
            s["year"] = row["year"]
            all_candidates.append(s)
    
    print(f"找到候选 sections: {len(all_candidates)}")
    
    if len(all_candidates) == 0:
        print("没有命中 heritage 关键词的 section,需要扩展关键词列表")
        return
    
    # 按命中类别分组,尽量均衡抽样
    by_cat = {}
    for c in all_candidates:
        for cat in c["matched_categories"].split("|"):
            by_cat.setdefault(cat, []).append(c)
    
    print(f"\n按命中类别分布:")
    for cat, items in by_cat.items():
        print(f"  {cat}: {len(items)} 个 sections")
    
    # 均衡抽样:每类抽接近 N_SAMPLES/4 个,去重
    target_per_cat = max(N_SAMPLES // len(by_cat), 5)
    selected = {}  # section_text -> record(去重)
    
    for cat, items in by_cat.items():
        random.shuffle(items)
        added = 0
        for item in items:
            if item["section_text"] in selected:
                continue
            selected[item["section_text"]] = item
            added += 1
            if added >= target_per_cat:
                break
    
    # 如果不够 N_SAMPLES,从剩余里随机补
    if len(selected) < N_SAMPLES:
        remaining = [c for c in all_candidates if c["section_text"] not in selected]
        random.shuffle(remaining)
        for item in remaining[:N_SAMPLES - len(selected)]:
            selected[item["section_text"]] = item
    
    # 截取到 N_SAMPLES
    final = list(selected.values())[:N_SAMPLES]
    
    print(f"\n最终抽样: {len(final)} 个 sections")
    
    # 输出
    CODES_A = ["power", "privacy", "safety", "choice", "community",
               "engagement", "ip_protection", "improvement", "care", "accountability"]
    CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
               "B3_indigenous_minority", "B4_traditional_craftsmanship",
               "B5_commercialization_culture", "B6_ai_cultural_content"]
    ALL_CODES = CODES_A + CODES_B
    
    records = []
    for i, item in enumerate(final):
        record = {
            "sample_id": f"H{i+1:03d}",
            "category": item["category"],
            "year": item["year"],
            "filename": item["filename"],
            "section_position": item["section_position"],
            "matched_categories": item["matched_categories"],
            "matched_keywords": item["matched_keywords"],
            "section_text": item["section_text"],
        }
        for code in ALL_CODES:
            record[code] = ""
        record["human_notes"] = ""
        records.append(record)
    
    out_df = pd.DataFrame(records)
    out_df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    
    print(f"\n保存至: {OUTPUT}")
    print(f"\n下一步:")
    print(f"  1. 用 Excel 打开 {OUTPUT}")
    print(f"  2. 阅读每个 section_text(注意 matched_keywords 列告诉你为什么命中)")
    print(f"  3. 对每个 section, 在 16 个 code 列填 1 或 0(参考 codebook v2)")
    print(f"  4. 完成后告诉 Claude")


if __name__ == "__main__":
    main()