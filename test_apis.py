"""Test all 4 websites' APIs and find the correct way to crawl them."""
import requests
import urllib3
import re
import json
import time

urllib3.disable_warnings()
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
})

# ============================================================
# 1. most.gov.cn - API is working! Fix encoding.
# ============================================================
print("="*60)
print("1. most.gov.cn (科技部) - API测试")
print("="*60)

# The response has GBK encoding - let's handle it properly
data = {
    'searchWord': '人工智能',
    'id': '779464455284195328',  # 全站
    'pageNum': 1,
    'pageSize': 10,
    'searchRange': 2,
    'sortMode': '-0'
}
try:
    r = s.post('https://search.most.gov.cn/hy/search/data', 
               json=data, timeout=20, verify=False)
    # Try to decode as GBK
    raw = r.content
    print(f'  状态码: {r.status_code}')
    print(f'  Content-Type: {r.headers.get("Content-Type")}')
    print(f'  原始bytes前200: {raw[:200]}')
    
    # Try GBK decode
    try:
        text_gbk = raw.decode('gbk')
        print(f'  GBK解码成功! 前500字符:')
        print(text_gbk[:500])
        
        # Try to parse JSON
        try:
            j = json.loads(text_gbk)
            print(f'  JSON解析成功! code={j.get("code")}')
            result = j.get('data', {}).get('result', [])
            print(f'  结果数量: {len(result)}')
            if result:
                item = result[0]
                print(f'  第一条: {json.dumps(item, ensure_ascii=False, indent=2)[:500]}')
        except json.JSONDecodeError as je:
            print(f'  JSON解析失败: {je}')
    except UnicodeDecodeError as ue:
        print(f'  GBK解码失败: {ue}')
        # Try utf-8
        try:
            text_utf8 = raw.decode('utf-8')
            print(f'  UTF-8解码成功: {text_utf8[:300]}')
        except:
            print(f'  UTF-8也失败')
            print(f'  原始文本(r.text): {r.text[:300]}')
            
except Exception as e:
    print(f'  ERROR: {e}')

print()

# ============================================================
# 2. mee.gov.cn - TRS returns HTML with results
# ============================================================
print("="*60)
print("2. mee.gov.cn (生态环境部) - TRS HTML解析")
print("="*60)

# The TRS search returns HTML - let's fetch page 1 and find the result structure
r2 = s.get(
    'https://www.mee.gov.cn/was5/web/search?channelid=270514&searchword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&page=1&perpage=10',
    timeout=20, verify=False
)
r2.encoding = 'utf-8'
t2 = r2.text

# Save full response for analysis
with open('results/mee_page1.html', 'w', encoding='utf-8') as f:
    f.write(t2)
print(f'  已保存响应到 results/mee_page1.html (len={len(t2)})')

# Find result items - TRS typically outputs results as:
# <div class="list-item"> or <li> with title link and date
# Let's find all <a> tags with href containing mee.gov.cn
links = re.findall(r'<a[^>]+href="([^"]+mee\.gov\.cn[^"]+)"[^>]*>([^<]+)</a>', t2)
print(f'  找到 {len(links)} 个含mee.gov.cn的链接')
for href, text in links[:5]:
    print(f'    {text.strip()[:50]} -> {href}')

# Also look for result container patterns
for pattern in [r'<div[^>]+class="[^"]*list[^"]*"[^>]*>', 
              r'<li[^>]*>', 
              r'class="[^"]*result[^"]*"']:
    found = re.findall(pattern, t2, re.IGNORECASE)
    if found:
        print(f'  找到 {len(found)} 个 "{pattern}" 元素')

# Find all dates in the page
dates = re.findall(r'(\d{4}-\d{2}-\d{2})', t2)
print(f'  找到 {len(dates)} 个日期, 前10个: {dates[:10]}')

# Look for the result list area - find "list" div
list_idx = t2.find('id="list"')
if list_idx >= 0:
    snippet = t2[list_idx:list_idx+1000]
    print(f'  #list 区域: {snippet[:500]}')
    
# Check if results are in the response or loaded via AJAX
# The page has: wasurl="/was5/web/search?channelid=270514&searchword=...&page=..."
# This suggests the same URL returns the result HTML via AJAX
# Let's look at what the AJAX response should look like
print()

