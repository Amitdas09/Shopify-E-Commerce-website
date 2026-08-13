"""Screenshot the shop grid and the page foot, live against the prototype."""
import os
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = "tools/preview/live"
os.makedirs(OUT, exist_ok=True)
URL = os.environ["PURELANE_URL"].rstrip("/")
PW = os.environ.get("PURELANE_PW", "")
PROTO = "file:///" + os.path.abspath("../purelane-homepage.html").replace(os.sep, "/")

with sync_playwright() as p:
    b = p.chromium.launch()

    pg = b.new_context(viewport={"width": 1280, "height": 1000}).new_page()
    pg.goto(PROTO, wait_until="networkidle")
    pg.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
    pg.mouse.wheel(0, 40000)
    pg.wait_for_timeout(1500)
    pg.locator("footer").screenshot(path=os.path.join(OUT, "FOOT-original.png"))

    ctx = b.new_context(viewport={"width": 1280, "height": 1000})
    pg2 = ctx.new_page()
    if PW:
        pg2.goto(URL + "/password", wait_until="domcontentloaded")
        try:
            pg2.fill("input[name='password']", PW)
            pg2.press("input[name='password']", "Enter")
            pg2.wait_for_load_state("networkidle")
        except Exception:
            pass
    pg2.goto(URL, wait_until="networkidle")
    pg2.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
    pg2.mouse.wheel(0, 40000)
    pg2.wait_for_timeout(2000)
    pg2.locator("#shop").scroll_into_view_if_needed()
    pg2.wait_for_timeout(1200)
    pg2.locator("#shop").screenshot(path=os.path.join(OUT, "SHOP-live.png"))
    pg2.mouse.wheel(0, 40000)
    pg2.wait_for_timeout(1500)
    pg2.locator(".purelane-footer").screenshot(path=os.path.join(OUT, "FOOT-live.png"))

    b.close()

print("done")
