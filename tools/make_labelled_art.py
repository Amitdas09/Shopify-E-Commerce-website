"""
Render the prototype's LABELLED bottle artwork for every product.

The prototype's shop shelf holds eight cards, and they are not all drawn the
same way. The first four use the flat `.pimg` background silhouettes from the
--p-* custom properties. The last four are inline SVGs of a completely different
order: a trigger spray head, a glass body with highlight runs, a shadow ellipse
on the floor, and a real label carrying the leaf mark, the PURELANE wordmark, a
rule, the product name over two lines and the fill volume.

Those four are the finished artwork. The flat ones read as placeholders that the
designer had not got to yet — which is why extract_product_art.py, which faithfully
rasterised them, produced faithful placeholders.

This takes the two finished templates the prototype defines:

  spray  — trigger head, used for every liquid (gTAP / gKIT / gCOP in the source)
  tub    — wide screw cap, used for the tablets (the `tb`/`tl`/`tc` card)

and applies them across the whole range, with each product's own label copy. The
geometry, gradients, stroke weights, type sizes, letter-spacing and the label
palette are lifted verbatim; only the words change.

Note the label gradient (#04756e -> #4b3a8f -> #013f3d) is a V1 colour that the
V2 light-theme stylesheet never overrides, so it is intentional, not a leftover.

Usage:  python tools/make_labelled_art.py
Output: tools/seed-images/*.png  (transparent, 1600px tall)
Then:   python tools/replace_product_art.py
"""

import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "seed-images", "label")
HEIGHT = 1600

LEAF = (
    '<g transform="translate({x} {y}) scale(.5)" fill="none" stroke="#f0a03c" '
    'stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 21c0-6.5 3.5-11 8-12.5C20 15 16.5 20 12 21Z"/>'
    '<path d="M12 21C12 14.5 8.5 10 4 8.5 4 15 7.5 20 12 21Z"/></g>'
)

GRADS = """
<defs>
<linearGradient id="b" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#ffffff" stop-opacity=".10"/><stop offset=".18" stop-color="#ffffff" stop-opacity=".38"/>
<stop offset=".5" stop-color="#dff3e4" stop-opacity=".10"/><stop offset=".82" stop-color="#ffffff" stop-opacity=".22"/>
<stop offset="1" stop-color="#9fc7b4" stop-opacity=".32"/></linearGradient>
<linearGradient id="l" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#04756e"/><stop offset=".55" stop-color="#4b3a8f"/><stop offset="1" stop-color="#013f3d"/></linearGradient>
<linearGradient id="c" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#8fa89b"/><stop offset=".22" stop-color="#eef6ef"/><stop offset="1" stop-color="#7d938c"/></linearGradient>
</defs>
"""

# ---- trigger-spray body, verbatim from the gTAP / gKIT / gCOP cards ----------
SPRAY = """
<ellipse cx="65" cy="190" rx="40" ry="7" fill="#01201c" opacity=".5"/>
<path d="M40 60V48c0-7 5-12 12-12h13c8 0 13 6 13 13v11Z" fill="url(#c)"/>
<path d="M65 37c11-1 19 3 25 10 3 4 2 9-2 10l-20 3Z" fill="#cfdcd2"/>
<path d="M14 44h27v9H19c-4 0-6-2-6-4s1-5 1-5Z" fill="#cfdcd2"/>
<path d="M44 52c-7 3-11 9-10 16 1 6 5 10 12 10v-6c-4 0-6-2-6-5s2-6 5-7Z" fill="#cfdcd2"/>
<rect x="38" y="56" width="42" height="7" rx="3" fill="#a8bdb2"/>
<rect x="41" y="62" width="36" height="16" rx="4" fill="url(#c)"/>
<path d="M28 96c0-11 6-18 15-24v-8h33v8c9 6 15 13 15 24v62c0 12-8 20-21 20H49c-13 0-21-8-21-20Z" fill="url(#b)" stroke="rgba(255,255,255,.4)" stroke-width="1.4"/>
<rect x="31" y="112" width="66" height="60" rx="6" fill="url(#l)"/>
<rect x="31" y="112" width="66" height="60" rx="6" fill="none" stroke="rgba(236,230,247,.26)" stroke-width="1"/>
{leaf}
<text x="64" y="140" text-anchor="middle" font-family="Outfit, sans-serif" font-size="8.6" font-weight="800" letter-spacing=".7" fill="#faf7fd">PURELANE</text>
<line x1="42" y1="146" x2="86" y2="146" stroke="#f0a03c" stroke-width=".9" opacity=".85"/>
<text x="64" y="156" text-anchor="middle" font-family="Inter, sans-serif" font-size="{fs}" font-weight="700" letter-spacing="1.1" fill="#ece6f7">{l1}</text>
<text x="64" y="164" text-anchor="middle" font-family="Inter, sans-serif" font-size="{fs}" font-weight="700" letter-spacing="1.1" fill="#ece6f7">{l2}</text>
<text x="64" y="171" text-anchor="middle" font-family="Inter, sans-serif" font-size="4.8" font-weight="600" letter-spacing=".9" fill="rgba(236,230,247,.7)">{vol}</text>
<rect x="36" y="98" width="6" height="72" rx="3" fill="#ffffff" opacity=".3"/>
<rect x="86" y="102" width="4" height="64" rx="2" fill="#ffffff" opacity=".18"/>
"""

