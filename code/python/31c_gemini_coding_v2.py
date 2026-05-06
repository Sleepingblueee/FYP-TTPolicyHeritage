"""
Gemini 编码 v2.2 — 激进提速版
- 重试间隔 3 秒固定(不再翻倍/不再 15 秒)
- 失败后塞回队列尾,主循环结束后追打 2 轮
- 调用间隔 1 秒
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

INPUT_PILOT = Path("data/processed/30_pilot_sample.csv")
INPUT_HERITAGE = Path("data/processed/33_heritage_targeted_sample.csv")
OUTPUT = Path("data/processed/34_gemini_coded_v2.csv")
CODEBOOK = Path("codebook/codebook_v2_en.md")

MODEL = "gemini-2.5-pro"

# 激进重试参数
WAIT_BETWEEN_CALLS = 1     # 调用间隔
RETRY_WAIT = 3             # 瞬时错误重试间隔
RETRY_MAX_ATTEMPTS = 6     # 单 section 内最多重试次数
SUPPLEMENTARY_ROUNDS = 2   # 主循环结束后追打几轮失败队列
SUPP_ROUND_PAUSE = 30      # 每轮追打前等多久(让服务器降温)

TRANSIENT_HINTS = ["503", "502", "504", "unavailable", "timeout",
                   "disconnect", "eof", "connection", "remoteprotocol"]

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B


SYSTEM_INSTRUCTION = """You are a research assistant performing content analysis on TikTok policy documents. You apply a fixed codebook to assign binary (1=present, 0=absent) judgments for 16 codes to each section of policy text.

CRITICAL CODING DISCIPLINE:
1. Follow the codebook's "DO NOT code 1 if" rules exactly. These rules are NON-NEGOTIABLE.
2. When in doubt, code 0. False negatives are preferred over false positives.
3. Read the codebook's "Quick Reference Anti-patterns" table before each judgment.

COMMON MISTAKES TO AVOID — DO NOT REPEAT THESE:
- "We do not permit X" / "Do not post Y" → This is SAFETY only. Do NOT code as power. Do NOT code as engagement. Content prohibitions are safety.
- "Subject to terms" / "you acknowledge and agree" / "all sales final" → These are routine TOS/commercial language. They do NOT warrant power.
- "Learn more in our Creator Academy / Help Center / Safety Center" → This is educational reference, NOT care. Care requires explicit language about helping users in distress, harm, or wellbeing crises.
- Mentions of "creators" or "our community" alone → NOT community. Community requires the section to invoke them as a valued, cherished collective. Mere reference as audience or rule-recipient is NOT enough.
- "Community Guidelines" used only in document title or referring to the document → NOT community.
- "Religion" appearing only in a list of protected attributes (e.g., "race, ethnicity, religion") → NOT B2. B2 requires substantive engagement with religious content.
- General misinformation, deepfakes, or hate speech rules → NOT heritage codes (B1-B6) unless cultural/religious/traditional/indigenous context is explicit.

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

Apply the codebook to the section above. Before assigning each code, mentally check the "DO NOT code 1 if" rules. When uncertain, code 0.

Output ONLY a valid JSON object with this exact schema (no markdown fences, no extra commentary):

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
    """编码一个 section,激进短间隔重试"""
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
                # 硬性错误(JSON 解析等):重试 2 次,失败就丢队列尾
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
    raise RuntimeError(f"无法识别 {path} 的编码")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["pilot", "heritage", "both"], default="both")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Step 31c: Gemini v2.2 (激进提速)")
    print(f"重试: {RETRY_MAX_ATTEMPTS} 次 × {RETRY_WAIT}s 间隔 + {SUPPLEMENTARY_ROUNDS} 轮追打")
    print("=" * 60)
    
    codebook_content = CODEBOOK.read_text(encoding="utf-8")
    print(f"\nCodebook v2 长度: {len(codebook_content)} 字符")
    
    dfs = []
    if args.source in ("pilot", "both"):
        df_pilot = read_csv_robust(INPUT_PILOT)[["sample_id", "category", "year", "section_text"]].copy()
        df_pilot["source"] = "pilot"
        dfs.append(df_pilot)
        print(f"  pilot: {len(df_pilot)}")
    if args.source in ("heritage", "both"):
        if INPUT_HERITAGE.exists():
            df_h = read_csv_robust(INPUT_HERITAGE)[["sample_id", "category", "year", "section_text"]].copy()
            df_h["source"] = "heritage"
            dfs.append(df_h)
            print(f"  heritage: {len(df_h)}")
    
    df = pd.concat(dfs, ignore_index=True)
    total = len(df)
    print(f"待编码: {total}")
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    print(f"模型: {MODEL}\n")
    
    # 主存储:sample_id -> record
    results = {}
    # 失败队列
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
    
    # 主循环
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
        print(f"\n[{processed}/{initial_total}] {item['sample_id']} ({item['source']}, {item['category']}) | 已 {elapsed_min:.1f}min, ETA {eta_min:.1f}min")
        
        coding = code_one_section(client, item["section_text"], codebook_content)
        
        if coding is None:
            results[item["sample_id"]] = {"item": item, "record": None}
        else:
            record, n_ones = make_filled_record(item["sample_id"], item["source"], item["category"], coding)
            results[item["sample_id"]] = {"item": item, "record": record}
            print(f"    OK: {n_ones} 个 codes 判为 1")
        
        time.sleep(WAIT_BETWEEN_CALLS)
    
    # 追打失败队列
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
    
    # 整理输出(失败的填空记录)
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
        print(f"最终失败 {len(final_failures)} 个: {final_failures}")
    print(f"保存: {OUTPUT}")


if __name__ == "__main__":
    main()