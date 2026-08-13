"""
Screenshot the live store, through the storefront password gate.

The local preview shims Shopify. This is the real renderer, the real catalogue
and the real CDN — the only check that actually counts.

Usage:
  PURELANE_URL=https://xxx.myshopify.com PURELANE_PW=... python tools/shoot_live.py
"""

import os
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("pip install playwright && playwright install chromium")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "preview", "live")

URL = os.environ.get("PURELANE_URL", "").rstrip("/")
PW = os.environ.get("PURELANE_PW", "")

if not URL:
    sys.exit("Set PURELANE_URL.")


def main():
    os.makedirs(OUT, exist_ok=True)
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append("console: " + m.text)
                if m.type == "error" else None)

        # storefront password gate
        page.goto(URL + "/password", wait_until="domcontentloaded")
        if PW and page.locator('input[type="password"]').count():
            page.fill('input[type="password"]', PW)
            page.press('input[type="password"]', "Enter")
            page.wait_for_load_state("networkidle")
            print("password accepted" if "/password" not in page.url else "PASSWORD REJECTED")

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(2500)

        title = page.title()
        print("title: %s" % title)

        counts = page.evaluate("""() => ({
          sections:  document.querySelectorAll('.purelane').length,
          cards:     document.querySelectorAll('.purelane .card').length,
          combos:    document.querySelectorAll('.purelane .combo').length,
          tiers:     document.querySelectorAll('.purelane .tier').length,
          reviews:   document.querySelectorAll('.purelane .rcard').length,
          slides:    document.querySelectorAll('.purelane .hslide').length,
          images:    document.querySelectorAll('.purelane img').length,
          broken:    [...document.querySelectorAll('.purelane img')]
                       .filter(i => i.complete && i.naturalWidth === 0).length,
          placeholders: document.querySelectorAll('.pl-pimg--empty').length,
          soldout:   [...document.querySelectorAll('.purelane button[disabled]')].length,
          height:    document.body.scrollHeight
        })""")
        for k, v in counts.items():
            print("  %-13s %s" % (k, v))

        # scroll so reveals fire, then capture
        height = counts["height"]
        step = 800
        shot = y = 0
        while y < height:
            page.evaluate("window.scrollTo(0, %d)" % y)
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(OUT, "d-%02d.png" % shot))
            shot += 1
            y += step
        print("desktop frames: %d over %dpx" % (shot, height))

        m = ctx.new_page()
        m.set_viewport_size({"width": 390, "height": 844})
        m.goto(URL, wait_until="networkidle")
        m.wait_for_timeout(2000)
        mh = m.evaluate("document.body.scrollHeight")
        shot = y = 0
        while y < mh and shot < 12:
            m.evaluate("window.scrollTo(0, %d)" % y)
            m.wait_for_timeout(900)
            m.screenshot(path=os.path.join(OUT, "m-%02d.png" % shot))
            shot += 1
            y += 780
        print("mobile frames: %d over %dpx" % (shot, mh))

        browser.close()

    uniq = list(dict.fromkeys(errors))
    if uniq:
        print("\nJS ERRORS (%d):" % len(uniq))
        for e in uniq[:12]:
            print("  " + e[:150])
    else:
        print("\nno JavaScript errors")


if __name__ == "__main__":
    main()
