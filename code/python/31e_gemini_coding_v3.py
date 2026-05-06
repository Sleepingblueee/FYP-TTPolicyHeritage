"""
Gemini 编码 v3
- 用 codebook v3(keyword-anchored heritage + power/safety co-occurrence)
- prompt 强调"keyword 命中 + governance context = code 1"
- 只跑 heritage batch(30 个),与你 v2 那一轮 heritage 人工编码对比
"""

import os
import re
import json
import time
import argparse
import pandas as pd
from pathlib import Path
from collections import deque
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"

INPUT_HERITAGE = Path("data/processed/33_heritage_targeted_sample.csv")
OUTPUT = Path("data/processed/36_gemini_coded_v3_heritage.csv")
CODEBOOK = Path("codebook/codebook_v3_en.md")

MODEL = "gemini-2.5-pro"
WAIT_BETWEEN_CALLS = 1
RETRY_WAIT = 3
RETRY_MAX_ATTEMPTS = 6
SUPPLEMENTARY_ROUNDS = 2
SUPP_ROUND_PAUSE = 30

TRANSIENT_HINTS = ["503", "502", "504", "unavailable", "timeout",
                   "disconnect", "eof", "connection", "remoteprotocol"]

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B


SYSTEM_INSTRUCTION = """You are a research assistant performing content analysis on TikTok policy documents using codebook v3.

CRITICAL v3 RULES — INTERNALIZE THESE:

(1) POWER + SAFETY CO-OCCUR IN PROHIBITIONS.
When a section is a content prohibition ("We do not allow X", "NOT ALLOWED", "Do not post", "Do not upload", "we will remove"), code BOTH power=1 AND safety=1.
The platform's authoritative voice issuing the rule IS the power signal. The harm-prevention substance IS the safety signal. They co-occur.
Only code safety=1 (without power) if there is no platform-issued rule framing — extremely rare.

(2) HERITAGE CODES USE KEYWORD-ANCHORED JUDGMENT.
B1-B6 codes are triggered when:
   (a) The section contains a heritage keyword (see codebook keyword lists), AND
   (b) The section discusses content rules, content categories, regional exceptions, governance, or behavior categorization.

DO NOT require "substantive elaboration" beyond keyword presence + governance context. The keyword does NOT need to be the section's main topic.

Examples of v3 INCLUSIONS (these are coded 1 in v3, not 0):
- Hate speech section listing "religion" as protected attribute → B2=1
- Hate speech section listing "ethnicity" as protected attribute → B3=1
- "Regional exceptions for body exposure in common cultural practices" → B3=1
- "We do not allow paid political promotion... including traditional paid advertisements" → B4=1
- "Religious motivations of terrorism" → B2=1
- "Cultural practice" appearing in any content rule → B3=1

(3) WHEN IN DOUBT:
- For Part A platform values (except power-safety co-occurrence): code 0
- For Part B heritage codes: code 1 (research operationalizes heritage broadly)

(4) MULTIPLE CODES PER SECTION ARE EXPECTED.
A typical TikTok hate-speech section will have safety=1, power=1, B2=1, B3=1 simultaneously.

Output valid JSON. Provide a brief one-sentence reason for each code marked 1."""


