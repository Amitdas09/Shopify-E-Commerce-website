import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
URL = os.environ["PURELANE_URL"].rstrip("/")
PW = os.environ.get("PURELANE_PW", "")

fails = []

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.on("response", lambda r: fails.append("%s %s" % (r.status, r.url.split("/")[-1][:70]))
          if (".woff" in r.url or r.status >= 400) else None)

    pg.goto(URL + "/password", wait_until="domcontentloaded")
    if pg.locator('input[type="password"]').count():
        pg.fill('input[type="password"]', PW)
        pg.press('input[type="password"]', "Enter")
        pg.wait_for_load_state("networkidle")
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(2500)

    print("FONT / FAILED REQUESTS:")
    for f in dict.fromkeys(fails):
        print("   " + f)

    d = pg.evaluate("""async () => {
      await document.fonts.ready;
      const loaded = [...document.fonts].map(f => f.family + ' ' + f.weight + ' ' + f.status);
      const h = document.querySelector('.purelane .d2');
      const cs = h ? getComputedStyle(h) : null;
      return {
        fontFaces: loaded,
        outfitLoaded: document.fonts.check('800 40px Outfit'),
        interLoaded: document.fonts.check('400 16px Inter'),
        headingFamily: cs ? cs.fontFamily : '-',
        headingWeight: cs ? cs.fontWeight : '-',
        headingText: h ? h.innerText.slice(0, 30) : '-'
      };
    }""")
    for k, v in d.items():
        print("  %-15s %s" % (k, v))

    b.close()
