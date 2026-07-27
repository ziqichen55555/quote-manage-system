import re, json, urllib.request, html
from urllib.parse import urljoin

base = "https://www.reware-project.com"
# paginate shop - try common Odoo shop URLs
urls = [
    f"{base}/shop",
    f"{base}/shop/page/2",
    f"{base}/shop/page/3",
    f"{base}/shop/page/4",
    f"{base}/shop/page/5",
    f"{base}/shop/page/6",
    f"{base}/shop/page/7",
    f"{base}/shop/page/8",
    f"{base}/shop/page/9",
    f"{base}/shop/page/10",
]
# also category pages if linked
seen = set()
products = []  # {name, href, img, sku?}

for url in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"FAIL {url}: {e}")
        continue
    # Odoo website_sale product cards
    # look for oe_product_image / product_detail links
    for m in re.finditer(r'<a[^>]+href="(/shop/[^"]+)"[^>]*>', text):
        href = m.group(1)
        if "/page/" in href or href.rstrip("/") == "/shop":
            continue
        seen.add(href)
    # try to parse product blocks more carefully
    # Card pattern: product name + image src
    blocks = re.split(r'oe_product_image|o_wsale_product_grid', text)
    print(f"{url}: len={len(text)} product_links~{len(re.findall(r'/shop/[^\"\\s]+-\\d+', text))}")

# Collect unique product URLs from all pages
prod_hrefs = set()
for url in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception:
        continue
    for m in re.finditer(r'href="(/shop/[^"?#]+-\d+)"', text):
        prod_hrefs.add(m.group(1))

print("unique_product_urls", len(prod_hrefs))
# sample
for h in sorted(prod_hrefs)[:5]:
    print(" ", h)