# ============================================================
# 3. nda.gov.cn - Find the v8d5 API
# ============================================================
print("="*60) 
print("3. nda.gov.cn (国家档案局) - v8d5 API")
print("="*60)

# From the JS: getWay_url + "/admin/ams-service/openApi/open/sjj/3/ssapi/h5ss"
# This is for search suggestions. The actual search might be different.
# Let's look at the page more carefully.
# The page URL is: /sjj/xxgk/search_xxgk/list/index_pc.html?keyword=...
# The results are loaded to <tbody id="searchresult">
# This suggests an AJAX call fills #searchresult

# Let's look for the AJAX URL in the JS files
# From nda_xxgksearch.js - the getList function should have the URL
# Let's fetch the JS again and look more carefully

r3_js = s.get('https://www.nda.gov.cn/sjj/js/xxgksearch/list/index_pc.js', 
               timeout=15, verify=False)
js3 = r3_js.text
print(f'  JS大小: {len(js3)}')

# Find getList function fully
getlist_match = re.search(r'function\s+getList\s*\([^)]*\)\s*\{([\s\S]*?)\}', js3)
if getlist_match:
    func_body = getlist_match.group(1)
    print(f'  getList函数体 (前500字符):')
    print(func_body[:500])
    
    # Find URL in the function
    url_match = re.search(r'url\s*:\s*["\']([^"\']+)["\']', func_body)
    if url_match:
        print(f'  AJAX URL: {url_match.group(1)}')

# Also check the other JS file
r3_js2 = s.get('https://www.nda.gov.cn/sjj/res/js/zwgk0723.js', 
                timeout=15, verify=False)
js3b = r3_js2.text
print(f'  zwgk0723.js 大小: {len(js3b)}')
# Find URL patterns
urls_js3b = re.findall(r'["\']([^"\']*(?:search|list|data|ajax)[^"\']*)["\']\s*', js3b, re.IGNORECASE)
print(f'  URL patterns: {urls_js3b[:10]}')

# Try directly accessing potential API endpoints for nda
# The site is 国家档案局 (National Archives Administration)
# Common pattern: /sjj/xxgk/search_xxgk/api/... or similar
test_urls = [
    'https://www.nda.gov.cn/sjj/xxgk/search_xxgk/api/list?keyword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&page=1&pageSize=10',
    'https://www.nda.gov.cn/sjj/xxgk/api/search?keyword=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&page=1',
]
for url in test_urls:
    try:
        r = s.get(url, timeout=10, verify=False)
        r.encoding = 'utf-8'
        print(f'  [{r.status_code}] {url[:80]} len={len(r.text)}')
    except Exception as e:
        print(f'  ERROR {url[:50]}: {e}')

print()

# ============================================================
# 4. mof.gov.cn - TRS - need correct channelid and approach
# ============================================================
print("="*60)
print("4. mof.gov.cn (财政部) - TRS")
print("="*60)

# The TRS page at search.mof.gov.cn returns a placeholder
# The actual search might be on a different URL or needs POST
# Let's try the main mof.gov.cn search page
r4 = s.get('https://www.mof.gov.cn/search?q=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD', 
           timeout=15, verify=False)
r4.encoding = 'utf-8'
print(f'  www.mof.gov.cn/search: [{r4.status_code}] len={len(r4.text)}')

# Try the TRS with POST (TRS sometimes uses POST)
try:
    r4_post = s.post('https://search.mof.gov.cn/was5/web/search',
                      data={'searchword': '人工智能', 'channelid': '271782', 'page': '1'},
                      timeout=15, verify=False)
    r4_post.encoding = 'utf-8'
    print(f'  POST search.mof.gov.cn: [{r4_post.status_code}] len={len(r4_post.text)}')
    if len(r4_post.text) > 1000:
        print(f'    内容: {r4_post.text[:500]}')
except Exception as e:
    print(f'  POST ERROR: {e}')

# Try to find the search page on mof.gov.cn
# Let's check the main site's search
r4_main = s.get('https://www.mof.gov.cn/', timeout=15, verify=False)
print(f'  www.mof.gov.cn: [{r4_main.status_code}]')

print()
print("="*60)
print("分析完成")
print("="*60)
