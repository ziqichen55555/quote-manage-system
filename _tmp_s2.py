import re, urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

base = "https://www.reware-project.com"
UA = {"User-Agent": "Mozilla/5.0"}

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")

# inspect page 1 structure
text = fetch(f"{base}/shop")
# find pagination info / total
for pat in [r'page.*of.*\d+', r'(\d+)\s*products?', r'oe_website_sale', r'o_wsale_products_main_row', r'product_template', r'data-ppg', r'ppg=']:
    ms = re.findall(pat, text, re.I)
    if ms:
        print(pat, ms[:10])

# all /shop/ links
hrefs = sorted(set(re.findall(r'href="(/shop/[^"#?]+)"', text)))
print("page1 hrefs", len(hrefs))
for h in hrefs[:40]:
    print(" ", h)

# category links
cats = sorted(set(re.findall(r'href="(/shop/category/[^"#?]+)"', text)))
print("cats", cats)

# product cards: look for img with product.template
imgs = re.findall(r'<img[^>]+src="([^"]+)"[^>]*>', text)
prod_imgs = [i for i in imgs if "product" in i.lower() or "image" in i.lower()]
print("img_count", len(imgs), "prodish", len(prod_imgs))
for i in prod_imgs[:15]:
    print(" IMG", i[:120])

# write snippet around first product
m = re.search(r'oe_product|o_wsale_product_btn', text)
if m:
    print("snippet at", m.start())
    print(text[m.start():m.start()+800][:800])
