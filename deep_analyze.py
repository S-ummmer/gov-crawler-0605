"""Deep analysis of all 4 gov websites to find actual data endpoints."""
import requests
import urllib3
import re
import json
import os

urllib3.disable_warnings()
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.most.gov.cn/',
})

results_dir = 'D:/Github/Mk-project/gov-crawler/results'
os.makedirs(results_dir, exist_ok=True)

# ============================================================
# 1. mee.gov.cn - Save full HTML and find result structure
# ============================================================
print("=== 1. mee.gov.cn 分析 ===")
r = s.get(
    'https://www.mee.gov.cn/searchnew/?searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD',
    timeout=20, verify=False
)
r.encoding = 'utf-8'
t = r.text
with open(f'{results_dir}/mee_full.html', 'w', encoding='utf-8') as f:
    f.write(t)
print(f'  保存了 {len(t)} 字符到 mee_full.html')

# Find result container - look for result1, result2, result3 divs
for div_id in ['result1', 'result2', 'result3', 'searchresult', 'list']:
    idx = t.find(f'id="{div_id}"')
    if idx >= 0:
        snippet = t[idx:idx+500].replace('\n', ' ').replace('\r', '')
        print(f'  找到 #{div_id}: ...{snippet[:300]}...')

# Find all <li> or <div class="..."> that might be result items
# Look for the result item pattern in TRS output
# TRS typically renders results as <li> elements inside a <ul>
li_matches = re.findall(r'<li[^>]*>.*?</li>', t, re.DOTALL)
print(f'  <li> 元素数量: {len(li_matches)}')
if li_matches:
    for i, li in enumerate(li_matches[:3]):
        print(f'  li[{i}]: {li[:200]}...')

# Look for the result area more carefully
# The page has result1, result2, result3 divs controlled by JS
# The actual results are loaded via AJAX to those divs
# Let's find the AJAX URL
ajax_urls = re.findall(r'url\s*:\s*["\']([^"\']+)["\']\s*,\s*type\s*:\s*["\'](GET|POST)["\']', t)
print(f'  AJAX URLs: {ajax_urls[:5]}')

# Also look for the pagination links
page_links = re.findall(r'href\s*=\s*["\']([^"\']*page[^"\']*)["\']', t)
print(f'  分页链接: {page_links[:5]}')

print()

# ============================================================
# 2. most.gov.cn - Try to find the actual search API
# ============================================================
print("=== 2. most.gov.cn 分析 ===")
# The page uses JS to load results. Let's try the common TRS pattern:
# most.gov.cn might use /was5/web/search or a custom API

# Try multiple API patterns
most_apis = [
    'https://www.most.gov.cn/was5/web/search?searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&channelid=&page=1&perpage=10',
    'https://www.most.gov.cn/search/query?searchWord=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&pageNo=1&pageSize=10',
    'https://www.most.gov.cn/search/data?searchWord=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&pageNo=1&pageSize=10',
]
for url in most_apis:
    try:
        r = s.get(url, timeout=15, verify=False)
        r.encoding = 'utf-8'
        print(f'  [{r.status_code}] {url[:80]} len={len(r.text)}')
        if len(r.text) > 500 and 'TRS' not in r.text[:100]:
            print(f'    Content: {r.text[:300]}')
    except Exception as e:
        print(f'  ERROR: {e}')

