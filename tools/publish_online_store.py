"""
Publish every product and collection to the Online Store sales channel.

Symptom this fixes: every product renders "Sold out", on the Purelane cards and
on Dawn's own product template alike, while the Admin API insists
availableForSale is true.

Cause: a CSV import sets publishedAt but does not create an Online Store
publication, and collectionCreate never does. Without that publication
onlineStoreUrl is null, product.available is false in Liquid, and
/collections/<handle> 404s. The catalogue is there; the storefront simply
cannot sell it.

Needs read_publications and write_publications on the app, in addition to the
six scopes seed_store.py asks for.

Usage: SHOPIFY_STORE=... SHOPIFY_TOKEN=... python tools/publish_online_store.py
"""

import json
import os
import sys
import urllib.request

STORE = os.environ.get("SHOPIFY_STORE", "").strip()
TOKEN = os.environ.get("SHOPIFY_TOKEN", "").strip()
if not STORE or not TOKEN:
    sys.exit("Set SHOPIFY_STORE and SHOPIFY_TOKEN.")


def call(query, variables=None):
    req = urllib.request.Request(
        "https://%s/admin/api/2025-01/graphql.json" % STORE,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": TOKEN},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read())
    if "errors" in payload:
        msg = payload["errors"][0].get("message", "")
        if "access scope" in msg:
            sys.exit(
                "\nMissing scope: %s\n\n"
                "Add read_publications and write_publications to the app:\n"
                "  Settings > Apps and sales channels > Develop apps > your app\n"
                "  > Configuration > Admin API scopes > tick both > Save\n"
                "  > API credentials > Install / Update\n"
                "then run this again.\n" % msg)
        sys.exit(json.dumps(payload["errors"], indent=2))
    return payload["data"]


PUBLICATIONS = "{ publications(first: 20) { edges { node { id name } } } }"
RESOURCES = """
query {
  products(first: 100) { edges { node { id handle onlineStoreUrl } } }
  collections(first: 50) { edges { node { id handle } } }
}
"""
PUBLISH = """
mutation P($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    publishable { availablePublicationsCount { count } }
    userErrors { field message }
  }
}
"""


def main():
    pubs = call(PUBLICATIONS)["publications"]["edges"]
    online = next((p["node"] for p in pubs
                   if p["node"]["name"].lower().startswith("online store")), None)
    if not online:
        sys.exit("No Online Store publication found. Channels: %s"
                 % ", ".join(p["node"]["name"] for p in pubs))

    print("Online Store publication: %s\n" % online["id"])

    data = call(RESOURCES)
    products = [e["node"] for e in data["products"]["edges"]]
    collections = [e["node"] for e in data["collections"]["edges"]]

    done = skipped = failed = 0

    for p in products:
        if p.get("onlineStoreUrl"):
            print("  %-34s already published" % p["handle"])
            skipped += 1
            continue
        res = call(PUBLISH, {"id": p["id"], "input": [{"publicationId": online["id"]}]})
        errs = res["publishablePublish"].get("userErrors") or []
        if errs:
            print("  %-34s FAILED %s" % (p["handle"], errs[0]["message"]))
            failed += 1
        else:
            print("  %-34s published" % p["handle"])
            done += 1

    print()
    for c in collections:
        res = call(PUBLISH, {"id": c["id"], "input": [{"publicationId": online["id"]}]})
        errs = res["publishablePublish"].get("userErrors") or []
        print("  collection %-22s %s" % (c["handle"], errs[0]["message"] if errs else "published"))

    print("\npublished %d products, skipped %d, failed %d" % (done, skipped, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
