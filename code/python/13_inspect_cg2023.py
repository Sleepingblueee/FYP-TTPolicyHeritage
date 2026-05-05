"""
仔细看一眼 2023 改版后 CG 子页面的 HTML 结构
专门解决 348 个 FAILED CG 文件的提取问题
"""

from pathlib import Path
from bs4 import BeautifulSoup

RAW_MAIN = Path("data/raw/main")

# 找一个典型样本
samples = sorted(RAW_MAIN.glob("CG_2023*.html"))[:3] + sorted(RAW_MAIN.glob("CG_sub_2023*.html"))[:3]

for f in samples[:3]:
    print(f"\n{'='*70}")
    print(f"文件: {f.name}")
    print(f"{'='*70}")
    
    html = f.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    
    main_tag = soup.find("main")
    if not main_tag:
        print("没有 <main>")
        continue
    
    # 看 main 的子结构
    print(f"\n<main> 直接子元素:")
    for i, child in enumerate(main_tag.find_all(recursive=False)[:10]):
        text_preview = child.get_text(strip=True)[:80]
        cls = child.get("class", [])
        attrs_to_show = {k: v for k, v in child.attrs.items() if k in ["class", "id", "role", "data-testid"]}
        print(f"  [{i}] <{child.name}> {attrs_to_show}")
        print(f"      文本前80字: {text_preview}")
        print(f"      文本总长: {len(child.get_text(strip=True))}")
    
    # 找 aside / nav / role=navigation 等
    print(f"\n<main> 内的导航元素:")
    for selector in ["aside", "nav", "[role=navigation]", "[role=complementary]"]:
        elems = main_tag.select(selector)
        if elems:
            print(f"  {selector}: 找到 {len(elems)} 个")
            for e in elems[:2]:
                print(f"    第一行文本: {e.get_text(strip=True)[:80]}")
    
    # 找 article 或者大段文本块
    print(f"\n<main> 内的 article / section:")
    for selector in ["article", "section", "[role=main]"]:
        elems = main_tag.select(selector)
        if elems:
            print(f"  {selector}: 找到 {len(elems)} 个")
            for e in elems[:2]:
                print(f"    文本长度: {len(e.get_text(strip=True))}")
                print(f"    文本前150字: {e.get_text(strip=True)[:150]}")