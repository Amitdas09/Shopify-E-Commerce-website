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

    # original
    pg = b.new_context(viewport={"width": 1280, "height": 1000}).new_page()
    pg.goto(PROTO, wait_until="networkidle")
    pg.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
    pg.wait_for_timeout(1200)
    pg.locator("#shop").scroll_into_view_if_needed()
    pg.wait_for_timeout(1200)
    pg.locator("#shop").screenshot(path=os.path.join(OUT, "SHOP-original.png"))
    card = pg.evaluate("""() => {
      const c = document.querySelector('#shop .card');
      return {html: c.outerHTML.replace(/<svg[\\s\\S]*?<\\/svg>/g,'<SVG/>').slice(0,700)};
    }""")
    print("ORIGINAL first card:\n", card["html"], "\n")

    # live
    pg2 = b.new_context(viewport={"width": 1280, "height": 1000}).new_page()
    pg2.goto(URL + "/password", wait_until="domcontentloaded")
    if pg2.locator('input[type="password"]').count():
        pg2.fill('input[type="password"]', PW)
        pg2.press('input[type="password"]', "Enter")
        pg2.wait_for_load_state("networkidle")
    pg2.goto(URL, wait_until="networkidle")
    pg2.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
    pg2.wait_for_timeout(1000)
    pg2.locator("#shop").scroll_into_view_if_needed()
    pg2.wait_for_timeout(1500)
    pg2.locator("#shop").screenshot(path=os.path.join(OUT, "SHOP-live.png"))
    card2 = pg2.evaluate("""() => {
      const c = document.querySelector('#shop .card');
      return {html: c.outerHTML.replace(/<svg[\\s\\S]*?<\\/svg>/g,'<SVG/>')
                    .replace(/srcset="[^"]*"/g,'srcset="…"').slice(0,700)};
    }""")
    print("LIVE first card:\n", card2["html"])
    b.close()
