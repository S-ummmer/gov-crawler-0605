"""Analyze all 4 target government websites to find their API endpoints and HTML structures."""
import requests
import urllib3
import re
import json

urllib3.disable_warnings()
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
})

# ============================================================
# 1. mee.gov.cn (生态环境部) - TRS API
# ============================================================
print("="*60)
print("1. mee.gov.cn (生态环境部)")
print("="*60)

r = s.get(
    'https://www.mee.gov.cn/was5/web/search?channelid=270514&searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&page=1&perpage=10',
    timeout=20, verify=False
)
r.encoding = 'utf-8'
t = r.text

# Extract pagination info
count_page = re.findall(r'countPage[^>]*value=["\'](\d+)', t)
count_temp = re.findall(r'count_temp[^>]*value=["\'](\d+)', t)
print(f'countPage (total pages): {count_page}')
print(f'count_temp (total items): {count_temp}')

# Find all result items - look for the pattern: <a href="..." title="..." target="_blank">title</a> <span>date</span>
# The TRS response format typically has <a> tags with title and href
links_with_title = re.findall(r'<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"', t)
print(f'\nLinks with title attr: {len(links_with_title)}')
for href, title in links_with_title[:5]:
    print(f'  [{title}] -> {href}')

# Try to find the full result item structure
# Look for date patterns near links
dates = re.findall(r'(\d{4}-\d{2}-\d{2})', t)
print(f'\nDates found: {len(dates)}, first 10: {dates[:10]}')

# Now find the structure of each result item
# TRS results often have: <div class="result-item"> or <li> with <a>, <span class="date">
# Let's look for the result container
result_containers = re.findall(r'(class=["\'](?:result|search|list)[^"\']*["\'])', t)
print(f'Result containers: {result_containers[:10]}')

# Print a raw snippet around the first link to understand structure
first_link = re.search(r'<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"', t)
if first_link:
    start = max(0, first_link.start() - 100)
    end = min(len(t), first_link.end() + 200)
    print(f'\nFirst result snippet:')
    print(t[start:end])
    print()

# ============================================================
# 2. most.gov.cn (科技部) - Custom search API
# ============================================================
print("="*60)
print("2. most.gov.cn (科技部)")
print("="*60)

# Fetch the search page to find the actual API
r2 = s.get('https://www.most.gov.cn/search/qzjs/?searchWord=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&group=%E5%85%A8%E7%AB%99',
           timeout=20, verify=False)
r2.encoding = 'utf-8'
t2 = r2.text

# Find all JS file references
print('JS files:')
for m in re.finditer(r'<script[^>]*src="([^"]+)"', t2):
    print(f'  {m.group(1)}')

# Look for data attributes and hidden inputs
print('\nHidden inputs:')
for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*>', t2):
    print(f'  {m.group(0)[:200]}')

# Look for the search form action
print('\nForm actions:')
for m in re.finditer(r'<form[^>]*action=["\']([^"\']+)["\']', t2):
    print(f'  {m.group(1)}')

# Look for data- attributes that might hold API config
for m in re.finditer(r'data-[^=]+=["\'][^"\']+["\']', t2):
    val = m.group(0)
    if 'api' in val.lower() or 'url' in val.lower() or 'search' in val.lower():
        print(f'  data attr: {val}')

print()

# ============================================================
# 3. nda.gov.cn (国家档案局) - v8d5 framework
# ============================================================
print("="*60)
print("3. nda.gov.cn (国家档案局)")
print("="*60)

r3 = s.get('https://www.nda.gov.cn/sjj/xxgk/search_xxgk/list/index_pc.html?keyword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD',
           timeout=20, verify=False)
r3.encoding = 'utf-8'
t3 = r3.text

# Find v8d5 initialization
v8d5_calls = re.findall(r'v8d5\.\w+\([^)]*\)', t3)
print(f'v8d5 calls: {v8d5_calls}')

# Look for the AJAX URL
# Common v8d5 patterns
v8d5_urls = re.findall(r'url\s*:\s*["]([^"]+)["]', t3)
print(f'AJAX URLs: {v8d5_urls}')

# Find the getList function
getlist_match = re.search(r'function getList[^{]*\{[^}]*\}', t3)
if getlist_match:
    print(f'getList function: {getlist_match.group(0)[:500]}')

# Save full HTML for analysis
with open('D:/Github/Mk-project/gov-crawler/results/nda_page.html', 'w', encoding='utf-8') as f:
    f.write(t3)

# Try alternative URL with different parameters
alt_urls = [
    'https://www.nda.gov.cn/was5/web/search?channelid=252733&searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&page=1',
    'https://www.nda.gov.cn/was5/web/search?searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&page=1&perpage=10',
]
for url in alt_urls:
    try:
        r = s.get(url, timeout=15, verify=False)
        r.encoding = 'utf-8'
        print(f'\nAlt URL [{r.status_code}] len={len(r.text)}: {url}')
        if len(r.text) > 200:
            print(f'  {r.text[:300]}')
    except Exception as e:
        print(f'  ERROR: {e}')

print()

# ============================================================
# 4. mof.gov.cn (财政部) - TRS
# ============================================================
print("="*60)
print("4. mof.gov.cn (财政部)")
print("="*60)

# Try various approaches for mof.gov.cn
mof_tests = [
    ('GET basic', 'https://search.mof.gov.cn/was5/web/search?searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&channelid=271782&page=1&perpage=10'),
    ('GET searchpage', 'https://search.mof.gov.cn/was5/web/search?searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD'),
    ('GET full', 'https://search.mof.gov.cn/was5/web/search'),
    ('search page', 'https://www.mof.gov.cn/was5/web/search?searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&channelid=271782'),
]

for name, url in mof_tests:
    try:
        r = s.get(url, timeout=15, verify=False, allow_redirects=True)
        r.encoding = 'utf-8'
        print(f'[{name}] {r.status_code} len={len(r.text)} url={r.url}')
        if len(r.text) < 1000:
            print(f'  Content: {r.text.strip()[:500]}')
        else:
            # Find key info
            for kw in ['result', 'total', 'record', 'href', 'title', 'searchword']:
                c = len(re.findall(kw, r.text, re.IGNORECASE))
                if c > 0:
                    print(f'  {kw}: {c} occurrences')
    except Exception as e:
        print(f'[{name}] ERROR: {e}')

print()
print("Done! Saved nda page HTML to results/nda_page.html")
