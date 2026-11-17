"""Collect public facts about Tediber's website (PUBLIC DATA), politely.

What is read (robots.txt allowed paths only, 1 request / 10 s, stop at the first 429):
- the homepage and a few information pages (trial, delivery, returns, store locator, mission);
- the product sitemap -> catalogue size by category (keyword in the product URL);
- at most 10 key product pages -> price from the JSON-LD `offers.price` block;
- third-party scripts observed in the public homepage source (name only, no guess about their use).
Never visited: /cart, /checkout, /checkouts/, /account, /search (robots.txt). No form, no account, no order.

    python src/collect_public.py
Raw HTML -> data/raw/public/ (not committed). Aggregates -> data/processed/tediber_*.csv
"""
import html
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

from polite import get

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw" / "public", ROOT / "data" / "processed"
BASE = "https://www.tediber.com"
PAGES = ["/", "/pages/essai-100-nuits", "/pages/livraison", "/pages/retours-produits",
         "/pages/store-locator", "/pages/notre-univers-entreprise-a-mission"]
CATEGORIES = {  # first matching keyword in the product URL handle wins
    "kids": ["enfant", "bebe", "tedi-", "junior", "berceau"],
    "mattress": ["matelas"],
    "topper": ["surmatelas", "sur-matelas"],
    "pillow": ["oreiller", "traversin"],
    "duvet": ["couette"],
    "bed base & bed": ["sommier", "lit-", "tete-de-lit", "pied", "cadre"],
    "bed linen": ["drap", "housse", "taie", "parure", "linge", "plaid", "protege"],
}
SCRIPTS = {  # name -> pattern searched in the public homepage source
    "Shopify": r"cdn\.shopify\.com|Shopify\.theme", "Kameleoon": r"kameleoon",
    "Contentsquare": r"contentsquare|cs-cdn|t\.contentsquare", "Microsoft Clarity": r"clarity\.ms",
    "Google Tag Manager": r"googletagmanager\.com/gtm|GTM-", "Klaviyo": r"klaviyo",
    "Trustpilot widget": r"trustpilot", "Alma (split payment)": r"getalma|alma\.eu|almapay|\balma\b",
    "Judge.me": r"judge\.me|judgeme",
}


def category(handle: str) -> str:
    h = handle.lower()
    if any(k in h for k in ("surmatelas", "sur-matelas")):
        return "topper"
    if h.startswith(("canape", "module-angle")):
        return "sofa"
    if h.startswith("pack"):
        return "bundle"
    if h == "lit":
        return "bed base & bed"
    if h.startswith("protege"):
        return "bed linen"  # mattress / pillow protectors
    for cat, keys in CATEGORIES.items():
        if any(k in h for k in keys):
            return cat
    return "other"


def jsonld_prices(html: str) -> list[float]:
    prices = []
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, flags=re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        for item in data if isinstance(data, list) else [data]:
            offers = item.get("offers") if isinstance(item, dict) else None
            for o in offers if isinstance(offers, list) else [offers] if offers else []:
                for key in ("price", "lowPrice"):
                    if isinstance(o, dict) and o.get(key) not in (None, ""):
                        prices.append(float(o[key]))
    return prices


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    log = []
    for path in PAGES:
        name = "home" if path == "/" else path.split("/")[-1]
        if (RAW / f"{name}.html").exists():  # already read in an earlier run: do not fetch again
            continue
        r = get(BASE + path)
        log.append({"url": BASE + path, "status": r.status_code if r is not None else "not fetched"})
        if r is not None and r.ok:
            (RAW / f"{name}.html").write_text(r.text, encoding="utf-8")

    home = (RAW / "home.html").read_text(encoding="utf-8") if (RAW / "home.html").exists() else ""
    scripts = [{"tool": k, "observed_in_public_homepage_source": bool(re.search(p, home, flags=re.I)),
                "observed_on": today} for k, p in SCRIPTS.items()]
    pd.DataFrame(scripts).to_csv(PROC / "tediber_scripts_observed.csv", index=False)

    r = get(BASE + "/sitemap.xml")  # the index gives the exact URLs of the product / collection sitemaps
    index = re.findall(r"<loc>([^<]+)</loc>", r.text) if r is not None else []
    sub = {k: next((u.replace("&amp;", "&") for u in index if f"sitemap_{k}_1" in u), None)
           for k in ("products", "collections")}
    urls, collections = [], []
    if sub["products"]:
        r = get(sub["products"])
        urls = re.findall(r"<loc>(https://www\.tediber\.com/products/[^<]+)</loc>", r.text) if r is not None else []
    if sub["collections"]:
        r = get(sub["collections"])
        collections = re.findall(r"<loc>(https://www\.tediber\.com/collections/[^<]+)</loc>", r.text) if r is not None else []
    pd.DataFrame({"url": collections}).to_csv(RAW / "collection_urls.csv", index=False)
    cat = pd.DataFrame({"url": pd.Series(urls, dtype="string")})
    cat["handle"] = cat["url"].str.split("/products/").str[-1]
    cat["category"] = cat["handle"].map(category)
    (cat.groupby("category").size().rename("product_urls").reset_index()
        .assign(source="sitemap_products_1.xml", observed_on=today)
        .to_csv(PROC / "tediber_catalogue_by_category.csv", index=False))
    cat[["handle", "category"]].to_csv(RAW / "product_handles.csv", index=False)

    # at most 10 key product pages: first handles of the main categories, flagship-like names first
    picks = []
    for c, n in [("mattress", 4), ("pillow", 2), ("duvet", 2), ("bed base & bed", 2)]:
        sub = cat[cat["category"] == c].copy()
        sub["score"] = sub["handle"].str.len()  # shortest handles are usually the core product
        picks += sub.sort_values("score")["url"].head(n).tolist()
    prices = []
    for url in picks[:10]:
        r = get(url)
        log.append({"url": url, "status": r.status_code if r is not None else "not fetched"})
        if r is None:
            break  # 429 -> stop for good (handled in polite.get)
        p = jsonld_prices(r.text) if r.ok else []
        title = re.search(r"<title>(.*?)</title>", r.text, flags=re.S)
        prices.append({"handle": url.split("/products/")[-1], "category": category(url.split("/products/")[-1]),
                       "title": html.unescape(" ".join(title.group(1).split())).split("|")[0].split(" – ")[0].split(" - Tediber")[0].strip() if title else "",
                       "min_price_eur": min(p) if p else None, "max_price_eur": max(p) if p else None,
                       "source": "JSON-LD offers on the public product page", "observed_on": today})
    pd.DataFrame(prices).to_csv(PROC / "tediber_prices.csv", index=False)
    pd.DataFrame(log).to_csv(RAW / "fetch_log.csv", index=False)
    print(pd.DataFrame(log).to_string(index=False))


if __name__ == "__main__":
    main()
