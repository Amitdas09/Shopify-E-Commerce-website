"""
Generate Purelane product images.

The prototype drew every bottle as an inline SVG built from rounded rectangles,
one per product, in a per-product shade of the brand purple. Those bottles *are*
the design — swapping in stock photography would change the look of the page.

So this redraws the same geometry as real raster images that can be uploaded to
Shopify as product photos, at a size that suits the largest srcset step.

Usage:  python tools/make_product_images.py
Output: tools/seed-images/*.png  (1600x1600, transparent)
"""

import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), "seed-images")
SIZE = 1600
SS = 2  # supersample factor for clean edges
LABEL = (250, 247, 253)


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rounded(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def gradient_body(size, box, radius, rgb, a0=0.95, a1=0.62):
    """Diagonal alpha ramp, matching the prototype's linearGradient(0,0 -> 1,1)."""
    x0, y0, x1, y1 = box
    w, h = int(x1 - x0), int(y1 - y0)
    if w <= 0 or h <= 0:
        return Image.new("RGBA", size, (0, 0, 0, 0))

    ramp = Image.new("L", (w, h))
    px = ramp.load()
    for y in range(h):
        for x in range(w):
            t = (x / max(w - 1, 1) + y / max(h - 1, 1)) / 2.0
            px[x, y] = int(round(255 * (a0 + (a1 - a0) * t)))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    ramp.putalpha  # no-op, kept explicit below

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    tile = Image.new("RGBA", (w, h), rgb + (255,))
    alpha = Image.new("L", (w, h))
    alpha.paste(ramp, (0, 0))
    alpha = Image.composite(alpha, Image.new("L", (w, h), 0), mask)
    tile.putalpha(alpha)
    layer.paste(tile, (int(x0), int(y0)), tile)
    return layer


def draw_bottle(colour, view_w, view_h, geometry):
    """Render one bottle. geometry values are in the prototype's viewBox units."""
    rgb = hex_rgb(colour)
    canvas = SIZE * SS

    # Fit the viewBox into the square canvas with a small margin.
    margin = 0.06
    scale = min(canvas * (1 - 2 * margin) / view_w, canvas * (1 - 2 * margin) / view_h)
    ox = (canvas - view_w * scale) / 2
    oy = (canvas - view_h * scale) / 2

    def S(*vals):
        return [v * scale for v in vals]

    def box(x, y, w, h):
        return [ox + x * scale, oy + y * scale, ox + (x + w) * scale, oy + (y + h) * scale]

    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))

    cap, neck, body, label, l1, l2 = geometry

    # cap + neck
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    rounded(d, box(*cap[:4]), S(cap[4])[0], rgb + (int(255 * 0.85),))
    d.rectangle(box(*neck), fill=rgb + (int(255 * 0.70),))
    img = Image.alpha_composite(img, over)

    # body with diagonal gradient
    img = Image.alpha_composite(img, gradient_body(img.size, box(*body[:4]), S(body[4])[0], rgb))

    # label plate + two copy bars
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    rounded(d, box(*label[:4]), S(label[4])[0], LABEL + (int(255 * 0.88),))
    rounded(d, box(*l1), S(4)[0], rgb + (int(255 * 0.55),))
    rounded(d, box(*l2), S(4)[0], rgb + (int(255 * 0.35),))
    img = Image.alpha_composite(img, over)

    return img.resize((SIZE, SIZE), Image.LANCZOS)


# Geometry lifted from the prototype's SVGs: (cap, neck, body, label, line1, line2)
TALL = (
    (149.9, 0, 80.1, 59.5, 17.6),
    (161.2, 53.6, 57.7, 41.7),
    (72.2, 119.0, 235.6, 476.0, 37.7),
    (100.5, 261.8, 179.1, 161.8, 11.8),
    (128.7, 309.4, 122.5, 21.4),
    (142.9, 352.2, 94.2, 16.7),
)

PUMP = (
    (94.7, 0, 50.6, 32.2, 11.1),
    (101.8, 29.0, 36.4, 22.5),
    (45.6, 64.4, 148.8, 257.6, 23.8),
    (63.5, 141.7, 113.1, 87.6, 7.4),
    (81.3, 167.4, 77.4, 11.6),
    (90.2, 190.6, 59.5, 9.0),
)

TUB = (
    (118.4, 0, 63.2, 42.9, 13.9),
    (127.2, 38.6, 45.5, 30.0),
    (57.0, 85.8, 186.0, 343.2, 29.8),
    (79.3, 188.8, 141.4, 116.7, 9.3),
    (101.6, 223.1, 96.7, 15.4),
    (112.8, 254.0, 74.4, 12.0),
)

PRODUCTS = [
    # handle,                              colour,   viewBox w,h,  geometry
    ("tap-cleaner-limescale-remover",      "#6250ad", 380, 595, TALL),
    ("kitchen-cleaner-foaming",            "#6b55b8", 380, 595, TALL),
    ("copper-bronze-brass-cleaner",        "#55429b", 300, 429, TUB),
    ("dishwash-gel",                       "#4b3a8f", 380, 609, TALL),
    ("laundry-detergent",                  "#5a46a3", 380, 603, TALL),
    ("floor-cleaner",                      "#8168c9", 380, 602, TALL),
    ("toilet-cleaner",                     "#7a62c2", 380, 619, TALL),
    ("liquid-handwash",                    "#8f74d4", 240, 322, PUMP),
    ("washing-machine-cleaner",            "#4b3a8f", 300, 488, TUB),
    ("kitchen-degreaser-refill-pouch",     "#6b55b8", 380, 595, TALL),
    # combo products reuse the hero bottle shades
    ("kitchen-essentials-combo",           "#6b55b8", 380, 595, TALL),
    ("laundry-care-bundle",                "#5a46a3", 380, 603, TALL),
    ("complete-home-bundle",               "#4b3a8f", 380, 609, TALL),
    ("bathroom-deep-clean",                "#7a62c2", 380, 619, TALL),
    ("hard-water-solution-kit",            "#6250ad", 380, 595, TALL),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for handle, colour, vw, vh, geom in PRODUCTS:
        img = draw_bottle(colour, vw, vh, geom)
        path = os.path.join(OUT, handle + ".png")
        img.save(path, "PNG", optimize=True)
        print("%-38s %s" % (handle, os.path.getsize(path)))
    print("\n%d images in %s" % (len(PRODUCTS), OUT))
    print("Note: magic-eraser has no image on purpose — it is the required")
    print("      'product with no image' seed case.")


if __name__ == "__main__":
    main()
