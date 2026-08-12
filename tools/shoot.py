"""
Screenshot the local preview at the widths the brief cares about.

"Pixel-accurate at every width from 375px up" is not a claim you can make by
reading CSS. This renders the preview at each breakpoint and writes a PNG, so
the layout can actually be looked at before anything reaches a store.

Usage: python tools/shoot.py [--full]
Output: tools/preview/shots/*.png
"""

import argparse
import os
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright is required:  pip install playwright && playwright install chromium")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "tools", "preview", "index.html")
SHOTS = os.path.join(ROOT, "tools", "preview", "shots")

# The widths that actually change this layout, taken from the media queries:
# 420, 760, 860, 900, 1024, 1200 are all real breakpoints in the design.
WIDTHS = [375, 390, 768, 900, 1024, 1200, 1440]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="full-page rather than viewport")
    args = parser.parse_args()

    if not os.path.exists(PAGE):
        sys.exit("no preview yet — run: python tools/preview.py")

    os.makedirs(SHOTS, exist_ok=True)
    url = "file:///" + PAGE.replace("\\", "/")
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for width in WIDTHS:
            page = browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=1)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url, wait_until="networkidle")

            # let the reveal observers settle and the fonts land
            page.wait_for_timeout(900)

            out = os.path.join(SHOTS, "w%04d.png" % width)
            page.screenshot(path=out, full_page=args.full)
            print("  %4dpx  %s" % (width, os.path.basename(out)))
            page.close()

        # Scroll-position captures rather than one full-page shot.
        #
        # full_page is misleading here for two reasons: the backdrop is
        # position:fixed so it only ever paints one viewport's worth, and the
        # reveal observers never fire for content that was never on screen, so
        # every below-fold section photographs as a blank rectangle.
        for width in (1200, 375):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(700)

            height = page.evaluate("document.body.scrollHeight")
            step = 800
            shot = 0
            y = 0

            while y < height:
                page.evaluate("window.scrollTo(0, %d)" % y)
                page.wait_for_timeout(1100)  # let reveals finish transitioning
                page.screenshot(path=os.path.join(SHOTS, "scroll-%d-%02d.png" % (width, shot)))
                shot += 1
                y += step

            print("  %4dpx  %d scroll frames over %dpx" % (width, shot, height))
            page.close()

        browser.close()

    if errors:
        print("\nJavaScript errors on the page:")
        for e in dict.fromkeys(errors):
            print("  %s" % e)
        return 1

    print("\nno JavaScript errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