# Now fetch the JS file to find the real API
print('  正在获取 searchForHaiYi.js...')
try:
    r_js = s.get('https://www.most.gov.cn/assets/js/searchForHaiYi.js', timeout=15, verify=False)
    js_content = r_js.text
    print(f'  JS大小: {len(js_content)}')
    
    # Find all URL patterns in the JS
    urls_in_js = re.findall(r'["\'](/[^"\']*(?:search|data|api|query)[^"\']*)["\']\s*', js_content)
    print(f'  JS中的URL: {list(set(urls_in_js))[:10]}')
    
    # Find the search function
    search_fn = re.search(r'function\s+\w*search\w*\([^)]*\)\s*\{[^}]+\}', js_content, re.DOTALL)
    if search_fn:
        print(f'  search函数: {search_fn.group(0)[:300]}')
    
    # Look for /search/data or similar
    data_api = re.search(r'["\'](/search/[^"\']+)["\']', js_content)
    if data_api:
        print(f'  找到API: {data_api.group(1)}')
        
    # Save JS for manual analysis
    with open(f'{results_dir}/most_searchForHaiYi.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f'  JS已保存到 {results_dir}/most_searchForHaiYi.js')
except Exception as e:
    print(f'  ERROR获取JS: {e}')

print()

# ============================================================
# 3. nda.gov.cn - Find the v8d5 API
# ============================================================
print("=== 3. nda.gov.cn 分析 ===")
r3 = s.get('https://www.nda.gov.cn/sjj/xxgk/search_xxgk/list/index_pc.html?keyword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD',
           timeout=20, verify=False)
r3.encoding = 'utf-8'
t3 = r3.text
with open(f'{results_dir}/nda_full.html', 'w', encoding='utf-8') as f:
    f.write(t3)
print(f'  保存了 {len(t3)} 字符到 nda_full.html')

# The page uses v8d5 framework and /sjj/js/xxgksearch/list/index_pc.js
# Let's fetch that JS
print('  正在获取 xxgksearch JS...')
try:
    r_js3 = s.get('https://www.nda.gov.cn/sjj/js/xxgksearch/list/index_pc.js', timeout=15, verify=False)
    js3 = r_js3.text
    print(f'  JS大小: {len(js3)}')
    
    # Find the getList function and its URL
    getlist = re.search(r'function\s+getList\s*\([^)]*\)\s*\{([^}]+)\}', js3, re.DOTALL)
    if getlist:
        print(f'  getList函数内容: {getlist.group(1)[:500]}')
    
    # Find AJAX URL
    ajax_url = re.search(r'url\s*:\s*["\']([^"\']+)["\']', js3)
    if ajax_url:
        print(f'  AJAX URL: {ajax_url.group(1)}')
    
    # Find the v8d5 call
    v8d5_calls = re.findall(r'v8d5\.\w+\([^)]*\)', js3)
    print(f'  v8d5调用: {v8d5_calls[:5]}')
    
    with open(f'{results_dir}/nda_xxgksearch.js', 'w', encoding='utf-8') as f:
        f.write(js3)
    print(f'  JS已保存到 {results_dir}/nda_xxgksearch.js')
except Exception as e:
    print(f'  ERROR获取JS: {e}')

print()

# ============================================================
# 4. mof.gov.cn - TRS system analysis
# ============================================================
print("=== 4. mof.gov.cn 分析 ===")
# The TRS page returns a small page - the search might be a form POST
# Let's look at the search page more carefully
# Try POST request to the TRS search

# First, let's try to access the search page with different parameters
# TRS often uses: /was5/web/search?channelid=XXX&searchword=XXX&page=XXX
# The channelid for mof.gov.cn might be different

# Let's try to find the correct channelid
# Try common channel IDs
for cid in ['271782', '218614', '200008', '280000', '1']:
    url = f'https://search.mof.gov.cn/was5/web/search?channelid={cid}&searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&page=1'
    try:
        r = s.get(url, timeout=10, verify=False)
        r.encoding = 'utf-8'
        if 'TRS' not in r.text[:100] and len(r.text) > 1000:
            print(f'  [channelid={cid}] 有数据! len={len(r.text)}')
            print(f'    {r.text[:300]}')
        else:
            print(f'  [channelid={cid}] 无数据 (len={len(r.text)})')
    except Exception as e:
        print(f'  [channelid={cid}] ERROR: {e}')

print()
print("分析完成！请查看 results/ 目录中的文件")
