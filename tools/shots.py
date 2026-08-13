"""
Capture the screenshots the README embeds.

Storefront only. The theme-editor and admin-inventory shots have to be taken by
hand because they need a logged-in admin session; drop those in as
docs/screenshots/theme-editor.png and docs/screenshots/inventory.png.

Usage:
  PURELANE_URL=https://your-store.myshopify.com PURELANE_PW=... python tools/shots.py
"""
import os, sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)
URL = os.environ["PURELANE_URL"].rstrip("/")
PW = os.environ.get("PURELANE_PW", "")


def unlock(pg):
    if not PW:
        return
    pg.goto(URL + "/password", wait_until="domcontentloaded")
    try:
        pg.fill("input[name='password']", PW)
        pg.press("input[name='password']", "Enter")
        pg.wait_for_load_state("networkidle")
    except Exception:
        pass


def settle(pg):
    # The reveal animation is intersection-driven; force it so a screenshot
    # never catches a half-faded section.
    pg.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
    pg.wait_for_timeout(1200)


with sync_playwright() as p:
    b = p.chromium.launch()

    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    unlock(pg)
    pg.goto(URL, wait_until="networkidle")
    settle(pg)
    pg.screenshot(path=os.path.join(OUT, "hero.png"))
    print("  hero.png")

    for sel, name in [("#shop", "shop-grid.png"), ("#bundles", "bundles.png"),
                      ("#combos", "combos.png"), ("#reviews", "reviews.png")]:
        pg.locator(sel).scroll_into_view_if_needed()
        settle(pg)
        pg.locator(sel).screenshot(path=os.path.join(OUT, name))
        print("  " + name)

    # Cart, proving the buy path end to end. The button is a real product form,
    # so this is the same path a customer takes, not an API call.
    pg.goto(URL, wait_until="networkidle")
    settle(pg)
    pg.locator("#shop").scroll_into_view_if_needed()
    pg.wait_for_timeout(600)
    pg.locator("#shop .card form button[type=submit]:not([disabled])").first.click()
    pg.wait_for_load_state("networkidle")
    pg.goto(URL + "/cart", wait_until="networkidle")
    pg.wait_for_timeout(900)
    pg.screenshot(path=os.path.join(OUT, "cart.png"))
    print("  cart.png")
    ctx.close()

    ctx = b.new_context(viewport={"width": 390, "height": 1100})
    pg = ctx.new_page()
    unlock(pg)
    pg.goto(URL, wait_until="networkidle")
    settle(pg)
    pg.locator("#shop").scroll_into_view_if_needed()
    settle(pg)
    pg.locator("#shop").screenshot(path=os.path.join(OUT, "shop-grid-mobile.png"))
    print("  shop-grid-mobile.png")
    ctx.close()

    b.close()
print("\nwritten to docs/screenshots/")
