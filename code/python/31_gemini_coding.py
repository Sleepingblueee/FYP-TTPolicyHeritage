"""
让 Gemini 2.5 Pro 对预试验 30 个 sections 做 zero-shot 编码
- 加载 codebook v1 作为 system prompt 的核心
- 对每个 section 单独调用 API（避免上下文污染）
- 输出 16 个 0/1 判断 + 简短理由
- 使用结构化 JSON 输出
- 失败重试 3 次
- v2: max_output_tokens 提到 8192 + thinking_budget 限制在 2048
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

# 设置代理（Clash 7897）
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"

INPUT = Path("data/processed/30_pilot_sample.csv")
OUTPUT = Path("data/processed/31_gemini_coded.csv")
CODEBOOK = Path("codebook/codebook_v1_en.md")

MODEL = "gemini-2.5-pro"
MAX_RETRIES = 3

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


def load_codebook():
    return CODEBOOK.read_text(encoding="utf-8")


def build_user_prompt(section_text, codebook_content):
    """构造发给 Gemini 的 prompt"""
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
    """从 Gemini 返回里抽出 JSON"""
    text = response_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    
    try:
        data = json.loads(text)
        return data
    except json.JSONDecodeError as e:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        raise ValueError(f"Cannot parse JSON: {e}\nRaw: {text[:500]}")


def code_one_section(client, section_text, codebook_content):
    """编码一个 section，带重试"""
    user_prompt = build_user_prompt(section_text, codebook_content)
    
    # 构造 config，thinking_config 如果 SDK 不支持就降级
    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_budget=2048),
        )
    except (AttributeError, TypeError):
        # SDK 版本不支持 thinking_config，降级
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
            print(f"    [Attempt {attempt}] {type(e).__name__}: {str(e)[:200]}")
            if attempt < MAX_RETRIES:
                time.sleep(5 * attempt)
            else:
                return None


def main():
    print("=" * 60)
    print("Step 31: Gemini 2.5 Pro 编码 30 个预试验 sections (v2)")
    print("=" * 60)
    
    codebook_content = load_codebook()
    print(f"\nCodebook 长度: {len(codebook_content)} 字符")
    
    df = pd.read_csv(INPUT)
    print(f"待编码 sections: {len(df)}")
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("请在 .env 设置 GOOGLE_API_KEY 或 GEMINI_API_KEY")
    
    client = genai.Client(api_key=api_key)
    print(f"模型: {MODEL}")
    print(f"max_output_tokens: 8192, thinking_budget: 2048")
    
    results = []
    failures = []
    
    for i, row in df.iterrows():
        sample_id = row["sample_id"]
        section_text = row["section_text"]
        print(f"\n[{i+1}/{len(df)}] {sample_id} ({row['category']}, {row['year']})")
        
        coding = code_one_section(client, section_text, codebook_content)
        
        if coding is None:
            print(f"    失败")
            failures.append(sample_id)
            record = {"sample_id": sample_id, "category": row["category"]}
            for code in ALL_CODES:
                record[f"gemini_{code}"] = ""
                record[f"gemini_reason_{code}"] = ""
            results.append(record)
            continue
        
        record = {"sample_id": sample_id, "category": row["category"]}
        n_ones = 0
        for code in ALL_CODES:
            if code in coding:
                value = coding[code].get("value", 0)
                reason = coding[code].get("reason", "")
                record[f"gemini_{code}"] = value
                record[f"gemini_reason_{code}"] = reason
                if value == 1:
                    n_ones += 1
            else:
                record[f"gemini_{code}"] = ""
                record[f"gemini_reason_{code}"] = ""
        
        print(f"    完成: {n_ones} 个 codes 判为 1")
        results.append(record)
        
        time.sleep(2)
    
    out_df = pd.DataFrame(results)
    out_df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    
    print(f"\n{'='*60}")
    print(f"完成: {len(results)} 个 sections")
    if failures:
        print(f"失败 {len(failures)} 个: {failures}")
    print(f"保存至: {OUTPUT}")


if __name__ == "__main__":
    main()