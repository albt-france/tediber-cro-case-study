"""Heuristic UX audit of Tediber's public pages (homepage -> category -> product page; never cart or checkout).

Scored by the analyst on 17 Nov 2026 from the public pages (mobile capture at 412 px, desktop from the page source and
the Lighthouse desktop screenshot). 0 = absent, 1 = partly / hard to find, 2 = present and clear.
Findings are written as opportunities to test, not as problems. Writes data/processed/ux_audit.csv and
docs/img/wireframe_pdp_mobile.svg (a drawn page schema: no screenshot, no logo).

    python src/ux_audit.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

GRID = [  # area, criterion, page, mobile, desktop, observation, hypothesis to test (or "keep")
    ("Offer clarity", "Value proposition visible without scrolling", "Home", 2, 2, "Promotion hero, trust line and range entry points at the top", "keep"),
    ("Offer clarity", "Ranges and categories reachable in one tap", "Home", 2, 2, "Icon row (Black Month, mattresses, packs, bed bases, beds) under the header", "keep"),
    ("Offer clarity", "Current promotion explained with its conditions", "Home", 1, 1, "'Jusqu'à -40%' with an asterisk; conditions in the terms of sale", "A one-line condition next to the banner reduces surprise in the cart"),
    ("Reassurance", "Trial period stated near the decision", "Product", 2, 2, "100 nights listed under the add-to-cart button", "keep"),
    ("Reassurance", "Free returns stated near the decision", "Product", 2, 2, "'Livraison et retour gratuit' under the button", "keep"),
    ("Reassurance", "Made-in / certifications visible", "Product", 2, 2, "'Fabriqué en France' and OEKO-TEX badges on product images", "keep"),
    ("Social proof", "Rating and review count next to the price", "Product", 2, 2, "Stars and review count under the product name", "keep"),
    ("Social proof", "Reviews readable on the page", "Product", 2, 2, "Review widget lower on the page", "keep"),
    ("Price & payment", "Price per size clear before choosing", "Product", 1, 1, "'Dès' price shown first; price updates with the size", "Showing the price of the most chosen size first may reduce the 'Dès' gap"),
    ("Price & payment", "Strike-through price and discount consistent", "Category / product", 2, 2, "Old price, new price and % badge shown together", "keep"),
    ("Price & payment", "Split-payment offer stated the same way everywhere", "Banner / home / product", 1, 1, "Banner says 3x to 24x; engagement blocks and product page say 3x to 12x", "One message everywhere (B06)"),
    ("Delivery", "Delivery date shown on the product page", "Product (mattress)", 2, 2, "'Livré dès le ...' estimate under the options", "keep"),
    ("Delivery", "Delivery fee and options for bulky items shown before the cart", "Product (bed base)", 2, 2, "Essential delivery free; room delivery 25 EUR, free from 1,000 EUR", "keep (test C shows how to measure it)"),
    ("Delivery", "Delivery promise consistent by product type", "Banner / bulky pages", 1, 1, "'Livraison en 48h' banner on every page; bulky items 8-10 days per the delivery page", "Adapt the banner on bulky-item pages (B07)"),
    ("Choice support", "Comparison of mattress models", "Category / product", 2, 2, "Comparison table on the category page and comparator on the product page", "keep; judge it on net revenue after returns (test D)"),
    ("Choice support", "Guided choice (quiz)", "Category", 2, 2, "'Quel matelas choisir ?' quiz, under 2 minutes", "Carry the quiz result to the product page (B10)"),
    ("Choice support", "Key specs on product tiles (height, firmness, layers)", "Category", 2, 2, "Three spec lines on every mattress tile", "keep"),
    ("Choice support", "Filters and sort on category pages", "Category", 2, 2, "'Filtrer' and 'Trier par' above the grid", "keep"),
    ("Mobile ergonomics", "Add-to-cart reachable while scrolling", "Product", 2, 2, "Sticky bar with price and button (mobile and desktop)", "keep (test A shows how to measure it)"),
    ("Mobile ergonomics", "Tap targets and text size on mobile", "All", 2, 2, "Large buttons; small grey legal text only", "keep"),
    ("Mobile ergonomics", "Consent panel leaves the page usable", "All", 1, 1, "In our capture the panel covers most of the mobile screen", "Compact layout, to test with the legal team (B14); confirm on a real phone"),
    ("Mobile ergonomics", "Help reachable (chat, phone)", "All", 2, 2, "Chat button bottom right", "keep"),
    ("Performance", "Largest content shown fast on mobile (lab)", "All", 0, 2, "Lab LCP 6.8 s or more on mobile, below 2 s on desktop", "Image and script budget on mobile; confirm with real-user data first (B05)"),
    ("Performance", "Main thread free on mobile (lab blocking time)", "All", 0, 1, "Lab blocking time above 1 s on mobile pages", "Defer non-essential third-party scripts (B05)"),
    ("Performance", "Layout stable while loading", "All", 2, 2, "Lab CLS close to 0 on all pages", "keep"),
    ("Stores", "Physical stores visible for people who want to try", "Product (mattress)", 1, 2, "4 stores in the footer and store locator; not seen near the mattress decision on mobile", "'Try it in store' block (B11)"),
]

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 760" font-family="Segoe UI, Arial, sans-serif" font-size="12">
<rect width="520" height="760" fill="#F2EFE9"/>
<rect x="30" y="20" width="230" height="720" rx="18" fill="#FFFFFF" stroke="#BDB9B0" stroke-width="2"/>
<rect x="30" y="20" width="230" height="22" rx="10" fill="#7A2E2A"/><text x="145" y="35" fill="#fff" text-anchor="middle" font-size="9">promotion banner (48h · 3x-24x)</text>
<rect x="44" y="50" width="202" height="18" fill="#E7E4DD"/><text x="145" y="63" text-anchor="middle" font-size="9" fill="#555">header (menu · search · cart)</text>
<rect x="44" y="76" width="140" height="10" fill="#1F1F1D"/><text x="190" y="85" font-size="9" fill="#555">product name</text>
<rect x="44" y="90" width="90" height="8" fill="#9C9A93"/><text x="140" y="98" font-size="9" fill="#555">price · stars · reviews</text>
<rect x="44" y="104" width="202" height="120" fill="#DCD8CF"/><text x="145" y="168" text-anchor="middle" fill="#555">image carousel</text>
<rect x="44" y="232" width="202" height="26" fill="#FFFFFF" stroke="#9C9A93"/><text x="52" y="249" fill="#555">size selector</text>
<rect x="44" y="264" width="202" height="40" fill="#FFFFFF" stroke="#9C9A93"/><text x="52" y="288" fill="#555">version · cross-sell</text>
<rect x="44" y="310" width="202" height="18" fill="#E3F0E5"/><text x="52" y="323" font-size="10" fill="#2E6B45">in stock · delivered from (date)</text>
<rect x="44" y="334" width="202" height="28" rx="4" fill="#1F1F1D"/><text x="145" y="352" fill="#fff" text-anchor="middle">add to cart</text>
<rect x="44" y="368" width="202" height="16" fill="#EFEDE8"/><text x="52" y="380" font-size="10" fill="#555">split payment 3x 4x 10x 12x</text>
<rect x="44" y="390" width="202" height="46" fill="#FFFFFF" stroke="#D9D6CF"/><text x="52" y="405" font-size="10" fill="#555">free delivery and returns</text><text x="52" y="418" font-size="10" fill="#555">100-night trial</text><text x="52" y="431" font-size="10" fill="#555">split payment 3x to 12x</text>
<rect x="44" y="444" width="202" height="70" fill="#DCD8CF"/><text x="145" y="483" text-anchor="middle" fill="#555">technical sheet · layers</text>
<rect x="44" y="520" width="202" height="70" fill="#FFFFFF" stroke="#D9D6CF"/><text x="145" y="558" text-anchor="middle" fill="#555">mattress comparator</text>
<rect x="44" y="596" width="202" height="60" fill="#EFEDE8"/><text x="145" y="630" text-anchor="middle" fill="#555">reviews</text>
<rect x="30" y="700" width="230" height="40" rx="0" fill="#FFFFFF" stroke="#BDB9B0"/><text x="44" y="724" font-size="10" fill="#555">sticky: size · price</text><rect x="160" y="708" width="90" height="24" rx="4" fill="#1F1F1D"/><text x="205" y="724" fill="#fff" text-anchor="middle" font-size="10">add to cart</text>
<g fill="#D03B3B" font-weight="700">
<circle cx="268" cy="31" r="9"/><text x="268" y="35" fill="#fff" text-anchor="middle">1</text>
<circle cx="268" cy="414" r="9"/><text x="268" y="418" fill="#fff" text-anchor="middle">1</text>
<circle cx="268" cy="164" r="9"/><text x="268" y="168" fill="#fff" text-anchor="middle">2</text>
<circle cx="268" cy="555" r="9"/><text x="268" y="559" fill="#fff" text-anchor="middle">3</text>
<circle cx="268" cy="245" r="9"/><text x="268" y="249" fill="#fff" text-anchor="middle">4</text>
</g>
<g fill="#2A78D6" font-weight="700"><circle cx="268" cy="720" r="9"/><text x="268" y="724" fill="#fff" text-anchor="middle">✓</text>
<circle cx="268" cy="320" r="9"/><text x="268" y="324" fill="#fff" text-anchor="middle">✓</text></g>
<g font-size="12" fill="#1F1F1D">
<text x="290" y="60" font-weight="700" font-size="13">Mattress product page, mobile</text>
<text x="290" y="77" fill="#5E5C57" font-size="11">drawn schema of the public page, 17 Nov 2026</text>
<text x="290" y="110" font-weight="700" fill="#D03B3B">1  One payment message</text><text x="290" y="125" font-size="11">banner 3x-24x, blocks 3x-12x:</text><text x="290" y="139" font-size="11">test a single statement</text>
<text x="290" y="170" font-weight="700" fill="#D03B3B">2  Lighter first screen</text><text x="290" y="185" font-size="11">lab mobile LCP 6.8 s: image</text><text x="290" y="199" font-size="11">and script budget, then real-user check</text>
<text x="290" y="235" font-weight="700" fill="#D03B3B">4  Price of the chosen size</text><text x="290" y="250" font-size="11">'Dès' price first: show the</text><text x="290" y="264" font-size="11">most chosen size by default</text>
<text x="290" y="540" font-weight="700" fill="#D03B3B">3  Comparator + returns</text><text x="290" y="555" font-size="11">already there: measure it on</text><text x="290" y="569" font-size="11">net revenue after the 100 nights</text>
<text x="290" y="315" font-weight="700" fill="#2A78D6">✓  Delivery date, trial, returns,</text><text x="290" y="330" font-size="11" fill="#2A78D6">reviews and sticky bar in place</text>
</g></svg>"""


