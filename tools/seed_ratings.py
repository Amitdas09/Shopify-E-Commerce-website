"""
Write Shopify's STANDARD product rating metafields onto the seeded products.

Why this is a separate script from seed_store.py:

  seed_store.py creates the `purelane.*` namespace — badges, benefit captions,
  combo contents. Those are ours. Ratings are not: `reviews.rating` and
  `reviews.rating_count` are Shopify standard definitions that every review app
  (Judge.me, Okendo, Loox, Yotpo, Shopify Product Reviews) writes to. The theme
  reads the standard keys precisely so that installing a real review app makes
  the "★ 4.8 · 237 reviews" line live with no theme change.

  Seeding them here is therefore demo data standing in for an app that is not
  installed on a dev store — and it is the one metafield set a merchant would
  never hand-write. Keeping it out of seed_store.py keeps that distinction
  honest: delete this data the moment a review app is connected.

Values come from the prototype's own cards. The prototype shelf repeated four
products twice to fill eight tiles; the four it actually specifies keep their
exact numbers, the rest carry counts in the same band, all at the 4.8 the
proof-stats ring advertises.

Usage:
  export SHOPIFY_STORE=your-store.myshopify.com
  export SHOPIFY_TOKEN=shpat_xxxxx
  python tools/seed_ratings.py            # write
  python tools/seed_ratings.py --clear    # remove again (before a real app)
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_VERSION = "2025-01"

STORE = os.environ.get("SHOPIFY_STORE", "").strip().replace("https://", "").rstrip("/")
TOKEN = os.environ.get("SHOPIFY_TOKEN", "").strip()

# handle -> (rating, review count)
RATINGS = {
    # exact values from the prototype's shelf
    "tap-cleaner-limescale-remover": (4.8, 237),
    "kitchen-cleaner-foaming":       (4.8, 254),
    "copper-bronze-brass-cleaner":   (4.8, 231),
    "washing-machine-cleaner":       (4.8, 183),
    # same band, for the tiles the prototype filled by repeating the four above
    "dishwash-gel":                  (4.8, 268),
    "laundry-detergent":             (4.8, 291),
    "floor-cleaner":                 (4.8, 214),
    "toilet-cleaner":                (4.8, 176),
    "liquid-handwash":               (4.8, 205),
    "magic-eraser":                  (4.7, 148),
    "kitchen-degreaser-refill-pouch": (4.8, 132),
}


def call(query, variables=None):
    if not STORE or not TOKEN:
        sys.exit("Set SHOPIFY_STORE and SHOPIFY_TOKEN first. See the header of this file.")

    url = "https://%s/admin/api/%s/graphql.json" % (STORE, API_VERSION)
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": TOKEN},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s from Shopify:\n%s" % (e.code, e.read().decode(errors="replace")[:400]))
    except urllib.error.URLError as e:
        sys.exit("Could not reach %s: %s" % (STORE, e.reason))

    if "errors" in payload:
        sys.exit("GraphQL error:\n%s" % json.dumps(payload["errors"], indent=2))
    return payload["data"]


PRODUCT_BY_HANDLE = """
query($handle: String!) {
  productByHandle(handle: $handle) { id title }
}
"""

SET = """
mutation($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { key }
    userErrors { field message }
  }
}
"""

DELETE = """
mutation($metafields: [MetafieldIdentifierInput!]!) {
  metafieldsDelete(metafields: $metafields) {
    deletedMetafields { key }
    userErrors { field message }
  }
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear", action="store_true",
                    help="delete the seeded ratings instead of writing them")
    args = ap.parse_args()

    written = skipped = 0

    for handle, (rating, count) in RATINGS.items():
        data = call(PRODUCT_BY_HANDLE, {"handle": handle})
        product = data.get("productByHandle")
        if not product:
            print("  !  %-32s not found, skipped" % handle)
            skipped += 1
            continue

        if args.clear:
            result = call(DELETE, {"metafields": [
                {"ownerId": product["id"], "namespace": "reviews", "key": "rating"},
                {"ownerId": product["id"], "namespace": "reviews", "key": "rating_count"},
            ]})
            errs = result["metafieldsDelete"]["userErrors"]
            print("  %s  %-32s cleared" % ("!" if errs else "-", handle))
            if errs:
                print("     %s" % errs)
            continue

        # `rating` is a JSON value, not a bare number: Shopify's rating type
        # carries the scale with the score so a 4.8/5 and a 9.6/10 are
        # distinguishable. The theme reads .rating and .scale_max off it.
        result = call(SET, {"metafields": [
            {
                "ownerId": product["id"],
                "namespace": "reviews",
                "key": "rating",
                "type": "rating",
                "value": json.dumps({
                    "value": str(rating),
                    "scale_min": "1.0",
                    "scale_max": "5.0",
                }),
            },
            {
                "ownerId": product["id"],
                "namespace": "reviews",
                "key": "rating_count",
                "type": "number_integer",
                "value": str(count),
            },
        ]})

        errs = result["metafieldsSet"]["userErrors"]
        if errs:
            print("  !  %-32s %s" % (handle, errs))
            skipped += 1
        else:
            print("  ok %-32s %s  %s reviews" % (handle, rating, count))
            written += 1

    print("\n%d written, %d skipped" % (written, skipped))


if __name__ == "__main__":
    main()
