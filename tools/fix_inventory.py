"""
Put real inventory behind the products, from tools/seed-products.csv.

The CSV asks for `shopify` as the inventory tracker on every variant, with
per-product quantities and `deny` as the policy — so that
washing-machine-cleaner, seeded at 0, is a genuinely sold-out product and the
rest are genuinely buyable. That is the edge case the brief asks for: the card
has to render an out-of-stock state driven by real Shopify inventory, not by a
hardcoded flag.

Shopify's CSV importer did not apply the tracker column. Every variant landed
untracked, which makes the quantities decorative — Shopify neither decrements
them nor blocks a sale. This turns tracking on, sets the policy, and writes the
CSV quantity to the store's location.

Usage:
  SHOPIFY_STORE=... SHOPIFY_TOKEN=... python tools/fix_inventory.py
  --dry to print the plan without writing

Needs read_inventory and write_inventory on the custom app, plus the usual
read_products / write_products.
"""

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "seed-products.csv")
API = "2025-01"

STORE = os.environ.get("SHOPIFY_STORE", "").strip().replace("https://", "").rstrip("/")
TOKEN = os.environ.get("SHOPIFY_TOKEN", "").strip()
if not STORE or not TOKEN:
    sys.exit("Set SHOPIFY_STORE and SHOPIFY_TOKEN.")


def call(query, variables=None):
    req = urllib.request.Request(
        "https://%s/admin/api/%s/graphql.json" % (STORE, API),
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": TOKEN},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s\n%s" % (e.code, e.read().decode(errors="replace")[:400]))
    if "errors" in payload:
        sys.exit(json.dumps(payload["errors"], indent=2))
    return payload["data"]


LOCATIONS = "{ locations(first: 5) { nodes { id } } }"

PRODUCT = """
query($handle: String!) {
  productByHandle(handle: $handle) {
    id title
    variants(first: 10) {
      nodes { id inventoryPolicy inventoryItem { id tracked } }
    }
  }
}
"""

SET_VARIANT = """
mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id inventoryPolicy inventoryItem { tracked } }
    userErrors { field message }
  }
}
"""

SET_QUANTITIES = """
mutation($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) {
    inventoryAdjustmentGroup { reason }
    userErrors { field message }
  }
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="print the plan, write nothing")
    args = ap.parse_args()

    locs = call(LOCATIONS)["locations"]["nodes"]
    if not locs:
        sys.exit("This store has no locations — inventory cannot be stocked anywhere.")
    location_id = locs[0]["id"]
    print("location: %s%s\n" % (location_id, "  (+%d more, using the first)"
                                % (len(locs) - 1) if len(locs) > 1 else ""))

    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    done = failed = 0

    for row in rows:
        handle = row["Handle"].strip()
        if not handle:
            continue
        qty = int(row["Variant Inventory Qty"] or 0)
        policy = (row["Variant Inventory Policy"] or "deny").strip().upper()
        tracked = (row["Variant Inventory Tracker"] or "").strip().lower() == "shopify"

        if args.dry:
            print("  %-32s qty=%-4d policy=%-8s tracked=%s" % (handle, qty, policy, tracked))
            continue

        product = call(PRODUCT, {"handle": handle}).get("productByHandle")
        if not product:
            print("  !  %-32s not found" % handle)
            failed += 1
            continue

        variants = product["variants"]["nodes"]

        result = call(SET_VARIANT, {
            "productId": product["id"],
            "variants": [{
                "id": v["id"],
                "inventoryPolicy": policy,
                "inventoryItem": {"tracked": tracked},
            } for v in variants],
        })
        errs = result["productVariantsBulkUpdate"]["userErrors"]
        if errs:
            print("  !  %-32s variant: %s" % (handle, errs))
            failed += 1
            continue

        if tracked:
            # setQuantities is absolute, not a delta, so re-running is safe and
            # lands on the CSV figure whatever the store drifted to.
            result = call(SET_QUANTITIES, {"input": {
                "name": "available",
                "reason": "correction",
                "ignoreCompareQuantity": True,
                "quantities": [{
                    "inventoryItemId": v["inventoryItem"]["id"],
                    "locationId": location_id,
                    "quantity": qty,
                } for v in variants],
            }})
            errs = result["inventorySetQuantities"]["userErrors"]
            if errs:
                print("  !  %-32s quantity: %s" % (handle, errs))
                failed += 1
                continue

        state = "SOLD OUT" if (tracked and qty == 0 and policy == "DENY") else "buyable"
        print("  ok %-32s %-4d  %-8s  %s" % (handle, qty, policy, state))
        done += 1

    if not args.dry:
        print("\n%d updated, %d failed" % (done, failed))


if __name__ == "__main__":
    main()
