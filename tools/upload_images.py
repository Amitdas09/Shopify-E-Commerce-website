"""
Attach the generated product art to products over the Admin API.

Originally this was left as a manual drag-and-drop, on the grounds that fifteen
of them is faster than wiring up staged uploads. That was wrong once the count
is fifteen and each one has to be matched to the right product by hand — it is
exactly the kind of repetitive matching that goes quietly wrong.

Flow is Shopify's three-step media upload:
  1. stagedUploadsCreate  -> a signed S3-style target
  2. POST the file there  -> multipart, parameters exactly as returned
  3. productCreateMedia   -> attach the staged resource to the product

Alt text is set from the product title, which is what the theme falls back to
anyway, so the two agree.

Usage:
  SHOPIFY_STORE=... SHOPIFY_TOKEN=... python tools/upload_images.py
  add --force to re-upload for products that already have an image
"""

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "tools", "seed-images")

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
        raise SystemExit(json.dumps(payload["errors"], indent=2))
    return payload["data"]


PRODUCTS = """
query { products(first: 100) { edges { node { id handle title featuredImage { url } } } } }
"""

STAGE = """
mutation Stage($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { message }
  }
}
"""

ATTACH = """
mutation Attach($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media { alt status }
    mediaUserErrors { field message }
  }
}
"""


def multipart(target, filename, blob):
    """Hand-rolled multipart: the staged upload needs the returned parameters
    first and the file last, in that order, which most helpers will not promise."""
    boundary = "----purelane%s" % uuid.uuid4().hex
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body = b""

    for param in target["parameters"]:
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                 % (boundary, param["name"], param["value"])).encode()

    body += ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
             "Content-Type: %s\r\n\r\n" % (boundary, filename, ctype)).encode()
    body += blob
    body += ("\r\n--%s--\r\n" % boundary).encode()

    req = urllib.request.Request(
        target["url"], data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="upload even if the product already has an image")
    args = parser.parse_args()

    products = {e["node"]["handle"]: e["node"]
                for e in call(PRODUCTS)["products"]["edges"]}
    print("%d products in the store\n" % len(products))

    done = skipped = failed = 0

    for handle, product in sorted(products.items()):
        path = os.path.join(IMAGES, handle + ".png")

        if not os.path.exists(path):
            print("  %-34s no art on disk (expected for magic-eraser)" % handle)
            skipped += 1
            continue

        if product.get("featuredImage") and not args.force:
            print("  %-34s already has an image" % handle)
            skipped += 1
            continue

        blob = open(path, "rb").read()

        staged = call(STAGE, {"input": [{
            "filename": handle + ".png",
            "mimeType": "image/png",
            "resource": "IMAGE",
            "httpMethod": "POST",
            "fileSize": str(len(blob)),
        }]})

        errs = staged["stagedUploadsCreate"].get("userErrors") or []
        if errs:
            print("  %-34s stage failed: %s" % (handle, errs[0]["message"]))
            failed += 1
            continue

        target = staged["stagedUploadsCreate"]["stagedTargets"][0]

        try:
            multipart(target, handle + ".png", blob)
        except urllib.error.HTTPError as e:
            print("  %-34s upload failed: HTTP %s" % (handle, e.code))
            failed += 1
            continue

        res = call(ATTACH, {
            "productId": product["id"],
            "media": [{
                "originalSource": target["resourceUrl"],
                "alt": product["title"],
                "mediaContentType": "IMAGE",
            }],
        })

        merrs = res["productCreateMedia"].get("mediaUserErrors") or []
        if merrs:
            print("  %-34s attach failed: %s" % (handle, merrs[0]["message"]))
            failed += 1
        else:
            print("  %-34s uploaded  (%d KB)" % (handle, len(blob) // 1024))
            done += 1

    print("\nuploaded %d, skipped %d, failed %d" % (done, skipped, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
