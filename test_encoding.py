#!/usr/bin/env python3
"""
编码测试脚本 - 诊断 people.com.cn 等站点的编码问题
对比 requests 自动检测 vs 硬编码 UTF-8 的效果
"""

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 测试 URL
URLS = [
    # 已知乱码的
    ("http://finance.people.com.cn/n1/2024/0324/c1004-40202067.html", "人民网 (finance.people.com.cn)"),
    # 对照：已有的 UTF-8 站点
    ("https://www.most.gov.cn/kjbgz/202507/t20250727_194260.html", "科技部 (most.gov.cn) - 对照"),
    ("https://www.mee.gov.cn/ywgz/kjjyc/gjkjjscj/", "生态环境部 (mee.gov.cn) - 对照"),
]


def test_url(url, label):
    print("=" * 60)
    print(f"[测试] {label}")
    print(f"  URL: {url}\n")

    r = requests.get(url, headers=HEADERS, timeout=15, verify=False)

    # 1. HTTP Header 声明的编码
    content_type = r.headers.get('Content-Type', '')
    print(f"  HTTP Content-Type: {content_type}")

    # 2. requests 库自动检测的编码
    print(f"  requests 推测编码 (apparent_encoding): {r.apparent_encoding}")

    # 3. 页面 <meta> 标签声明的编码
    # 先尝试用 apparent_encoding 正确解码来看看 meta 标签
    try:
        soup_raw = BeautifulSoup(r.content, 'html.parser')
        for meta in soup_raw.find_all('meta'):
            if 'charset' in str(meta).lower():
                print(f"  页面 <meta> 声明: {meta.get('charset') or meta.get('content')}")
                break
    except:
        pass

    # 4. 使用 hardcoded UTF-8 (当前 crawler.py 的做法)
    r.encoding = 'utf-8'
    try:
        text_utf8 = r.text[:200]
        has_garbled = "�" in text_utf8 or "？" in text_utf8
    except:
        text_utf8 = "[解码失败]"
        has_garbled = True

    # 5. 使用 apparent_encoding (自动检测)
    r.encoding = r.apparent_encoding
    try:
        text_auto = r.text[:200]
    except:
        text_auto = "[解码失败]"

    print(f"\n  UTF-8 forced (first 200 chars): {text_utf8.replace(chr(10), ' ')}")
    print(f"    -> Garbled: {'YES - PROBLEM' if has_garbled else 'OK'}")

    print(f"\n  Auto-detected (first 200 chars): {text_auto.replace(chr(10), ' ')}")
    is_auto_ok = '\ufffd' not in text_auto
    print(f"    -> Garbled: {'OK' if is_auto_ok else 'YES - PROBLEM'}")

    # 6. 提取标题验证
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    title = soup.find('title')
    h1 = soup.find('h1')
    print(f"\n  Title (<title>): {title.get_text(strip=True)[:80] if title else 'N/A'}")
    print(f"  Title (<h1>):   {h1.get_text(strip=True)[:80] if h1 else 'N/A'}")

    print()


def main():
    print("gov-crawler 编码诊断工具\n")

    for url, label in URLS:
        try:
            test_url(url, label)
        except Exception as e:
            print(f"  [错误] {e}\n")

    print("=" * 60)
    print("CONCLUSION:")
    print("  If garbled above, crawler.py fetch_detail() hardcodes r.encoding='utf-8'")
    print("  which is incompatible with that site.")
    print("  Fix: use r.encoding = r.apparent_encoding for auto-detection.")
    print("=" * 60)


if __name__ == "__main__":
    main()
