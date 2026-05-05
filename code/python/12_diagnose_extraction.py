"""
诊断提取失败的真实原因
不再用 try/except 吞掉错误，直接复现 + 抽样
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
import traceback

RAW_MAIN = Path("data/raw/main")
RAW_NEWS = Path("data/raw/news")
REPORT_PATH = Path("data/processed/11_extraction_report.csv")


def find_file(filename):
    """在 main 或 news 里找文件"""
    for d in [RAW_MAIN, RAW_NEWS]:
        p = d / filename
        if p.exists():
            return p
    return None


def diagnose_error_files():
    """对每个 ERROR 案例，看是哪一步抛异常"""
    print("=" * 60)
    print("诊断 ERROR 案例")
    print("=" * 60)
    
    df = pd.read_csv(REPORT_PATH)
    errors = df[df["method"] == "ERROR"]
    print(f"ERROR 总数: {len(errors)}")
    
    # 按类别抽样 2 个
    samples = errors.groupby("category").head(2)
    
    error_signatures = {}
    
    for _, row in samples.iterrows():
        f = find_file(row["filename"])
        if not f:
            print(f"\n  {row['filename']}: 文件找不到")
            continue
        
        print(f"\n[{row['category']}] {row['filename']} ({row['html_size_kb']:.1f} KB)")
        
        try:
            html = f.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(html, "lxml")
            
            # 试一下 __NEXT_DATA__ 的 JSON 解析
            nd = soup.find("script", id="__NEXT_DATA__")
            if nd and nd.string:
                try:
                    data = json.loads(nd.string)
                    print(f"  __NEXT_DATA__: 长度 {len(nd.string)}, JSON 解析成功")
                    print(f"  顶层: {list(data.keys())[:8]}")
                    pp = data.get("props", {}).get("pageProps", {})
                    print(f"  pageProps keys: {list(pp.keys())[:10]}")
                except json.JSONDecodeError as e:
                    print(f"  __NEXT_DATA__ JSON 解析失败: {e}")
            else:
                print(f"  __NEXT_DATA__: 不存在")
            
            print(f"  body 文本长度: {len(soup.find('body').get_text(strip=True)) if soup.find('body') else '无 body'}")
            
        except Exception as e:
            sig = type(e).__name__
            error_signatures[sig] = error_signatures.get(sig, 0) + 1
            print(f"  抛异常: {sig}: {str(e)[:200]}")
            print(f"  Traceback:")
            traceback.print_exc(limit=3)


def diagnose_failed_files():
    """对每个 FAILED 案例，看为什么三种方法都返回 None"""
    print("\n" + "=" * 60)
    print("诊断 FAILED 案例")
    print("=" * 60)
    
    df = pd.read_csv(REPORT_PATH)
    failed = df[df["method"] == "FAILED"]
    print(f"FAILED 总数: {len(failed)}")
    
    # 按类别抽样 3 个
    samples = failed.groupby("category").head(3)
    
    for _, row in samples.iterrows():
        f = find_file(row["filename"])
        if not f:
            continue
        
        print(f"\n[{row['category']}] {row['filename']} ({row['html_size_kb']:.1f} KB)")
        
        html = f.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "lxml")
        
        # 检查每种架构的迹象
        nd = soup.find("script", id="__NEXT_DATA__")
        if nd and nd.string:
            try:
                data = json.loads(nd.string)
                pp = data.get("props", {}).get("pageProps", {})
                content = pp.get("content")
                if isinstance(content, str):
                    print(f"  __NEXT_DATA__.pageProps.content: 长度 {len(content)}")
                    if len(content) <= 500:
                        print(f"    内容: {content[:300]}")
                else:
                    print(f"  __NEXT_DATA__.pageProps.content: 不是字符串 (类型 {type(content).__name__})")
                    # 看看其他可能含正文的字段
                    for k, v in pp.items():
                        if isinstance(v, str) and len(v) > 200:
                            print(f"    候选字段 pageProps.{k}: 字符串长度 {len(v)}")
                            print(f"      预览: {v[:200]}")
                        elif isinstance(v, dict):
                            for k2, v2 in v.items():
                                if isinstance(v2, str) and len(v2) > 500:
                                    print(f"    候选字段 pageProps.{k}.{k2}: 字符串长度 {len(v2)}")
            except Exception as e:
                print(f"  JSON 解析问题: {e}")
        else:
            print(f"  没有 __NEXT_DATA__")
        
        main_tag = soup.find("main")
        article_tag = soup.find("article")
        body_tag = soup.find("body")
        
        print(f"  <main>: {'有' if main_tag else '无'}", end="")
        if main_tag:
            print(f" 文本 {len(main_tag.get_text(strip=True))}")
        else:
            print()
        
        print(f"  <article>: {'有' if article_tag else '无'}", end="")
        if article_tag:
            print(f" 文本 {len(article_tag.get_text(strip=True))}")
        else:
            print()
        
        print(f"  <body> 文本: {len(body_tag.get_text(strip=True)) if body_tag else '无'}")
        
        # 看 body 的前 200 字符
        if body_tag:
            body_text = body_tag.get_text(separator=' ', strip=True)
            print(f"    body 预览: {body_text[:300]}")


if __name__ == "__main__":
    diagnose_error_files()
    diagnose_failed_files()