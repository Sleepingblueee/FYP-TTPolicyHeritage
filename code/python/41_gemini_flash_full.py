"""
全量 Gemini 编码 v3 - Flash-Lite 提速版
- 模型: gemini-2.5-flash-lite (Pro 太慢,Flash 之前撞 503)
- 并发: 6 线程
- RPM 限制: 200 RPM
- 断点续传 + 失败行清理 + 自动重试
"""

import os
import re
import json
import time
import threading
from collections import deque
from pathlib import Path
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7897"

INPUT = Path("data/processed/40_sampled_sections.csv")
OUTPUT = Path("data/processed/41_full_coded.csv")
CODEBOOK = Path("codebook/codebook_v3_en.md")

# ============================================
# 模型与并发参数
# ============================================
MODEL = "gemini-2.5-flash-lite"
N_THREADS = 6
MAX_RPM = 200
RATE_429_PAUSE = 30
RETRY_WAIT = 3
RETRY_MAX = 4

TRANSIENT_HINTS = ["503", "502", "504", "unavailable", "timeout",
                   "disconnect", "eof", "connection", "remoteprotocol",
                   "rate", "exhausted", "quota", "429", "toomany"]

CODES_A = ["power", "privacy", "safety", "choice", "community",
           "engagement", "ip_protection", "improvement", "care", "accountability"]
CODES_B = ["B1_authenticity_claims", "B2_religious_sensitivity",
           "B3_indigenous_minority", "B4_traditional_craftsmanship",
           "B5_commercialization_culture", "B6_ai_cultural_content"]
ALL_CODES = CODES_A + CODES_B


SYSTEM_INSTRUCTION = """You are a research assistant performing content analysis on TikTok policy documents using codebook v3.

CRITICAL v3 RULES:

(1) POWER + SAFETY CO-OCCUR IN PROHIBITIONS.
When a section is a content prohibition ("We do not allow X", "NOT ALLOWED", "Do not post", "Do not upload", "we will remove"), code BOTH power=1 AND safety=1.

(2) HERITAGE CODES USE KEYWORD-ANCHORED JUDGMENT.
B1-B6 codes are triggered when:
   (a) The section contains a heritage keyword (religion, religious, sacred, ceremony, ritual, indigenous, tribal, ethnic, traditional, cultural practice, heritage, ancestral), AND
   (b) The section discusses content rules, content categories, regional exceptions, governance, or behavior categorization.

DO NOT require "substantive elaboration" beyond keyword presence + governance context.

Examples:
- Hate speech section listing "religion" as protected attribute -> B2=1
- Hate speech section listing "ethnicity" as protected attribute -> B3=1
- "Regional exceptions for body exposure in common cultural practices" -> B3=1
- "We do not allow paid political promotion... including traditional paid advertisements" -> B4=1

(3) WHEN IN DOUBT:
- Part A platform values (except power-safety co-occurrence): code 0
- Part B heritage codes: code 1

(4) MULTIPLE CODES PER SECTION ARE EXPECTED.

Output valid JSON only. No markdown fences, no commentary."""


