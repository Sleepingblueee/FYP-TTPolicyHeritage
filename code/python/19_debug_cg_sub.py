"""精确定位 CG_sub 失败的原因"""
from pathlib import Path
from bs4 import BeautifulSoup
import re

NOISE_TAGS = ["script", "style", "nav", "footer", "header",
              "noscript", "iframe", "svg", "img", "aside"]
NOISE_CLASS_EXACT = {
    "cookie-banner", "cookie-consent", "cookie-notice",
    "skip-link", "skiplink", "skip-to-content",
    "language-selector", "region-selector",
    "wb-autocheck", "side-list-container",
    "breadcrumb", "breadcrumbs",
    "header-container", "footer-container",
    "site-header", "site-footer",
}

f = Path("data/raw/main/CG_sub_20230321122525_OZPNV2A3XA6A.html")
html = f.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "lxml")

main_tag = soup.find("main")
print(f"main 原始文本: {len(main_tag.get_text(strip=True))} 字符")

# 复制一份模拟 soup_to_markdown 的处理
main_copy = BeautifulSoup(str(main_tag), "lxml")

# 删噪音标签
for tag_name in NOISE_TAGS:
    tags = main_copy.find_all(tag_name)
    if tags:
        for t in tags:
            t.decompose()
        print(f"  删 <{tag_name}> ({len(tags)} 个) 后: {len(main_copy.get_text(strip=True))} 字符")

# 删噪音 class
print(f"\n按 class 精确匹配删除前: {len(main_copy.get_text(strip=True))} 字符")
for elem in list(main_copy.find_all(attrs={"class": True})):
    if elem.parent is None:
        continue
    cls_set = set(elem.get("class", []))
    matched = cls_set & NOISE_CLASS_EXACT
    if matched:
        text_len = len(elem.get_text(strip=True))
        print(f"  匹配 {matched}: <{elem.name} class={list(cls_set)[:3]}> 含 {text_len} 字符")
        elem.decompose()

print(f"\n清理后 main 总文本: {len(main_copy.get_text(strip=True))} 字符")
print(f"前 300 字符: {main_copy.get_text(separator=' ', strip=True)[:300]}")