# ---- screw-cap tub, verbatim from the washing-machine card ------------------
TUB = """
<ellipse cx="65" cy="190" rx="42" ry="7" fill="#01201c" opacity=".5"/>
<rect x="30" y="46" width="70" height="20" rx="7" fill="url(#c)"/>
<ellipse cx="65" cy="46" rx="35" ry="8" fill="#f2f8f2"/>
<path d="M28 66h74v100c0 11-8 18-20 18H48c-12 0-20-7-20-18Z" fill="url(#b)" stroke="rgba(255,255,255,.4)" stroke-width="1.4"/>
<rect x="31" y="96" width="68" height="62" rx="6" fill="url(#l)"/>
<rect x="31" y="96" width="68" height="62" rx="6" fill="none" stroke="rgba(236,230,247,.26)" stroke-width="1"/>
{leaf}
<text x="65" y="124" text-anchor="middle" font-family="Outfit, sans-serif" font-size="8.6" font-weight="800" letter-spacing=".7" fill="#faf7fd">PURELANE</text>
<line x1="43" y1="130" x2="87" y2="130" stroke="#f0a03c" stroke-width=".9" opacity=".85"/>
<text x="65" y="140" text-anchor="middle" font-family="Inter, sans-serif" font-size="{fs}" font-weight="700" letter-spacing="1.1" fill="#ece6f7">{l1}</text>
<text x="65" y="148" text-anchor="middle" font-family="Inter, sans-serif" font-size="{fs}" font-weight="700" letter-spacing="1.1" fill="#ece6f7">{l2}</text>
<text x="65" y="155" text-anchor="middle" font-family="Inter, sans-serif" font-size="4.8" font-weight="600" letter-spacing=".9" fill="rgba(236,230,247,.7)">{vol}</text>
<rect x="36" y="76" width="6" height="80" rx="3" fill="#ffffff" opacity=".3"/>
<rect x="88" y="82" width="4" height="70" rx="2" fill="#ffffff" opacity=".18"/>
"""

