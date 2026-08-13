import os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = "tools/preview/live"; os.makedirs(OUT, exist_ok=True)
URL = os.environ["PURELANE_URL"].rstrip("/"); PW = os.environ["PURELANE_PW"]
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, tag in [(1280, "desktop"), (768, "tablet"), (375, "mobile")]:
        ctx = b.new_context(viewport={"width": w, "height": 900})
        pg = ctx.new_page()
        pg.goto(URL + "/password", wait_until="domcontentloaded")
        try:
            pg.fill("input[name='password']", PW); pg.press("input[name='password']", "Enter")
            pg.wait_for_load_state("networkidle")
        except Exception: pass
        pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(1500)
        pg.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
        pg.locator("#shop").scroll_into_view_if_needed(); pg.wait_for_timeout(1500)
        pg.locator("#shop").screenshot(path=os.path.join(OUT, "FINAL-shop-%s.png" % tag))
        info = pg.evaluate("""() => {
          const cards=[...document.querySelectorAll('#shop .card')];
          return {
            n: cards.length,
            overflow: document.documentElement.scrollWidth > window.innerWidth,
            scrollW: document.documentElement.scrollWidth, vw: window.innerWidth,
            items: cards.map(c => ({
              t: (c.querySelector('.card-title')||{}).innerText || '',
              img: !!c.querySelector('img.pl-pimg'),
              empty: !!c.querySelector('.pl-pimg--empty'),
              btn: (c.querySelector('button,.btn')||{}).innerText || ''
            }))
          };
        }""")
        print("--- %s (%dpx) cards=%d  h-overflow=%s (%d vs %d)" % (
            tag, w, info["n"], info["overflow"], info["scrollW"], info["vw"]))
        for it in info["items"]:
            print("    %-38s img=%-5s empty=%-5s btn=%s" % (
                it["t"][:36].replace("\n"," "), it["img"], it["empty"], it["btn"][:14]))
        ctx.close()
    b.close()