def build_user_prompt(section_text, codebook_content):
    return f"""# Codebook v3

{codebook_content}

---

# Section to code

{section_text}

---

Apply codebook v3. Content prohibitions trigger BOTH power=1 AND safety=1. Heritage keywords within governance sections trigger B-codes.

Output ONLY valid JSON:

{{
  "power": {{"value": 0 or 1, "reason": "brief if 1, empty if 0"}},
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


def is_429(exception):
    msg = str(exception).lower()
    return "429" in msg or "toomany" in msg or ("rate" in msg and "limit" in msg)


def get_config():
    """Flash-Lite 不需要 thinking budget,直接返回简洁配置"""
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.0,
        max_output_tokens=4096,
    )


# ============================================
# 滑动窗口速率限制器
# ============================================
class RateLimiter:
    def __init__(self, max_rpm):
        self.max_rpm = max_rpm
        self.timestamps = deque()
        self.lock = threading.Lock()
    
    def acquire(self):
        while True:
            with self.lock:
                now = time.time()
                while self.timestamps and self.timestamps[0] < now - 60:
                    self.timestamps.popleft()
                
                if len(self.timestamps) < self.max_rpm:
                    self.timestamps.append(now)
                    return
                
                wait_time = 60 - (now - self.timestamps[0]) + 0.1
            
            time.sleep(min(wait_time, 5))


_rate_limiter = RateLimiter(MAX_RPM)
_client_lock = threading.Lock()
_client = None


def get_client():
    global _client
    with _client_lock:
        if _client is None:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            _client = genai.Client(api_key=api_key)
    return _client


def code_one_section(section_text, codebook_content):
    client = get_client()
    user_prompt = build_user_prompt(section_text, codebook_content)
    config = get_config()
    
    for attempt in range(1, RETRY_MAX + 1):
        _rate_limiter.acquire()
        
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config=config,
            )
            return parse_response(response.text), None
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:80]}"
            
            if is_429(e):
                if attempt < RETRY_MAX:
                    time.sleep(RATE_429_PAUSE)
                    continue
                else:
                    return None, err
            elif is_transient(e):
                if attempt < RETRY_MAX:
                    time.sleep(RETRY_WAIT)
                    continue
                else:
                    return None, err
            else:
                if attempt == 1:
                    time.sleep(1)
                    continue
                else:
                    return None, err
    return None, "max_retries"


def make_record(section_id, coding):
    record = {"section_id": section_id}
    n_ones = 0
    if coding is None:
        for code in ALL_CODES:
            record[f"gemini_{code}"] = ""
            record[f"gemini_reason_{code}"] = ""
        return record, 0
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


_write_lock = threading.Lock()


def append_to_csv(record, output_path):
    with _write_lock:
        write_header = not output_path.exists() or output_path.stat().st_size == 0
        df = pd.DataFrame([record])
        df.to_csv(output_path, mode="a", header=write_header, index=False, encoding="utf-8-sig")


def load_done_success(output_path):
    if not output_path.exists():
        return set()
    try:
        df = pd.read_csv(output_path, encoding="utf-8-sig")
        df["gemini_power"] = pd.to_numeric(df["gemini_power"], errors="coerce")
        ok = df[df["gemini_power"].isin([0, 1])]
        return set(ok["section_id"].tolist())
    except Exception:
        return set()


def remove_failed_rows(output_path):
    if not output_path.exists():
        return 0
    try:
        df = pd.read_csv(output_path, encoding="utf-8-sig")
        df["gemini_power"] = pd.to_numeric(df["gemini_power"], errors="coerce")
        ok = df[df["gemini_power"].isin([0, 1])]
        removed = len(df) - len(ok)
        if removed > 0:
            ok.to_csv(output_path, index=False, encoding="utf-8-sig")
        return removed
    except Exception:
        return 0


def worker(task, codebook_content, output_path):
    coding, err = code_one_section(task["section_text"], codebook_content)
    record, n_ones = make_record(task["section_id"], coding)
    append_to_csv(record, output_path)
    return task["section_id"], coding is not None, n_ones, err


def read_csv_robust(path):
    for enc in ["utf-8-sig", "utf-8", "gbk"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别 {path}")


def main():
    print("=" * 60)
    print(f"Step 41: 全量编码 (Gemini 2.5 Flash-Lite)")
    print(f"  模型: {MODEL}")
    print(f"  并发: {N_THREADS} 线程")
    print(f"  限速: {MAX_RPM} RPM (滑动窗口)")
    print(f"  429 暂停: {RATE_429_PAUSE}s")
    print(f"  重试: {RETRY_MAX} 次")
    print("=" * 60)
    
    codebook_content = CODEBOOK.read_text(encoding="utf-8")
    print(f"\nCodebook v3: {len(codebook_content)} 字符")
    
    df = read_csv_robust(INPUT)
    print(f"全量 sections: {len(df)}")
    
    removed = remove_failed_rows(OUTPUT)
    if removed > 0:
        print(f"清理之前 {removed} 个失败记录,准备重新跑")
    
    done = load_done_success(OUTPUT)
    print(f"已成功编完: {len(done)}")
    
    todo = df[~df["section_id"].isin(done)].copy()
    print(f"待编: {len(todo)}\n")
    
    if len(todo) == 0:
        print("全部编完,退出")
        return
    
    tasks = todo[["section_id", "section_text"]].to_dict("records")
    
    start = time.time()
    success_count = 0
    failure_count = 0
    failures_list = []
    
    print(f"开始并发编码...\n")
    
    with ThreadPoolExecutor(max_workers=N_THREADS) as executor:
        futures = [executor.submit(worker, task, codebook_content, OUTPUT) for task in tasks]
        
        for i, future in enumerate(as_completed(futures)):
            try:
                sid, ok, n_ones, err = future.result()
                if ok:
                    success_count += 1
                else:
                    failure_count += 1
                    failures_list.append((sid, err))
            except Exception as e:
                failure_count += 1
                failures_list.append(("unknown", f"future_error: {e}"))
            
            if (i + 1) % 50 == 0 or (i + 1) == len(tasks):
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta_min = (len(tasks) - i - 1) / rate / 60 if rate > 0 else 0
                rpm_actual = rate * 60
                print(f"[{i+1}/{len(tasks)}] OK={success_count} FAIL={failure_count} | "
                      f"{rpm_actual:.0f} RPM | 已 {elapsed/60:.1f}min | ETA {eta_min:.0f}min")
    
    total_min = (time.time() - start) / 60
    print(f"\n{'='*60}")
    print(f"完成: success={success_count} failure={failure_count} | 总用时 {total_min:.1f}min")
    
    if failures_list:
        fail_df = pd.DataFrame(failures_list, columns=["section_id", "error"])
        fail_path = Path("data/processed/41_failures.csv")
        fail_df.to_csv(fail_path, index=False, encoding="utf-8-sig")
        print(f"失败列表: {fail_path}")
        print(f"重跑此脚本会自动跳过已成功的,只重试失败的")


if __name__ == "__main__":
    main()