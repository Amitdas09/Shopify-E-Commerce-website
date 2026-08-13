"""
Render the prototype's own bottle artwork to PNGs for upload as product photos.

The first pass at this redrew the bottles from scratch in Pillow, which can only
ever approximate them. It is not necessary: every `.pimg` in the prototype is a
CSS background pointing at a `--p-*` custom property holding a base64 SVG.
Decoding the artwork the designer actually shipped and rasterising it is exact,
which is the whole point — "this is a build, not a redesign".

These are the *flat* silhouettes, used wherever a product is one element of a
group. The labelled bottles for the shop cards come from make_labelled_art.py.

Chromium does the rasterising because these SVGs use gradients, blurs and
embedded text; cairosvg and Pillow both drop parts of that.

Usage:  python tools/extract_product_art.py
Output: tools/seed-images/*.png  (transparent, 1600px tall, native aspect)
"""

import base64
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, "..", "..", "purelane-homepage.html"))
OUT = os.path.join(HERE, "seed-images", "flat")
HEIGHT = 1600

# prototype art key -> product handle it belongs on.
#
# The prototype has two sets of bottle drawings: the wide "card" set (aspect
# ~0.64) and a narrow hero set (~0.32, the *btl keys). Shopify gives a product
# one featured image and the card grid is where it is read most closely, so the
# card set wins. The hero section caps widths per slide position to cope — see
# the note in purelane-hero.css.
ART = {
    "p-tap":       "tap-cleaner-limescale-remover",
    "p-kitchen":   "kitchen-cleaner-foaming",
    "p-metal":     "copper-bronze-brass-cleaner",
    "p-wm":        "washing-machine-cleaner",
    "p-dish":      "dishwash-gel",
    "p-laundry":   "laundry-detergent",
    "p-floor":     "floor-cleaner",
    "p-toilet":    "toilet-cleaner",
    "p-handwash":  "liquid-handwash",
    "p-eraser":    "magic-eraser",
    "p-combo2":    "hard-water-solution-kit",
}


def svgs_from_prototype():
    html = open(PROTO, encoding="utf-8", errors="replace").read()
    found = {}
    for key, payload in re.findall(
        r"--(p-[a-z0-9]+)\s*:\s*url\(\"data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)\"\)", html
    ):
        found[key] = base64.b64decode(payload).decode("utf-8", "replace")
    return found


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("pip install playwright && playwright install chromium")

    art = svgs_from_prototype()
    missing = [k for k in ART if k not in art]
    if missing:
        print("!! not found in the prototype: %s" % ", ".join(missing))

    os.makedirs(OUT, exist_ok=True)
    written = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # deviceScaleFactor is left at 1 and the SVG is sized explicitly instead,
        # so the vector is rasterised at the target pixel size rather than being
        # drawn small and scaled up.
        page = browser.new_context(viewport={"width": 1200, "height": 1800}).new_page()

        for key, handle in ART.items():
            svg = art.get(key)
            if not svg:
                continue

            box = re.search(r'viewBox="([\d.\s-]+)"', svg)
            if not box:
                print("  !  %-30s no viewBox, skipped" % handle)
                continue
            _, _, vw, vh = [float(n) for n in box.group(1).split()]
            width = int(round(HEIGHT * vw / vh))

            # Force the root <svg> to the render size; several of these carry
            # their own width/height attributes that would otherwise win.
            sized = re.sub(r'<svg([^>]*)>',
                           lambda m: '<svg%s width="%d" height="%d">'
                                     % (re.sub(r'\s(width|height)="[^"]*"', '', m.group(1)),
                                        width, HEIGHT),
                           svg, count=1)

            page.set_content(
                "<style>html,body{margin:0;background:transparent}</style>" + sized
            )
            page.wait_for_timeout(60)
            page.locator("svg").first.screenshot(
                path=os.path.join(OUT, handle + ".png"), omit_background=True
            )
            print("  ok %-30s %dx%d" % (handle, width, HEIGHT))
            written += 1

        browser.close()

    print("\n%d images written to %s" % (written, OUT))
    print("upload with:  python tools/replace_product_art.py")


if __name__ == "__main__":
    main()