def main() -> None:
    df = pd.DataFrame(GRID, columns=["area", "criterion", "page", "score_mobile", "score_desktop", "observation", "hypothesis"])
    df["audited_on"] = "2026-11-17"
    df.to_csv(ROOT / "data" / "processed" / "ux_audit.csv", index=False)
    (ROOT / "docs" / "img").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "img" / "wireframe_pdp_mobile.svg").write_text(SVG, encoding="utf-8")
    s = df.groupby("area")[["score_mobile", "score_desktop"]].sum() / (2 * df.groupby("area").size().to_numpy()[:, None])
    print(s.round(2))
    lines = ["# UX audit - Tediber public pages (17 Nov 2026)", "",
             "Heuristic review of the public journey **homepage -> category -> product page** on mobile (412 px) and desktop.",
             "Cart, checkout, account and search were **not** visited (robots.txt). Scores: 0 absent, 1 partly, 2 present and clear.",
             "Findings are written as **opportunities to test**; most good practices are already in place.", "",
             "![Drawn schema of the mobile mattress page](img/wireframe_pdp_mobile.svg)", "",
             f"**Total: mobile {df.score_mobile.sum()}/{2 * len(df)}, desktop {df.score_desktop.sum()}/{2 * len(df)}.**", "",
             "| Area | Criterion | Page | Mobile | Desktop | Observation | Hypothesis to test |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r.area} | {r.criterion} | {r.page} | {r.score_mobile} | {r.score_desktop} | {r.observation} | {r.hypothesis} |"
              for r in df.itertuples()]
    lines += ["", "## Opportunities to test, in Tediber's own pages",
              "1. **One split-payment message** (3x-24x in the banner, 3x-12x in the blocks and on the product page).",
              "2. **Mobile performance budget** - lab mobile LCP and blocking time are high on every page measured; confirm with",
              "   real-user Core Web Vitals (CrUX) before investing, then test lighter images and deferred third-party scripts.",
              "3. **Delivery promise by product type** - the '48h' banner also shows on bulky-item pages (8-10 days).",
              "4. **Measure the comparator and the quiz on net revenue after returns**, not on conversion only (simulated test D).",
              "5. **Carry the quiz result to the product page**; **'try it in store'** near the mattress decision.",
              "", "Already in place (to keep, and to measure the same way): sticky add-to-cart bar, delivery date, delivery options and",
              "fee for bulky items, trial and free returns under the button, reviews next to the price, filters, specs on tiles.",
              "", "*Method: own review of the public pages; no screenshot of the site is published (the schema above is drawn).*"]
    (ROOT / "docs" / "UX_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"total mobile {df.score_mobile.sum()}/{2 * len(df)}, desktop {df.score_desktop.sum()}/{2 * len(df)}")


if __name__ == "__main__":
    main()