# handle -> (shape, label line 1, label line 2, volume)
#
# The four the prototype draws itself keep its exact copy, including its
# abbreviations ("WASHING MC"), so those cards are pixel-identical.
PRODUCTS = {
    "tap-cleaner-limescale-remover":  ("spray", "TAP CLEANER", "LIMESCALE", "500 ML"),
    "kitchen-cleaner-foaming":        ("spray", "KITCHEN", "CLEANER", "500 ML"),
    "copper-bronze-brass-cleaner":    ("spray", "COPPER BRASS", "&amp; BRONZE", "300 ML"),
    "washing-machine-cleaner":        ("tub",   "WASHING MC", "DESCALER", "8 TABLETS"),
    # the rest of the range, same templates, own copy
    "dishwash-gel":                   ("spray", "DISHWASH", "GEL", "500 ML"),
    "laundry-detergent":              ("tub",   "LAUNDRY", "DETERGENT", "1 L"),
    "floor-cleaner":                  ("spray", "FLOOR", "CLEANER", "1 L"),
    "toilet-cleaner":                 ("spray", "TOILET", "CLEANER", "500 ML"),
    "liquid-handwash":                ("spray", "LIQUID", "HANDWASH", "250 ML"),
    "magic-eraser":                   ("tub",   "MAGIC", "ERASER", "2 PACK"),
    "kitchen-degreaser-refill-pouch": ("tub",   "KITCHEN", "DEGREASER", "1 L REFILL"),
    # bundles: the tub reads as a boxed set well enough at card size
    "kitchen-essentials-combo":       ("tub",   "KITCHEN", "ESSENTIALS", "3 PRODUCTS"),
    "laundry-care-bundle":            ("tub",   "LAUNDRY", "CARE BOX", "3 PRODUCTS"),
    "complete-home-bundle":           ("tub",   "COMPLETE", "HOME BOX", "5 PRODUCTS"),
    "bathroom-deep-clean":            ("tub",   "BATHROOM", "DEEP CLEAN", "3 PRODUCTS"),
    "hard-water-solution-kit":        ("tub",   "HARD WATER", "SOLUTION", "2 PRODUCTS"),
}


def build(shape, l1, l2, vol):
    body = SPRAY if shape == "spray" else TUB
    leaf = LEAF.format(x=58 if shape == "spray" else 58,
                       y=120 if shape == "spray" else 104)

    # The prototype sets 6.4px for its four labels. Longer words than those
    # would run past the 66px label panel, so step down rather than overflow —
    # measured against "COPPER BRASS", the widest string it ships.
    longest = max(len(re.sub(r"&\w+;", "&", l1)), len(re.sub(r"&\w+;", "&", l2)))
    fs = 6.4 if longest <= 12 else round(6.4 * 12.0 / longest, 2)

    return ('<svg viewBox="0 0 130 200" width="{w}" height="{h}" '
            'xmlns="http://www.w3.org/2000/svg">{g}{b}</svg>').format(
        w=int(round(HEIGHT * 130.0 / 200.0)), h=HEIGHT, g=GRADS,
        b=body.format(leaf=leaf, fs=fs, l1=l1, l2=l2, vol=vol),
    )


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("pip install playwright && playwright install chromium")

    os.makedirs(OUT, exist_ok=True)
    width = int(round(HEIGHT * 130.0 / 200.0))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(
            viewport={"width": width + 40, "height": HEIGHT + 40}
        ).new_page()

        # Outfit and Inter are named in the artwork. Without them Chromium falls
        # back to a default sans and the wordmark sits at the wrong width, so
        # they are loaded from the theme's own woff2 files before rendering.
        fonts = os.path.join(os.path.dirname(HERE), "assets")
        page.set_content(
            "<style>"
            "@font-face{font-family:'Outfit';src:url('file:///%s') format('woff2');font-weight:500 800}"
            "@font-face{font-family:'Inter';src:url('file:///%s') format('woff2');font-weight:400 700}"
            "html,body{margin:0;background:transparent}"
            "</style>"
            % (os.path.join(fonts, "purelane-outfit.woff2").replace(os.sep, "/"),
               os.path.join(fonts, "purelane-inter.woff2").replace(os.sep, "/"))
        )
        page.evaluate("document.fonts.ready")

        for handle, (shape, l1, l2, vol) in PRODUCTS.items():
            page.evaluate(
                "svg => { document.querySelectorAll('svg').forEach(s => s.remove());"
                "        document.body.insertAdjacentHTML('beforeend', svg); }",
                build(shape, l1, l2, vol),
            )
            page.wait_for_timeout(40)
            page.locator("svg").first.screenshot(
                path=os.path.join(OUT, handle + ".png"), omit_background=True
            )
            print("  ok %-32s %-5s %s / %s / %s" % (handle, shape, l1, l2, vol))

        browser.close()

    print("\n%d images written to %s" % (len(PRODUCTS), OUT))
    print("upload with:  python tools/replace_product_art.py")


if __name__ == "__main__":
    main()
