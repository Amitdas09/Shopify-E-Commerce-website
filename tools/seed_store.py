"""
Seed a Purelane development store over the Admin GraphQL API.

What this does, in order:
  1. creates the seven purelane.* product metafield definitions
  2. creates the purelane_review metaobject definition
  3. creates the review entries
  4. creates the `bestsellers` and `combos` automated collections
  5. writes the metafield VALUES onto the products (combo contents, badges,
     benefit captions, ribbons, highlight flags)

What it deliberately does NOT do:
  * create the products — Shopify's own CSV importer does that natively and
    reliably. Import tools/seed-products.csv first.
  * upload images — 15 drag-and-drops in the admin is genuinely faster than
    staged uploads, and it is the one step where you want to see the result.

Step 5 is the reason this exists: setting those values by hand is around
twenty-five separate edits through the admin UI.

Setup:
  In your dev store: Settings -> Apps and sales channels -> Develop apps
  -> Create an app -> Configure Admin API scopes, tick:
        read_products, write_products,
        read_metaobjects, write_metaobjects,
        read_metaobject_definitions, write_metaobject_definitions
  -> Install app -> reveal the Admin API access token (starts shpat_)

Usage:
  export SHOPIFY_STORE=your-store.myshopify.com
  export SHOPIFY_TOKEN=shpat_xxxxx
  python tools/seed_store.py --check          # verify credentials only
  python tools/seed_store.py --step 1         # run one step
  python tools/seed_store.py                  # run all steps

Every step is safe to re-run: existing objects are reported and skipped rather
than duplicated.
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


# ----------------------------------------------------------------- transport

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
        detail = e.read().decode(errors="replace")[:400]
        sys.exit("HTTP %s from Shopify:\n%s" % (e.code, detail))
    except urllib.error.URLError as e:
        sys.exit("Could not reach %s: %s" % (STORE, e.reason))

    if "errors" in payload:
        sys.exit("GraphQL error:\n%s" % json.dumps(payload["errors"], indent=2))

    return payload["data"]


def user_errors(result, *path):
    node = result
    for key in path:
        node = node.get(key, {}) if isinstance(node, dict) else {}
    return node.get("userErrors", []) if isinstance(node, dict) else []


# ------------------------------------------------------------------ step 1

METAFIELDS = [
    ("Badge", "badge", "single_line_text_field",
     "Corner pill on a product card, e.g. Best seller."),
    ("Benefit", "benefit", "single_line_text_field",
     "One-line caption shown under this product inside a combo tray."),
    ("Combo items", "combo_items", "list.product_reference",
     "Products contained in this combo or bundle."),
    ("Flag", "flag", "single_line_text_field",
     "Corner ribbon on a combo card, e.g. Most popular."),
    ("Save label", "save_label", "single_line_text_field",
     "Overrides the computed You save X chip."),
    ("Highlight", "highlight", "boolean",
     "Gives the combo card the gold border and solid button."),
    ("Includes", "includes", "multi_line_text_field",
     "The Includes: sentence. Generated from combo items when empty."),
]

M_DEF = """
mutation Create($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition { id key }
    userErrors { field message code }
  }
}
"""


def step_metafields():
    print("\n1. Product metafield definitions")
    for name, key, mtype, description in METAFIELDS:
        data = call(M_DEF, {"definition": {
            "name": name,
            "namespace": "purelane",
            "key": key,
            "description": description,
            "type": mtype,
            "ownerType": "PRODUCT",
            "access": {"storefront": "PUBLIC_READ"},
        }})
        errs = user_errors(data, "metafieldDefinitionCreate")
        if errs:
            code = errs[0].get("code")
            if code == "TAKEN":
                print("   exists   purelane.%s" % key)
            else:
                print("   FAILED   purelane.%-12s %s" % (key, errs[0]["message"]))
        else:
            print("   created  purelane.%s" % key)


# ------------------------------------------------------------------ step 2

MO_DEF = """
mutation Create($definition: MetaobjectDefinitionCreateInput!) {
  metaobjectDefinitionCreate(definition: $definition) {
    metaobjectDefinition { id type }
    userErrors { field message code }
  }
}
"""

REVIEW_FIELDS = [
    ("Title", "title", "single_line_text_field", True),
    ("Body", "body", "multi_line_text_field", True),
    ("Author", "author", "single_line_text_field", False),
    ("Rating", "rating", "number_integer", False),
    ("Verified", "verified", "boolean", False),
    ("Product", "product", "product_reference", False),
    ("Context", "context", "single_line_text_field", False),
]


def step_metaobject_definition():
    print("\n2. Review metaobject definition")
    data = call(MO_DEF, {"definition": {
        "name": "Purelane review",
        "type": "purelane_review",
        "access": {"storefront": "PUBLIC_READ"},
        "capabilities": {"publishable": {"enabled": True}},
        "fieldDefinitions": [
            {"name": n, "key": k, "type": t, "required": r}
            for n, k, t, r in REVIEW_FIELDS
        ],
    }})
    errs = user_errors(data, "metaobjectDefinitionCreate")
    if errs:
        if errs[0].get("code") == "TAKEN":
            print("   exists   purelane_review")
        else:
            print("   FAILED   %s" % errs[0]["message"])
    else:
        print("   created  purelane_review with %d fields" % len(REVIEW_FIELDS))


# ------------------------------------------------------------------ step 3

MO_CREATE = """
mutation Create($metaobject: MetaobjectCreateInput!) {
  metaobjectCreate(metaobject: $metaobject) {
    metaobject { id handle }
    userErrors { field message code }
  }
}
"""

REVIEWS = [
    ("works-like-a-charm", "Works like a charm",
     "Finally an eco option that cleans as well as the chemical detergent I used for years, and it smells better.",
     "Anita", "Laundry detergent"),
    ("best-dishwash-ever", "Best dishwash ever",
     "Our old dishwash left my help with dry, cracked skin. That stopped completely after we switched.",
     "Priya", "Dishwash gel"),
    ("great-packaging", "Great product, great packaging",
     "Very soft on hands with a lovely fragrance, and it feels good to be using far less plastic.",
     "Sunita", "Liquid handwash"),
    ("dog-friendly", "Dog friendly",
     "We switched because chemical floor cleaners were setting off my dog's allergies. No reactions since.",
     "Rohit S.", "Floor cleaner"),
    ("sparkling-taps", "Sparkling taps again",
     "Hard water had ruined our bathroom fittings. Two sprays and the scale wipes straight off, no scrubbing.",
     "Verified buyer", "Tap cleaner"),
]


def step_reviews():
    print("\n3. Review entries")
    for handle, title, body, author, context in REVIEWS:
        data = call(MO_CREATE, {"metaobject": {
            "type": "purelane_review",
            "handle": handle,
            "capabilities": {"publishable": {"status": "ACTIVE"}},
            "fields": [
                {"key": "title", "value": title},
                {"key": "body", "value": body},
                {"key": "author", "value": author},
                {"key": "context", "value": context},
                {"key": "rating", "value": "5"},
                {"key": "verified", "value": "true"},
            ],
        }})
        errs = user_errors(data, "metaobjectCreate")
        if errs:
            if errs[0].get("code") == "TAKEN":
                print("   exists   %s" % handle)
            else:
                print("   FAILED   %-22s %s" % (handle, errs[0]["message"]))
        else:
            print("   created  %s" % handle)


# ------------------------------------------------------------------ step 4

COLLECTION_CREATE = """
mutation Create($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection { id handle }
    userErrors { field message }
  }
}
"""


def step_collections():
    print("\n4. Collections")
    for title, handle, tag in [("Bestsellers", "bestsellers", "bestsellers"),
                               ("Combos", "combos", "combos")]:
        data = call(COLLECTION_CREATE, {"input": {
            "title": title,
            "handle": handle,
            "ruleSet": {
                "appliedDisjunctively": False,
                "rules": [{"column": "TAG", "relation": "EQUALS", "condition": tag}],
            },
        }})
        errs = user_errors(data, "collectionCreate")
        if errs:
            print("   exists / failed  %-14s %s" % (handle, errs[0]["message"]))
        else:
            print("   created  %s (auto: tag = %s)" % (handle, tag))


# ------------------------------------------------------------------ step 5

PRODUCTS_QUERY = """
query { products(first: 100) { edges { node { id handle title } } } }
"""

METAFIELDS_SET = """
mutation Set($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { key }
    userErrors { field message }
  }
}
"""

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
    "kitchen-essentials-combo": ["kitchen-cleaner-foaming", "dishwash-gel",
                                 "tap-cleaner-limescale-remover"],
    "laundry-care-bundle": ["laundry-detergent", "washing-machine-cleaner", "floor-cleaner"],
    "complete-home-bundle": ["kitchen-cleaner-foaming", "laundry-detergent", "floor-cleaner",
                             "toilet-cleaner", "liquid-handwash"],
    "bathroom-deep-clean": ["toilet-cleaner", "tap-cleaner-limescale-remover", "magic-eraser"],
    "hard-water-solution-kit": ["tap-cleaner-limescale-remover", "toilet-cleaner"],
}

FLAGS = {
    "kitchen-essentials-combo": "Most popular",
    "complete-home-bundle": "Best value",
}

HIGHLIGHT = ["complete-home-bundle"]
SAVE_LABEL = {"complete-home-bundle": "Biggest saving"}

INCLUDES = {
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


def step_values():
    print("\n5. Metafield values on products")

    data = call(PRODUCTS_QUERY)
    by_handle = {e["node"]["handle"]: e["node"]["id"] for e in data["products"]["edges"]}
    print("   found %d products in the store" % len(by_handle))

    missing = [h for h in set(list(BENEFITS) + list(COMBO_ITEMS)) if h not in by_handle]
    if missing:
        print("   NOT IN STORE — import the CSV first: %s" % ", ".join(sorted(missing)))

    payload = []

    def add(handle, key, mtype, value):
        if handle not in by_handle:
            return
        payload.append({
            "ownerId": by_handle[handle],
            "namespace": "purelane",
            "key": key,
            "type": mtype,
            "value": value,
        })

    for handle, text in BADGES.items():
        add(handle, "badge", "single_line_text_field", text)
    for handle, text in BENEFITS.items():
        add(handle, "benefit", "single_line_text_field", text)
    for handle, text in FLAGS.items():
        add(handle, "flag", "single_line_text_field", text)
    for handle, text in SAVE_LABEL.items():
        add(handle, "save_label", "single_line_text_field", text)
    for handle, text in INCLUDES.items():
        add(handle, "includes", "multi_line_text_field", text)
    for handle in HIGHLIGHT:
        add(handle, "highlight", "boolean", "true")

    for combo, items in COMBO_ITEMS.items():
        gids = [by_handle[h] for h in items if h in by_handle]
        if gids:
            add(combo, "combo_items", "list.product_reference", json.dumps(gids))

    # metafieldsSet accepts 25 at a time
    for i in range(0, len(payload), 25):
        batch = payload[i:i + 25]
        result = call(METAFIELDS_SET, {"metafields": batch})
        errs = user_errors(result, "metafieldsSet")
        if errs:
            for e in errs:
                print("   FAILED   %s" % e["message"])
        else:
            print("   wrote    %d values" % len(batch))


# --------------------------------------------------------------------- main

SHOP_QUERY = "query { shop { name myshopifyDomain currencyCode } }"


def check():
    data = call(SHOP_QUERY)
    shop = data["shop"]
    print("connected to %s (%s), currency %s"
          % (shop["name"], shop["myshopifyDomain"], shop["currencyCode"]))
    if shop["currencyCode"] != "INR":
        print("note: the design prices in rupees. Settings -> Store details -> "
              "Store currency to switch, before you take screenshots.")


STEPS = {
    1: step_metafields,
    2: step_metaobject_definition,
    3: step_reviews,
    4: step_collections,
    5: step_values,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify credentials and exit")
    parser.add_argument("--step", type=int, choices=sorted(STEPS), help="run a single step")
    args = parser.parse_args()

    check()
    if args.check:
        return 0

    for number in ([args.step] if args.step else sorted(STEPS)):
        STEPS[number]()

    print("\nDone. Next: Online Store -> Customize, and point each section at "
          "the collections, products and reviews.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
