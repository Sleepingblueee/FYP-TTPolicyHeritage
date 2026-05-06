"""
补跑 31 号失败的 sections
- 只针对失败的 sample_id
- 每次调用之间等 30 秒,避开 503 拥堵
- 最多 5 次重试,每次重试间隔指数退避
"""

import os
import re
import json
import time
import pandas as pd
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"

INPUT_SAMPLE = Path("data/processed/30_pilot_sample.csv")
INPUT_GEMINI = Path("data/processed/31_gemini_coded.csv")
OUTPUT = Path("data/processed/31_gemini_coded.csv")  # 覆盖原文件
CODEBOOK = Path("codebook/codebook_v1_en.md")

MODEL = "gemini-2.5-pro"
MAX_RETRIES = 5
WAIT_BETWEEN_CALLS = 30  # 秒

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B


SYSTEM_INSTRUCTION = """You are a research assistant performing content analysis on TikTok policy documents. You apply a fixed codebook to assign binary (1=present, 0=absent) judgments for 16 codes to each section of policy text.

You must follow the codebook's definitions and decision rules exactly. When in doubt, code 0. False negatives are preferred over false positives.

Codes A1-A10 are platform values from Su & Chan (2025). Codes B1-B6 are heritage-specific codes that REQUIRE explicit cultural, religious, traditional, or indigenous context — do not infer cultural relevance from generic terms.

Each section receives 16 independent binary judgments. A section can have multiple 1s.

Always output valid JSON in the exact schema specified. Provide a brief one-sentence reason for each code marked 1; for codes marked 0, no reason is needed."""


def build_user_prompt(section_text, codebook_content):
    return f"""# Codebook

{codebook_content}

---

# Section to code

{section_text}

---

# Output instructions

Apply the codebook to the section above. Output ONLY a valid JSON object with this exact schema (no markdown fences, no extra commentary):

{{
  "power": {{"value": 0 or 1, "reason": "brief reason if 1, empty string if 0"}},
  "privacy": {{"value": 0 or 1, "reason": "..."}},
  "safety": {{"value": 0 or 1, "reason": "..."}},
  "choice": {{"value": 0 or 1, "reason": "..."}},
  "community": {{"value": 0 or 1, "reason": "..."}},
  "engagement": {{"value": 0 or 1, "reason": "..."}},
  "ip_protection": {{"value": 0 or 1, "reason": "..."}},
  "improvement": {{"value": 0 or 1, "reason": "..."}},
  "care": {{"value": 0 or 1, "reason": "..."}},
  "accountability": {{"value": 0 or 1, "reason": "..."}},
  "B1_authenticity_claims": {{"value": 0 or 1, "reason": "..."}},
  "B2_religious_sensitivity": {{"value": 0 or 1, "reason": "..."}},
  "B3_indigenous_minority": {{"value": 0 or 1, "reason": "..."}},
  "B4_traditional_craftsmanship": {{"value": 0 or 1, "reason": "..."}},
  "B5_commercialization_culture": {{"value": 0 or 1, "reason": "..."}},
  "B6_ai_cultural_content": {{"value": 0 or 1, "reason": "..."}}
}}"""


def parse_response(response_text):
    text = response_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def code_one_section(client, section_text, codebook_content):
    user_prompt = build_user_prompt(section_text, codebook_content)
    
    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_budget=2048),
        )
    except (AttributeError, TypeError):
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
            max_output_tokens=8192,
        )
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config=config,
            )
            return parse_response(response.text)
        except Exception as e:
            wait = 15 * (2 ** (attempt - 1))  # 15, 30, 60, 120, 240
            print(f"    [Attempt {attempt}] {type(e).__name__}: {str(e)[:150]}")
            if attempt < MAX_RETRIES:
                print(f"    等 {wait} 秒后重试...")
                time.sleep(wait)
            else:
                return None


def main():
    print("=" * 60)
    print("Step 31b: 补跑失败的 sections")
    print("=" * 60)
    
    samples_df = pd.read_csv(INPUT_SAMPLE)
    gemini_df = pd.read_csv(INPUT_GEMINI)
    codebook_content = CODEBOOK.read_text(encoding="utf-8")
    
    # 找出失败的 (gemini_power 列为空)
    failed_mask = gemini_df["gemini_power"].isna() | (gemini_df["gemini_power"] == "")
    failed_ids = gemini_df.loc[failed_mask, "sample_id"].tolist()
    print(f"\n待补跑: {len(failed_ids)} 个 — {failed_ids}")
    
    if not failed_ids:
        print("没有需要补跑的,退出。")
        return
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    still_failed = []
    
    for i, sample_id in enumerate(failed_ids):
        sample_row = samples_df[samples_df["sample_id"] == sample_id].iloc[0]
        section_text = sample_row["section_text"]
        
        print(f"\n[{i+1}/{len(failed_ids)}] {sample_id} ({sample_row['category']}, {sample_row['year']})")
        
        coding = code_one_section(client, section_text, codebook_content)
        
        if coding is None:
            print(f"    仍然失败")
            still_failed.append(sample_id)
        else:
            n_ones = 0
            row_idx = gemini_df[gemini_df["sample_id"] == sample_id].index[0]
            for code in ALL_CODES:
                if code in coding:
                    value = coding[code].get("value", 0)
                    reason = coding[code].get("reason", "")
                    gemini_df.at[row_idx, f"gemini_{code}"] = value
                    gemini_df.at[row_idx, f"gemini_reason_{code}"] = reason
                    if value == 1:
                        n_ones += 1
            print(f"    完成: {n_ones} 个 codes 判为 1")
        
        if i < len(failed_ids) - 1:
            print(f"    等 {WAIT_BETWEEN_CALLS} 秒...")
            time.sleep(WAIT_BETWEEN_CALLS)
    
    gemini_df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    
    print(f"\n{'='*60}")
    success_count = len(failed_ids) - len(still_failed)
    print(f"补跑成功: {success_count}/{len(failed_ids)}")
    if still_failed:
        print(f"仍然失败: {still_failed}")
        print(f"建议:等 1-2 小时之后再跑一次,或者今天先用现有 {30-len(still_failed)} 个数据做对比")
    print(f"已写回: {OUTPUT}")


if __name__ == "__main__":
    main()