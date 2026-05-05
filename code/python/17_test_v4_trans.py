"""测试 v4 在 TRANS 文件上到底走的哪条路径"""
from pathlib import Path
from bs4 import BeautifulSoup
import sys
sys.path.insert(0, "code/python")

# 直接 import v4 的提取函数
import importlib.util
spec = importlib.util.spec_from_file_location(
    "v4", "code/python/11_extract_text_v4.py"
)
v4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4)

f = Path("data/raw/main/TRANS_20200728090448_XTYSZHMYYWHT.html")
html = f.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "lxml")

print(f"测试文件: {f.name}")
print(f"HTML 长度: {len(html)}")

# 1. 检查是不是被 CSR 判定误杀
is_csr = v4.is_csr_only(html, soup)
print(f"\nis_csr_only(): {is_csr}")
body = soup.find("body")
body_text = body.get_text(strip=True)
print(f"  body 文本长度: {len(body_text)}")
nav_hits = sum(1 for p in v4.CSR_NAV_PHRASES if p in body_text)
print(f"  导航词命中数: {nav_hits}")
big_js = any(s.string and len(s.string) > 100000 for s in soup.find_all("script"))
print(f"  有大 JS bundle: {big_js}")

# 2. 走完整提取
print(f"\n完整提取流程:")
text, method = v4.extract_one(f, is_news=False)
print(f"  方法: {method}")
print(f"  长度: {len(text) if text else 0}")
if text:
    print(f"  前 200 字符: {text[:200]}")

# 3. 单独测试 method C
print(f"\n单独测试 method C:")
text_c = v4.try_method_c_body(soup)
print(f"  返回长度: {len(text_c) if text_c else 0}")
if text_c:
    print(f"  前 200 字符: {text_c[:200]}")

# 4. 单独测试 method MB
print(f"\n单独测试 method MB (main-body):")
text_mb = v4.try_method_main_body(soup)
print(f"  返回长度: {len(text_mb) if text_mb else 0}")
if text_mb:
    print(f"  前 200 字符: {text_mb[:200]}")

# 5. 直接看 main-body 那个 div 在不在
import re
mb_divs = soup.find_all("div", class_=re.compile(r"main-body"))
print(f"\nmain-body div 数: {len(mb_divs)}")
for d in mb_divs:
    cls = d.get("class", [])
    print(f"  class: {cls}")
    print(f"  原始文本长度: {len(d.get_text(strip=True))}")