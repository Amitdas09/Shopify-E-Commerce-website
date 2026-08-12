"""
Render the Purelane sections to a static HTML file, with no Shopify store.

Liquid cannot be opened in a browser. Until the theme is pushed to a store
there is nothing to look at, which makes it very easy to write Liquid that
looks right and renders wrong.

This shims the Shopify objects and filters the sections actually use, feeds
them the same seed catalogue that goes into the store, and renders the real
section files — not a hand-written approximation of them. If a section throws,
it throws here rather than on the store.

It is a preview, not an emulator. Shopify's own renderer is the authority; this
catches the class of mistake that is expensive to find later.

Usage: python tools/preview.py [--open]
Output: tools/preview/index.html
"""

import argparse
import csv
import html
import os
import re
import sys
import webbrowser

try:
    from liquid import Environment
    from liquid import DictLoader
except ImportError:
    sys.exit("python-liquid is required:  pip install python-liquid")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "tools", "preview")


# --------------------------------------------------------------- Shopify shims

def money(value):
    """Shopify stores money in cents. The seed CSV is in rupees, so the loader
    multiplies by 100 and this divides back — same round trip as the platform."""
    try:
        cents = int(value)
    except (TypeError, ValueError):
        return ""
    rupees = cents / 100.0
    if rupees == int(rupees):
        return "₹%s" % format(int(rupees), ",d")
    return "₹%s" % format(rupees, ",.2f")


def asset_url(name):
    return "../../assets/%s" % name


def stylesheet_tag(url):
    return '<link rel="stylesheet" href="%s">' % url


def script_tag(url):
    return '<script src="%s" defer></script>' % url


def image_url(image, width=None, **kwargs):
    if not image:
        return ""
    src = image.get("src") if isinstance(image, dict) else str(image)
    return src


def _intrinsic(src):
    """Real pixel dimensions, so the browser lays the image out on its true
    aspect ratio. Hardcoding a square here would mask exactly the bug this
    preview exists to catch."""
    path = os.path.normpath(os.path.join(OUT_DIR, src))
    try:
        from PIL import Image as _Image
        with _Image.open(path) as im:
            return im.size
    except Exception:
        return (800, 800)


def image_tag(src, **kwargs):
    if not src:
        return ""
    iw, ih = _intrinsic(src)
    attrs = {
        "src": src,
        "alt": kwargs.get("alt", ""),
        "loading": kwargs.get("loading", "lazy"),
        "decoding": kwargs.get("decoding", "async"),
        "class": kwargs.get("class", ""),
        "sizes": kwargs.get("sizes", ""),
        "width": str(iw),
        "height": str(ih),
    }
    if kwargs.get("fetchpriority") and kwargs["fetchpriority"] != "auto":
        attrs["fetchpriority"] = kwargs["fetchpriority"]

    return "<img %s>" % " ".join(
        '%s="%s"' % (k, html.escape(str(v), quote=True)) for k, v in attrs.items() if v
    )


