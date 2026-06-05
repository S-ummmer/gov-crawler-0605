# -*- coding: utf-8 -*-
"""
Government website policy document crawler
Target: 4 government websites for AI-related documents
Output: JSON + CSV in results/ directory
支持增量更新：读取旧数据去重，只新增未收录的条目
"""

import os
import json
import csv
import time
import random
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()

# ============================================================
# Global Config
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

# 简化输出文件名
OUTPUT_JSON = os.path.join(RESULTS_DIR, 'result.json')
OUTPUT_CSV = os.path.join(RESULTS_DIR, 'result.csv')

COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

all_results = []
seen_urls = set()
new_items_count = 0


def load_old_data():
    """加载历史数据用于增量更新"""
    global all_results, seen_urls
    
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
                all_results = json.load(f)
            
            seen_urls = {item['url'] for item in all_results if item.get('url')}
            print(f'  [增量更新] 已加载 {len(all_results)} 条历史数据')
        except Exception as e:
            print(f'  [警告] 读取历史数据失败: {e}')
            all_results = []
            seen_urls = set()
    else:
        print(f'  [首次运行] 未找到历史数据，将从头开始')


def extract_date(text):
    """Extract date from text, return YYYY-MM-DD format."""
    if not text:
        return ''
    m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', text)
    if m:
        return f'{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}'
    return ''


def add_item(title, url, source, doc_date, content):
    """Item addition with dedup."""
    global all_results, seen_urls, new_items_count
    if url in seen_urls:
        return False
    seen_urls.add(url)
    all_results.append({
        'seq': 0,
        'tag': '[正文] 人工智能',
        'title': title,
        'docDate': doc_date,
        'url': url,
        'source': source,
        'content': content,
    })
    new_items_count += 1
    return True


