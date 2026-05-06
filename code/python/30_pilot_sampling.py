"""
预试验抽样：从 1245 个 .md 文件里随机抽 30 个 sections
- 按文件类别分层抽样（保证 CG/VI/TOS 等都覆盖）
- 每个文件只取一个 section（三句话）
- 输出一个 CSV，包含 section 内容 + 16 列空白编码字段
"""

import re
import random
import pandas as pd
from pathlib import Path

EXTRACT_MAIN = Path("data/processed/extracted/main")
EXTRACT_NEWS = Path("data/processed/extracted/news")
REPORT = Path("data/processed/11_extraction_report_v6.csv")
OUTPUT = Path("data/processed/30_pilot_sample.csv")

random.seed(42)  # 固定随机种子，保证可复现

N_SAMPLES = 30

# 16 个 codes
CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B


def split_into_sentences(text):
    """简单的英文句子切分。不完美但够用。"""
    # 去掉 markdown 标题符号 ##
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    # 简单按 . ! ? 切分（保留分隔符）
    sentences = re.split(r"(?<=[.!?])\s+", text)
    # 去掉太短的（<20 字符，多是标题或残片）
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 20]
    return sentences


def extract_random_section(md_path, min_section_chars=200):
    """
    从一个 .md 文件中随机抽取一个三句一段的 section
    返回 section 文本 + 在文件中的位置信息
    """
    text = md_path.read_text(encoding="utf-8")
    sentences = split_into_sentences(text)
    
    if len(sentences) < 3:
        return None  # 文件太短，跳过
    
    # 随机选一个起始位置（确保后面还有 2 句）
    max_start = len(sentences) - 3
    
    # 多试几次，确保选到的 section 不太短
    for _ in range(10):
        start = random.randint(0, max_start)
        section = " ".join(sentences[start:start+3])
        if len(section) >= min_section_chars:
            return {
                "section_text": section,
                "section_position": f"{start+1}-{start+3}",
                "total_sentences": len(sentences),
            }
    
    # 试 10 次都没找到合格的 section，返回最长的那一个
    return None


def main():
    print("=" * 60)
    print("Step 30: 预试验抽样")
    print("=" * 60)
    
    # 加载提取报告
    df = pd.read_csv(REPORT)
    success = df[df["extracted_chars"] > 0].copy()
    
    print(f"\n可用提取文件总数: {len(success)}")
    print(f"按类别:")
    for cat, count in success.groupby("category").size().items():
        print(f"  {cat}: {count}")
    
    # 按类别分层抽样
    # 我们手头各类别比例: CG 699, VI 269, NEWS 120, TOS 107, TRANS 40, CCC 10
    # 总 1245
    # 30 个样本按比例分配（向上取整保证小类别也有样本）
    print(f"\n分层抽样目标（共 {N_SAMPLES} 个）:")
    total = len(success)
    sample_plan = {}
    for cat, group in success.groupby("category"):
        proportion = len(group) / total
        # 向上取整，但保证至少 2 个（除非该类总数 < 2）
        n = max(2, round(proportion * N_SAMPLES))
        n = min(n, len(group))
        sample_plan[cat] = n
        print(f"  {cat}: {n} 个 (占总体 {proportion*100:.1f}%)")
    
    # 调整使总和正好 = N_SAMPLES
    current = sum(sample_plan.values())
    if current > N_SAMPLES:
        # 从最大的类别里减掉
        excess = current - N_SAMPLES
        largest = max(sample_plan, key=sample_plan.get)
        sample_plan[largest] -= excess
    elif current < N_SAMPLES:
        # 加到最大的类别里
        deficit = N_SAMPLES - current
        largest = max(sample_plan, key=sample_plan.get)
        sample_plan[largest] += deficit
    
    print(f"\n调整后总计: {sum(sample_plan.values())}")
    
    # 真正抽样
    sampled_records = []
    for cat, n in sample_plan.items():
        cat_files = success[success["category"] == cat]
        # 随机抽 n 个文件
        sampled_files = cat_files.sample(n=n, random_state=42)
        
        for _, row in sampled_files.iterrows():
            # 找到这个文件
            md_dir = EXTRACT_NEWS if cat == "NEWS" else EXTRACT_MAIN
            md_path = md_dir / row["output_file"]
            
            if not md_path.exists():
                print(f"  警告: 文件不存在 {md_path}")
                continue
            
            section = extract_random_section(md_path)
            if section is None:
                print(f"  警告: 无法从 {md_path.name} 抽到合格 section")
                continue
            
            record = {
                "sample_id": f"S{len(sampled_records)+1:03d}",
                "category": cat,
                "year": row["year"],
                "filename": row["filename"],
                "section_position": section["section_position"],
                "section_text": section["section_text"],
            }
            # 加 16 列空白编码字段
            for code in ALL_CODES:
                record[code] = ""  # 留给你和 Gemini 填
            # 加一列给你写理由（可选）
            record["human_notes"] = ""
            sampled_records.append(record)
    
    # 保存
    out_df = pd.DataFrame(sampled_records)
    out_df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    
    print(f"\n{'='*60}")
    print(f"抽样完成: {len(out_df)} 个 sections")
    print(f"保存至: {OUTPUT}")
    print(f"\n下一步:")
    print(f"  1. 用 Excel 打开 {OUTPUT}")
    print(f"  2. 阅读每个 section 的 section_text 列")
    print(f"  3. 对每个 section, 在 16 个 code 列填 1 或 0")


if __name__ == "__main__":
    main()