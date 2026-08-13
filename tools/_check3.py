"""Shoot the reviews band, the shop grid, and the rail dot at three scroll depths."""
import os
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = "tools/preview/live"
os.makedirs(OUT, exist_ok=True)
URL = os.environ["PURELANE_URL"].rstrip("/")
PW = os.environ.get("PURELANE_PW", "")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={"width": 1440, "height": 950}).new_page()

    if PW:
        pg.goto(URL + "/password", wait_until="domcontentloaded")
        try:
            pg.fill("input[name='password']", PW)
            pg.press("input[name='password']", "Enter")
            pg.wait_for_load_state("networkidle")
        except Exception:
            pass

    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(1500)

    def rail_state(where):
        st = pg.evaluate("""() => {
          const as = [...document.querySelectorAll('.purelane-rail a')];
          return {
            on: as.filter(a => a.classList.contains('on'))
                  .map(a => a.getAttribute('href')),
            all: as.length,
          };
        }""")
        print("%-12s dots=%d active=%s" % (where, st["all"], st["on"]))

    rail_state("top")
    pg.locator("#reviews").scroll_into_view_if_needed()
    pg.wait_for_timeout(900)
    rail_state("reviews")
    pg.locator("#reviews").screenshot(path=os.path.join(OUT, "REVIEWS-live.png"))

    pg.locator("#proof").scroll_into_view_if_needed()
    pg.wait_for_timeout(900)
    rail_state("proof")

    pg.locator("#shop").scroll_into_view_if_needed()
    pg.wait_for_timeout(900)
    rail_state("shop")
    pg.screenshot(path=os.path.join(OUT, "RAIL-shop.png"))

    pg.locator("#range").scroll_into_view_if_needed()
    pg.wait_for_timeout(900)
    pg.locator("#range").screenshot(path=os.path.join(OUT, "RANGE-live.png"))

    b.close()