def handleize(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def pluralize(count, singular, plural=None):
    try:
        n = int(count)
    except (TypeError, ValueError):
        n = 0
    return singular if n == 1 else (plural if plural is not None else singular + "s")


FILTERS = {
    "money": money,
    "money_with_currency": money,
    "asset_url": asset_url,
    "stylesheet_tag": stylesheet_tag,
    "script_tag": script_tag,
    "image_url": image_url,
    "image_tag": image_tag,
    "handle": handleize,
    "handleize": handleize,
    "pluralize": pluralize,
    "t": lambda v, **k: v,
}


# ------------------------------------------------------------------- tags

SCHEMA_RE = re.compile(r"\{%-?\s*schema\s*-?%\}.*?\{%-?\s*endschema\s*-?%\}", re.S)


def strip_schema(source):
    """{% schema %} is metadata for the theme editor, not output."""
    return SCHEMA_RE.sub("", source)


FORM_OPEN_RE = re.compile(r"\{%-?\s*form\s+'product'[^%]*?-?%\}")
FORM_CLOSE_RE = re.compile(r"\{%-?\s*endform\s*-?%\}")


def shim_form(source):
    """{% form 'product' %} needs the store's routes. A plain <form> is close
    enough for a visual check and keeps the markup structure honest."""
    source = FORM_OPEN_RE.sub('<form method="post" action="/cart/add" class="card-form">', source)
    return FORM_CLOSE_RE.sub("</form>", source)


def preprocess(source):
    return shim_form(strip_schema(source))


# ------------------------------------------------------------------ catalogue

def load_products():
    path = os.path.join(ROOT, "tools", "seed-products.csv")
    products = {}

    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            handle = row["Handle"]
            price = int(float(row["Variant Price"]) * 100)
            compare = row["Variant Compare At Price"]
            compare = int(float(compare) * 100) if compare else 0
            qty = int(row["Variant Inventory Qty"] or 0)
            has_image = bool(row["Image Alt Text"].strip())

            image = None
            if has_image:
                rel = "../seed-images/%s.png" % handle
                if os.path.exists(os.path.join(ROOT, "tools", "seed-images", handle + ".png")):
                    image = {"src": rel, "alt": row["Image Alt Text"]}

            products[handle] = {
                "id": handle,
                "handle": handle,
                "title": row["Title"],
                "url": "/products/%s" % handle,
                "price": price,
                "compare_at_price": compare,
                "price_varies": False,
                "available": qty > 0,
                "featured_image": image,
                "tags": [t.strip() for t in row["Tags"].split(",")],
                "selected_or_first_available_variant": {"id": handle + "-v1"},
                "metafields": {"purelane": Namespace(), "reviews": Namespace()},
            }

    return products


BADGES = {
    "tap-cleaner-limescale-remover": "Best seller",
    "kitchen-cleaner-foaming": "Best seller",
    "copper-bronze-brass-cleaner": "Top rated",
}

BENEFITS = {
    "kitchen-cleaner-foaming": "Cuts grease instantly",
    "dishwash-gel": "Squeaky clean dishes",
    "tap-cleaner-limescale-remover": "Melts hard water stains",
    "laundry-detergent": "Removes tough stains & odour",
    "washing-machine-cleaner": "Deep-cleans your machine",
    "floor-cleaner": "Kills 99.9% germs",
    "liquid-handwash": "Gentle hydration for hands",
    "toilet-cleaner": "Fights limescale in the bowl",
    "magic-eraser": "Scrubs away soap scum",
    "copper-bronze-brass-cleaner": "Brings back the shine",
}

COMBO_ITEMS = {
    "kitchen-essentials-combo": ["kitchen-cleaner-foaming", "dishwash-gel", "tap-cleaner-limescale-remover"],
    "laundry-care-bundle": ["laundry-detergent", "washing-machine-cleaner", "floor-cleaner"],
    "complete-home-bundle": [
        "kitchen-cleaner-foaming", "laundry-detergent", "floor-cleaner",
        "toilet-cleaner", "liquid-handwash",
    ],
    "bathroom-deep-clean": ["toilet-cleaner", "tap-cleaner-limescale-remover", "magic-eraser"],
    "hard-water-solution-kit": ["tap-cleaner-limescale-remover", "toilet-cleaner"],
}

RATINGS = {
    "tap-cleaner-limescale-remover": (4.8, 237),
    "kitchen-cleaner-foaming": (4.8, 254),
    "copper-bronze-brass-cleaner": (4.8, 231),
    "dishwash-gel": (4.9, 402),
    "laundry-detergent": (4.7, 318),
    "floor-cleaner": (4.8, 265),
    "toilet-cleaner": (4.6, 189),
    "liquid-handwash": (4.9, 355),
    "washing-machine-cleaner": (4.5, 96),
    "magic-eraser": (4.7, 143),
    "kitchen-degreaser-refill-pouch": (4.8, 51),
}


class Namespace(dict):
    """Shopify returns nil for a metafield that was never set, and nil is blank.
    python-liquid returns Undefined, which compares unequal to blank — so
    without this the preview shows empty badges that the real store would not.
    An empty string is blank in both."""

    def __missing__(self, key):
        return {"value": ""}


def mf(value):
    """Metafields are drops with a .value. Mirroring that is the whole point —
    it is how the bare-access bug in the review card was found."""
    return {"value": value}


def decorate(products):
    for handle, product in products.items():
        pl = product["metafields"]["purelane"]

        if handle in BADGES:
            pl["badge"] = mf(BADGES[handle])
        if handle in BENEFITS:
            pl["benefit"] = mf(BENEFITS[handle])
        if handle in COMBO_ITEMS:
            pl["combo_items"] = mf([products[h] for h in COMBO_ITEMS[handle] if h in products])
        if handle in RATINGS:
            score, count = RATINGS[handle]
            product["metafields"]["reviews"]["rating"] = mf({"rating": score, "scale_max": 5})
            product["metafields"]["reviews"]["rating_count"] = mf(count)

    products["kitchen-essentials-combo"]["metafields"]["purelane"]["flag"] = mf("Most popular")
    products["complete-home-bundle"]["metafields"]["purelane"]["flag"] = mf("Best value")
    products["complete-home-bundle"]["metafields"]["purelane"]["highlight"] = mf(True)
    products["complete-home-bundle"]["metafields"]["purelane"]["save_label"] = mf("Biggest saving")

    includes = {
        "kitchen-essentials-combo":
            "Includes: Foaming Kitchen Cleaner, Dishwash Gel & Tap Cleaner. Everything for a "
            "sparkling kitchen, no need to pick separately.",
        "laundry-care-bundle":
            "Includes: Laundry Detergent, Fabric Conditioner & Machine Cleaner Powder. Softer, "
            "fresher wash, all in one box.",
        "complete-home-bundle":
            "Includes: Kitchen Cleaner, Laundry Detergent, Floor Cleaner, Toilet Cleaner & "
            "Handwash. Our biggest saving box.",
        "bathroom-deep-clean":
            "Includes: Toilet Cleaner, Tap Cleaner & Magic Eraser. A complete bathroom refresh "
            "in one box.",
        "hard-water-solution-kit":
            "Includes: Tap Cleaner & Toilet Cleaner. A quick, focused fix for hard water stains "
            "across the home.",
    }
    for handle, text in includes.items():
        products[handle]["metafields"]["purelane"]["includes"] = mf(text)

    return products


REVIEWS = [
    ("Works like a charm",
     "Finally an eco option that cleans as well as the chemical detergent I used for years, and it smells better.",
     "Anita", "Laundry detergent", 5),
    ("Best dishwash ever",
     "Our old dishwash left my help with dry, cracked skin. That stopped completely after we switched.",
     "Priya", "Dishwash gel", 5),
    ("Great product, great packaging",
     "Very soft on hands with a lovely fragrance, and it feels good to be using far less plastic.",
     "Sunita", "Liquid handwash", 5),
    ("Dog friendly",
     "We switched because chemical floor cleaners were setting off my dog's allergies. No reactions since.",
     "Rohit S.", "Floor cleaner", 5),
    ("Sparkling taps again",
     "Hard water had ruined our bathroom fittings. Two sprays and the scale wipes straight off, no scrubbing.",
     "Verified buyer", "Tap cleaner", 5),
]


def build_reviews():
    return [
        {
            "title": mf(title),
            "body": mf(body),
            "author": mf(author),
            "context": mf(context),
            "rating": mf(rating),
            "verified": mf(True),
            "product": mf(None),
        }
        for title, body, author, context, rating in REVIEWS
    ]


# --------------------------------------------------------------------- sections

def section(sid, settings, blocks=None):
    return {
        "id": sid,
        "settings": settings,
        "blocks": [
            dict(b, shopify_attributes="", id="%s-%d" % (sid, i))
            for i, b in enumerate(blocks or [])
        ],
    }


def build_sections(products):
    bestsellers = [p for p in products.values() if "bestsellers" in p["tags"]]
    combos = [p for p in products.values() if "combos" in p["tags"]]

    # the long-title and no-image products are pushed into the visible grid on
    # purpose — the point of the preview is to see them fail or hold
    grid = bestsellers + [
        products["magic-eraser"],                 # no image
        products["washing-machine-cleaner"],      # sold out
        products["kitchen-degreaser-refill-pouch"],  # 162-character title
    ]

    return [
        ("purelane-ambient", section("pl-ambient", {
            "show_water": True, "show_vignette": True, "parallax": True,
        })),

        ("purelane-hero", section("pl-hero", {
            "heading": "Clean\nThat",
            "heading_highlight": "Lasts",
            "show_rule": True,
            "subheading": "Homecare that works on the toughest grime, made from plants. Kind to your home, your family and the world outside it.",
            "button_1_label": "Shop now", "button_1_link": "#shop",
            "button_2_label": "How it works", "button_2_link": "#how",
            "stage_label": "Purelane bundles",
            "autoplay_seconds": 4,
            "scene_depth": 1,
        }, [
            {"type": "promise", "settings": {"icon": "leaf", "line_1": "Plant", "line_2": "powered"}},
            {"type": "promise", "settings": {"icon": "shield", "line_1": "Safe for", "line_2": "kids & pets"}},
            {"type": "promise", "settings": {"icon": "no-chem", "line_1": "Zero harsh", "line_2": "chemicals"}},
            {"type": "slide", "settings": {
                "label": "Single bottle",
                "product_1": products["kitchen-cleaner-foaming"],
                "product_2": None, "product_3": None, "price_product": None,
                "saving_style": "percent"}},
            {"type": "slide", "settings": {
                "label": "Any 2 products",
                "product_1": products["tap-cleaner-limescale-remover"],
                "product_2": products["kitchen-cleaner-foaming"],
                "product_3": None,
                "price_product": products["hard-water-solution-kit"],
                "saving_style": "amount"}},
            {"type": "slide", "settings": {
                "label": "Any 3 products",
                "product_1": products["tap-cleaner-limescale-remover"],
                "product_2": products["copper-bronze-brass-cleaner"],
                "product_3": products["kitchen-cleaner-foaming"],
                "price_product": products["kitchen-essentials-combo"],
                "saving_style": "amount"}},
        ])),

        ("purelane-reviews", section("pl-reviews", {
            "kicker": "That's what they said",
            "average_rating": "4.8", "rating_caption": "from 8,000+ reviews",
            "reach_prefix": "Loved by", "reach_number": "12 lakh+", "reach_suffix": "homes",
            "reviews": build_reviews(),
            "rail_label": "Customer reviews",
            "anchor_id": "reviews", "scene_depth": 1,
            "padding_top": 34, "padding_bottom": 34,
        })),

        ("purelane-combos", section("pl-combos", {
            "kicker": "Pre-built to save you money",
            "heading": "Best selling combos", "show_rule": True,
            "subheading": "Swipe through the boxes people order most. Each one is already priced below buying the same products on their own.",
            "source": "picked", "collection": None, "products": combos,
            "combos_to_show": 6,
            "button_label": "Shop bundle",
            "fine_print": "Inclusive of all taxes · COD available",
            "swipe_cue": "Swipe for more combos",
            "rail_note": 'Tapping "Shop bundle" opens the bundle picker with these products already added. You can still swap anything before you pay.',
            "anchor_id": "combos", "scene_depth": 3,
            "padding_top": 34, "padding_bottom": 34,
        })),

        ("purelane-bundles", section("pl-bundles", {
            "kicker": "Build your bundle",
            "heading": "One box. Every room.",
            "subheading": "Mix and match across kitchen, laundry, home and skin. One flat price, no code needed, free shipping either way.",
            "anchor_id": "bundles", "scene_depth": 3,
            "padding_top": 34, "padding_bottom": 34,
        }, [
            {"type": "tier", "settings": {
                "tag": "Starter", "quantity": 2, "quantity_label": "Products",
                "product": products["hard-water-solution-kit"],
                "features": "Pick any two products\nFree shipping across India",
                "highlight": False, "button_label": "Build this box", "button_link": "#shop"}},
            {"type": "tier", "settings": {
                "tag": "Most popular", "quantity": 3, "quantity_label": "Products",
                "product": products["kitchen-essentials-combo"],
                "features": "Pick any three products\nCovers kitchen and laundry\nFree shipping across India",
                "highlight": True, "button_label": "Build this box", "button_link": "#shop"}},
            {"type": "tier", "settings": {
                "tag": "Whole home", "quantity": 5, "quantity_label": "Products",
                "product": products["complete-home-bundle"],
                "features": "Pick any five products\nEvery room in one order\nFree shipping across India",
                "highlight": False, "button_label": "Build this box", "button_link": "#shop"}},
        ])),

        ("purelane-product-grid", section("pl-shop", {
            "kicker": "Bestsellers",
            "heading": "Loved by 30,000 homes",
            "show_rule": True,
            "source": "picked", "collection": None, "products": grid,
            "products_to_show": 12, "columns_desktop": 4, "show_rating": True,
            "anchor_id": "shop", "scene_depth": 3,
            "padding_top": 34, "padding_bottom": 34,
        })),
    ]


# ------------------------------------------------------------------------ main

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Purelane — local section preview</title>
<style>
  html,body{margin:0;padding:0;background:#eee7fb}
  body{padding-bottom:60px}
  .pl-preview-note{
    position:fixed;left:12px;bottom:12px;z-index:9999;max-width:330px;
    font:12px/1.5 ui-sans-serif,system-ui,sans-serif;color:#241a3d;
    background:rgba(255,255,255,.92);border:1px solid rgba(75,58,143,.2);
    border-radius:12px;padding:11px 13px;box-shadow:0 8px 24px rgba(58,44,112,.16)}
  .pl-preview-note b{display:block;margin-bottom:3px;color:#17102b}
  .pl-preview-note button{float:right;margin:-2px -3px 0 8px;border:0;background:none;
    cursor:pointer;font-size:15px;line-height:1;color:#241a3d}
</style>
</head>
<body>
%(body)s
<div class="pl-preview-note">
  <button onclick="this.parentNode.remove()" aria-label="Dismiss">&times;</button>
  <b>Local preview</b>
  Real section files, rendered with the seed catalogue and shimmed Shopify
  filters. Layout, type, colour and motion are live. Cart, routing and
  Shopify's own image CDN are not.
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true", help="open in the default browser")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    # Snippets go through the same preprocessing as sections — {% form %} and
    # {% schema %} appear in both — so they are loaded from a dict rather than
    # straight off disk.
    snippets = {}
    for path in os.listdir(os.path.join(ROOT, "snippets")):
        if not path.endswith(".liquid"):
            continue
        name = os.path.splitext(path)[0]
        with open(os.path.join(ROOT, "snippets", path), encoding="utf-8") as fh:
            snippets[name] = preprocess(fh.read())

    env = Environment(loader=DictLoader(snippets))
    env.filters.update(FILTERS)

    products = decorate(load_products())
    parts = []
    failed = []

    for name, ctx in build_sections(products):
        path = os.path.join(ROOT, "sections", name + ".liquid")
        source = preprocess(open(path, encoding="utf-8").read())

        try:
            template = env.from_string(source, name=name)
            parts.append(template.render(section=ctx, request={"design_mode": False}))
            print("  rendered  %s" % name)
        except Exception as exc:
            failed.append((name, exc))
            print("  FAILED    %s\n            %s: %s" % (name, type(exc).__name__, exc))

    out = os.path.join(OUT_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(PAGE % {"body": "\n".join(parts)})

    print("\n%d of %d sections rendered" % (len(parts), len(parts) + len(failed)))
    print("wrote %s" % out)

    if args.open:
        webbrowser.open("file:///" + out.replace("\\", "/"))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
