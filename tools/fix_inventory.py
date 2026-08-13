"""
Make the seeded catalogue actually purchasable on the storefront.

The CSV import writes Variant Inventory Qty, and the Admin API duly reports
availableForSale: true — but the storefront disagreed and every product rendered
"Sold out", including on Dawn's own product template. The quantities exist
without an inventory level at a location the Online Store can fulfil from, and
the storefront only counts stock it can actually ship.

Correcting the levels needs write_inventory, which the seeding token does not
carry. Turning tracking off is the honest alternative: plenty of real merchants
do not track inventory, an untracked variant is always purchasable, and it keeps
the demo catalogue behaving like a catalogue.

washing-machine-cleaner stays tracked at zero with policy DENY, because "one
product sold out" is one of the three cases the brief requires.

Usage: SHOPIFY_STORE=... SHOPIFY_TOKEN=... python tools/fix_inventory.py
"""

import json
import os
import sys
import urllib.request

STORE = os.environ.get("SHOPIFY_STORE", "").strip()
TOKEN = os.environ.get("SHOPIFY_TOKEN", "").strip()
if not STORE or not TOKEN:
    sys.exit("Set SHOPIFY_STORE and SHOPIFY_TOKEN.")

KEEP_TRACKED = {"washing-machine-cleaner"}


def call(query, variables=None):
    req = urllib.request.Request(
        "https://%s/admin/api/2025-01/graphql.json" % STORE,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": TOKEN},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read())
    if "errors" in payload:
        raise SystemExit(json.dumps(payload["errors"], indent=2))
    return payload["data"]


PRODUCTS = """
query { products(first: 100) { edges { node { id handle
  variants(first: 5) { edges { node { id inventoryItem { id tracked } } } }
} } } }
"""

UPDATE = """
mutation Untrack($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id }
    userErrors { field message }
  }
}
"""


def main():
    data = call(PRODUCTS)
    changed = kept = failed = 0

    for edge in data["products"]["edges"]:
        node = edge["node"]
        handle = node["handle"]

        if handle in KEEP_TRACKED:
            print("  %-34s left tracked at 0 (the sold-out case)" % handle)
            kept += 1
            continue

        variants = [{"id": v["node"]["id"], "inventoryItem": {"tracked": False}}
                    for v in node["variants"]["edges"]]
        if not variants:
            continue

        res = call(UPDATE, {"productId": node["id"], "variants": variants})
        errs = res["productVariantsBulkUpdate"].get("userErrors") or []
        if errs:
            print("  %-34s FAILED  %s" % (handle, errs[0]["message"]))
            failed += 1
        else:
            print("  %-34s tracking off -> purchasable" % handle)
            changed += 1

    print("\nuntracked %d, left tracked %d, failed %d" % (changed, kept, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
