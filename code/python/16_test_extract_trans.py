"""单独测试一份 TRANS 文件的提取，看 method C 在哪一步把内容丢了"""
from pathlib import Path
from bs4 import BeautifulSoup

f = Path("data/raw/main/TRANS_20200728090448_XTYSZHMYYWHT.html")
html = f.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "lxml")

body = soup.find("body")
print(f"body 原始文本长度: {len(body.get_text(strip=True))}")

# 复制一份 body
body_copy = BeautifulSoup(str(body), "lxml")

# 模拟 v3 里 remove_noise 的步骤
NOISE_TAGS = ["script", "style", "nav", "footer", "header",
              "noscript", "iframe", "svg", "img", "aside"]
NOISE_CLASS_KEYWORDS = ["nav", "header", "footer", "sidebar", "cookie", "banner",
                        "consent", "skip-link", "skiplink", "language-selector",
                        "region-selector", "wb-autocheck", "wm-",
                        "side-list", "breadcrumb"]

# 一步步删，看每步剩多少
for tag_name in NOISE_TAGS:
    tags = body_copy.find_all(tag_name)
    if tags:
        for t in tags:
            t.decompose()
        remaining = len(body_copy.get_text(strip=True))
        print(f"  删掉 <{tag_name}> ({len(tags)} 个) 后，body 剩 {remaining} 字符")

print(f"\n按 class 关键词删除前: {len(body_copy.get_text(strip=True))} 字符")
for elem in list(body_copy.find_all(attrs={"class": True})):
    if elem.parent is None:
        continue
    cls = " ".join(elem.get("class", [])).lower()
    matched = [kw for kw in NOISE_CLASS_KEYWORDS if kw in cls]
    if matched:
        text_len = len(elem.get_text(strip=True))
        print(f"  匹配 {matched}: <{elem.name} class='{cls[:60]}'> 含 {text_len} 字符")
        elem.decompose()

print(f"\n清理后 body 总文本: {len(body_copy.get_text(strip=True))} 字符")
print(f"前 500 字符: {body_copy.get_text(separator=' ', strip=True)[:500]}")