def save_results():
    """Save current results to JSON and CSV."""
    for i, item in enumerate(all_results, 1):
        item['seq'] = i

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    if all_results:
        fieldnames = ['seq', 'tag', 'title', 'docDate', 'url', 'source', 'content']
        with open(OUTPUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in all_results:
                row = {k: item.get(k, '') for k in fieldnames}
                writer.writerow(row)

    print(f'  [保存] 共 {len(all_results)} 条记录，本次新增 {new_items_count} 条')


def cleanup_results_dir():
    """清理 results 目录中不必要的文件，只保留 result.json 和 result.csv"""
    allowed_files = {'result.json', 'result.csv'}
    
    for filename in os.listdir(RESULTS_DIR):
        filepath = os.path.join(RESULTS_DIR, filename)
        if os.path.isfile(filepath) and filename not in allowed_files:
            try:
                os.remove(filepath)
                print(f'  [清理] 删除不必要的文件: {filename}')
            except Exception as e:
                print(f'  [警告] 删除文件失败 {filename}: {e}')


def fetch_detail(url):
    """Fetch detail page content."""
    try:
        r = requests.get(url, headers=COMMON_HEADERS, timeout=15, verify=False)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            tag.decompose()
        
        selectors = [
            soup.find('div', class_=lambda x: x and any(k in str(x).lower() for k in ['content', 'article', 'TRS_EDITOR'])),
            soup.find('div', {'id': lambda x: x and any(k in str(x).lower() for k in ['content', 'article'])}),
            soup.find('article'),
            soup.find('main'),
            soup.find('div', class_='TRS_EDITOR'),
            soup.find('div', class_='zoom'),
            soup.find('div', class_='detail'),
            soup.find('div', class_='article-content'),
            soup.find('div', class_='article'),
        ]
        
        for div in selectors:
            if div:
                text = div.get_text(separator='\n', strip=True)
                if len(text) > 100:
                    return text[:5000]
        
        body_content = soup.find('body')
        if body_content:
            return body_content.get_text(separator='\n', strip=True)[:5000]
        
        return ''
    except Exception as e:
        print(f'    [Detail Error] {e}')
        return ''


# ============================================================
# 1. most.gov.cn (Ministry of Science and Technology)
# ============================================================

def crawl_most():
    """most.gov.cn uses JSON API"""
    print('\n[1/4] Crawling most.gov.cn (科技部)...')
    
    headers = {
        **COMMON_HEADERS,
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.most.gov.cn/search/qzjs/',
    }

    categories = [
        ('全站', '779464455284195328'),
        ('政策', '779464812773113856'),
    ]

    count = 0
    for cat_name, cat_id in categories:
        print(f'  Category: {cat_name}')
        for page_num in range(1, 51):
            data = {
                'searchWord': '人工智能',
                'id': cat_id,
                'pageNum': page_num,
                'pageSize': 20,
                'searchRange': 2,
                'sortMode': '-0',
            }
            try:
                r = requests.post(
                    'https://search.most.gov.cn/hy/search/data',
                    json=data,
                    headers=headers,
                    timeout=20,
                    verify=False
                )
                
                if r.status_code != 200:
                    print(f'    Page {page_num}: HTTP {r.status_code}')
                    break
                
                resp = r.json()
                if resp.get('code') != 200:
                    print(f'    Page {page_num}: API code={resp.get("code")}')
                    break
                
                result_list = resp.get('data', {}).get('result', [])
                if not result_list:
                    print(f'    Page {page_num}: empty')
                    break
                
                page_count = 0
                for item in result_list:
                    url = item.get('PUBURL', '').strip()
                    if not url or not url.startswith('http'):
                        continue
                    
                    title = BeautifulSoup(item.get('DOCTITLE', ''), 'html.parser').get_text(strip=True)
                    doc_date = extract_date(item.get('DOCPUBTIME', ''))
                    
                    content = fetch_detail(url) if url else ''
                    
                    if add_item(title, url, '科学技术部', doc_date, content):
                        count += 1
                        page_count += 1
                
                print(f'    Page {page_num}: +{page_count} items')
                time.sleep(random.uniform(0.3, 0.8))
                
            except Exception as e:
                print(f'    Page {page_num} error: {e}')
                break
    
    print(f'  [most.gov.cn] 本次新增: {count} 条')
    return count


# ============================================================
# 2. mee.gov.cn (Ministry of Ecology and Environment)
# ============================================================

def crawl_mee():
    """mee.gov.cn uses TRS search"""
    print('\n[2/4] Crawling mee.gov.cn (生态环境部)...')
    
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    
    # First visit search page to get cookies
    try:
        session.get('https://www.mee.gov.cn/searchnew/?searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD',
                   timeout=10, verify=False)
    except:
        pass
    
    base_url = 'https://www.mee.gov.cn/was5/web/search'
    params = {
        'channelid': '270514',
        'searchword': '人工智能',
        'perpage': '20',
    }
    
    count = 0
    total_pages = 999
    
    for page in range(1, 101):
        params['page'] = str(page)
        try:
            r = session.get(base_url, params=params, timeout=15, verify=False)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            if page == 1:
                count_page = soup.find('input', {'id': 'countPage'})
                if count_page and count_page.get('value'):
                    total_pages = int(count_page['value'])
                    print(f'  Total pages: {total_pages}')
            
            result_div = soup.find('div', class_='ll_gjjs_list_was') or soup
            
            page_count = 0
            for link in result_div.find_all('a', href=True):
                href = link['href'].strip()
                if 'mee.gov.cn' not in href:
                    continue
                
                url = href if href.startswith('http') else urljoin('https://www.mee.gov.cn', href)
                title = link.get_text(strip=True)
                if not title or len(title) < 3:
                    continue
                
                parent = link.find_parent(['li', 'div'])
                date_text = parent.get_text() if parent else ''
                doc_date = extract_date(date_text)
                
                content = fetch_detail(url) if url else ''
                
                if add_item(title, url, '生态环境部', doc_date, content):
                    count += 1
                    page_count += 1
            
            print(f'    Page {page}: +{page_count} items')
            
            if page_count == 0:
                break
            if page >= total_pages:
                break
            
            time.sleep(random.uniform(0.5, 1.0))
            
        except Exception as e:
            print(f'    Page {page} error: {e}')
            break
    
    print(f'  [mee.gov.cn] 本次新增: {count} 条')
    return count


# ============================================================
# 3. nda.gov.cn (National Archives) - Playwright
# ============================================================

def crawl_nda():
    """nda.gov.cn: JS rendered, use Playwright browser."""
    print('\n[3/4] Crawling nda.gov.cn (国家档案局) via Playwright...')

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('  Playwright not installed, skipping')
        return 0

    count = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='zh-CN',
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        base_url = 'https://www.nda.gov.cn/sjj/xxgk/search_xxgk/list/index_pc.html?keyword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD'

        try:
            page.goto(base_url, wait_until='networkidle')
            time.sleep(3)
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            all_links = soup.find_all('a', href=True)
            content_links = []
            for link in all_links:
                href = link['href'].strip()
                title = link.get_text(strip=True)
                if title and len(title) >= 5:
                    if 'list/' not in href and 'index_pc' not in href:
                        full_url = href if href.startswith('http') else urljoin('https://www.nda.gov.cn', href)
                        content_links.append((title, full_url))
            
            content_links = list(dict.fromkeys(content_links))
            print(f'  Found {len(content_links)} links')
            
            for title, url in content_links[:50]:
                doc_date = extract_date(title)
                content = fetch_detail(url) if url else ''
                if add_item(title, url, '国家档案局', doc_date, content):
                    count += 1
                
                time.sleep(random.uniform(0.3, 0.6))
            
        except Exception as e:
            print(f'  nda.gov.cn error: {e}')
        finally:
            browser.close()
    
    print(f'  [nda.gov.cn] 本次新增: {count} 条')
    return count


# ============================================================
# 4. mof.gov.cn (Ministry of Finance) - Playwright
# ============================================================

def crawl_mof():
    """mof.gov.cn: TRS JS rendering, try Playwright."""
    print('\n[4/4] Crawling mof.gov.cn (财政部) via Playwright...')

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('  Playwright not installed, skipping')
        return 0

    count = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='zh-CN',
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        search_url = 'https://search.mof.gov.cn/was5/web/search?searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&channelid=271782'

        try:
            page.goto(search_url, wait_until='networkidle')
            time.sleep(3)
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            all_links = soup.find_all('a', href=True)
            result_links = []
            for link in all_links:
                href = link['href'].strip()
                title = link.get_text(strip=True)
                if title and 'mof.gov.cn' in href and len(title) >= 5:
                    result_links.append((title, href))
            
            result_links = list(dict.fromkeys(result_links))
            print(f'  Found {len(result_links)} links')
            
            for title, url in result_links[:100]:
                doc_date = extract_date(title)
                content = fetch_detail(url) if url else ''
                if add_item(title, url, '财政部', doc_date, content):
                    count += 1
                
                time.sleep(random.uniform(0.3, 0.6))
            
        except Exception as e:
            print(f'  mof.gov.cn error: {e}')
        finally:
            browser.close()
    
    print(f'  [mof.gov.cn] 本次新增: {count} 条')
    return count


# ============================================================
# Main
# ============================================================

def main():
    print('=' * 60)
    print('Government Website AI Policy Document Crawler')
    print('Keywords: 人工智能 (Artificial Intelligence)')
    print('=' * 60)
    
    # 加载历史数据用于增量更新
    load_old_data()
    
    start_time = time.time()
    results_summary = {}
    
    # 1. most.gov.cn
    n = crawl_most()
    results_summary['科学技术部'] = n
    
    # 2. mee.gov.cn
    n = crawl_mee()
    results_summary['生态环境部'] = n
    
    # 3. nda.gov.cn
    n = crawl_nda()
    results_summary['国家档案局'] = n
    
    # 4. mof.gov.cn
    n = crawl_mof()
    results_summary['财政部'] = n
    
    # 清理不必要的文件
    cleanup_results_dir()
    
    # 保存结果
    save_results()
    
    elapsed = time.time() - start_time
    print('\n' + '=' * 60)
    print('CRAWLING COMPLETE')
    print(f'  Total time: {elapsed:.1f} seconds')
    print(f'  Total unique items: {len(all_results)}')
    print(f'  New items added: {new_items_count}')
    print('  By source:')
    for source, n in results_summary.items():
        print(f'    {source}: {n} new')
    print(f'\n  Output:')
    print(f'    JSON: {OUTPUT_JSON}')
    print(f'    CSV:  {OUTPUT_CSV}')
    print('=' * 60)


if __name__ == '__main__':
    main()