def build_user_prompt(section_text, codebook_content):
    return f"""# Codebook v3

{codebook_content}

---

# Section to code

{section_text}

---

# Output instructions

Apply codebook v3. Remember:
- Content prohibitions trigger BOTH power=1 AND safety=1.
- Heritage keywords (religion, ethnic, traditional, cultural practice, etc.) within governance sections trigger B-codes, even if listed as one of many attributes.
- Multiple codes per section are expected and normal.

Output ONLY valid JSON:

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


def is_transient(exception):
    msg = (str(exception) + " " + type(exception).__name__).lower()
    return any(hint in msg for hint in TRANSIENT_HINTS)


def get_config():
    try:
        return types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_budget=2048),
        )
    except (AttributeError, TypeError):
        return types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
            max_output_tokens=8192,
        )


def code_one_section(client, section_text, codebook_content, max_attempts=RETRY_MAX_ATTEMPTS):
    user_prompt = build_user_prompt(section_text, codebook_content)
    config = get_config()
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config=config,
            )
            return parse_response(response.text)
        except Exception as e:
            err_short = f"{type(e).__name__}: {str(e)[:80]}"
            if is_transient(e):
                if attempt < max_attempts:
                    print(f"    [{attempt}/{max_attempts}] {err_short} | 等 {RETRY_WAIT}s")
                    time.sleep(RETRY_WAIT)
                else:
                    print(f"    [{attempt}/{max_attempts}] {err_short} | 队列尾")
            else:
                if attempt < 2:
                    print(f"    [硬错] {err_short} | 立即重试")
                    time.sleep(1)
                else:
                    print(f"    [硬错] {err_short} | 队列尾")
                    return None
    return None


def make_empty_record(sample_id, source, category):
    record = {"sample_id": sample_id, "source": source, "category": category}
    for code in ALL_CODES:
        record[f"gemini_{code}"] = ""
        record[f"gemini_reason_{code}"] = ""
    return record


def make_filled_record(sample_id, source, category, coding):
    record = {"sample_id": sample_id, "source": source, "category": category}
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
    return record, n_ones


def read_csv_robust(path):
    for enc in ["utf-8-sig", "utf-8", "gbk", "gb18030", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别 {path}")


def main():
    print("=" * 60)
    print("Step 31e: Gemini v3 编码 (heritage batch only)")
    print("=" * 60)
    
    codebook_content = CODEBOOK.read_text(encoding="utf-8")
    print(f"\nCodebook v3 长度: {len(codebook_content)} 字符")
    
    df = read_csv_robust(INPUT_HERITAGE)
    df = df[["sample_id", "category", "year", "section_text"]].copy()
    df["source"] = "heritage"
    print(f"待编码: {len(df)} 个 heritage sections")
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    print(f"模型: {MODEL}\n")
    
    results = {}
    queue = deque()
    for _, row in df.iterrows():
        queue.append({
            "sample_id": row["sample_id"],
            "source": row["source"],
            "category": row["category"],
            "section_text": row["section_text"],
            "year": row["year"],
        })
    
    start = time.time()
    
    print("=" * 60)
    print("主循环")
    print("=" * 60)
    initial_total = len(queue)
    processed = 0
    while queue:
        item = queue.popleft()
        processed += 1
        elapsed_min = (time.time() - start) / 60
        eta_min = (elapsed_min / processed * (initial_total - processed)) if processed > 0 else 0
        print(f"\n[{processed}/{initial_total}] {item['sample_id']} | 已 {elapsed_min:.1f}min, ETA {eta_min:.1f}min")
        
        coding = code_one_section(client, item["section_text"], codebook_content)
        
        if coding is None:
            results[item["sample_id"]] = {"item": item, "record": None}
        else:
            record, n_ones = make_filled_record(item["sample_id"], item["source"], item["category"], coding)
            results[item["sample_id"]] = {"item": item, "record": record}
            print(f"    OK: {n_ones} 个 codes 判为 1")
        
        time.sleep(WAIT_BETWEEN_CALLS)
    
    for round_idx in range(1, SUPPLEMENTARY_ROUNDS + 1):
        failed_ids = [sid for sid, v in results.items() if v["record"] is None]
        if not failed_ids:
            break
        print(f"\n{'='*60}")
        print(f"追打轮 {round_idx}/{SUPPLEMENTARY_ROUNDS}: {len(failed_ids)} 个失败")
        print(f"等 {SUPP_ROUND_PAUSE}s 让服务器降温...")
        print(f"{'='*60}")
        time.sleep(SUPP_ROUND_PAUSE)
        for i, sid in enumerate(failed_ids):
            item = results[sid]["item"]
            print(f"\n[追打 {round_idx}, {i+1}/{len(failed_ids)}] {sid}")
            coding = code_one_section(client, item["section_text"], codebook_content)
            if coding is not None:
                record, n_ones = make_filled_record(sid, item["source"], item["category"], coding)
                results[sid]["record"] = record
                print(f"    OK: {n_ones} 个 codes 判为 1")
            else:
                print(f"    仍失败")
            time.sleep(WAIT_BETWEEN_CALLS)
    
    final_records = []
    final_failures = []
    for _, row in df.iterrows():
        sid = row["sample_id"]
        v = results.get(sid)
        if v and v["record"] is not None:
            final_records.append(v["record"])
        else:
            final_failures.append(sid)
            final_records.append(make_empty_record(sid, row["source"], row["category"]))
    
    out_df = pd.DataFrame(final_records)
    out_df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    
    total_min = (time.time() - start) / 60
    print(f"\n{'='*60}")
    print(f"完成: {len(final_records) - len(final_failures)}/{len(final_records)} | 总用时 {total_min:.1f}min")
    if final_failures:
        print(f"最终失败: {final_failures}")
    print(f"保存: {OUTPUT}")


if __name__ == "__main__":
    main()