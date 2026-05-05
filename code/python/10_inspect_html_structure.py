"""
第三步第一小步：抽样侦察 HTML 结构
随机选 10 个文件，看每个文件:
1. 是否有 __NEXT_DATA__ JSON
2. JSON 的顶层 keys 是什么
3. 是否有 <main> 或 <article> 标签
4. <body> 里实际的可见文本长度
"""

import random
import json
from pathlib import Path
from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw/main")

# 跨类别均匀抽样
def sample_diverse(n_per_category=2):
    """每个类别抽 2 个，保证覆盖"""
    files = list(RAW_DIR.glob("*.html"))
    by_category = {}
    for f in files:
        cat = f.name.split("_")[0]
        by_category.setdefault(cat, []).append(f)
    
    sample = []
    for cat, flist in by_category.items():
        random.seed(42)
        sample.extend(random.sample(flist, min(n_per_category, len(flist))))
    return sample


def inspect_one(filepath):
    print(f"\n{'='*60}")
    print(f"文件: {filepath.name}")
    print(f"大小: {filepath.stat().st_size / 1024:.1f} KB")
    print(f"{'='*60}")
    
    html = filepath.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    
    # 1. 检查 __NEXT_DATA__
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data:
        print(f"\n[1] __NEXT_DATA__: 存在 ({len(next_data.string or '')} 字符)")
        try:
            data = json.loads(next_data.string)
            print(f"    顶层 keys: {list(data.keys())}")
            if "props" in data:
                pp = data["props"].get("pageProps", {})
                print(f"    props.pageProps keys: {list(pp.keys())[:15]}")
                # 找出可能含正文的字段
                for k, v in pp.items():
                    if isinstance(v, str) and len(v) > 500:
                        print(f"      [可能含正文] pageProps.{k}: 字符串长度 {len(v)}")
                    elif isinstance(v, dict):
                        for k2, v2 in v.items():
                            if isinstance(v2, str) and len(v2) > 500:
                                print(f"      [可能含正文] pageProps.{k}.{k2}: 字符串长度 {len(v2)}")
        except Exception as e:
            print(f"    JSON 解析失败: {e}")
    else:
        print(f"\n[1] __NEXT_DATA__: 不存在")
    
    # 2. 检查 <main> 和 <article>
    main_tag = soup.find("main")
    article_tag = soup.find("article")
    print(f"\n[2] 语义化标签:")
    print(f"    <main>: {'存在' if main_tag else '不存在'}")
    if main_tag:
        print(f"      文本长度: {len(main_tag.get_text(strip=True))}")
    print(f"    <article>: {'存在' if article_tag else '不存在'}")
    if article_tag:
        print(f"      文本长度: {len(article_tag.get_text(strip=True))}")
    
    # 3. body 文本总长度
    body = soup.find("body")
    if body:
        body_text = body.get_text(separator=" ", strip=True)
        print(f"\n[3] <body> 总文本: {len(body_text)} 字符")
        print(f"    前 300 字符: {body_text[:300]}")


def main():
    print("HTML 结构抽样侦察")
    print(f"从 {RAW_DIR} 中按类别抽样")
    
    sample = sample_diverse(n_per_category=2)
    print(f"共抽样 {len(sample)} 个文件\n")
    
    for f in sample:
        inspect_one(f)
    
    print(f"\n\n{'='*60}")
    print("侦察完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()