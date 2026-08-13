"""
Swap the product photos for the artwork extracted from the prototype.

upload_images.py --force attaches a second image rather than replacing the
first, which leaves every product with two near-identical bottles and makes the
featured image a coin toss. This deletes the existing media, waits for Shopify
to release the handle, then uploads the new file under the same name.

Run tools/extract_product_art.py first.

Usage:
  SHOPIFY_STORE=... SHOPIFY_TOKEN=... python tools/replace_product_art.py
"""

import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(HERE, "seed-images")
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
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s\n%s" % (e.code, e.read().decode(errors="replace")[:400]))
    if "errors" in payload:
        sys.exit(json.dumps(payload["errors"], indent=2))
    return payload["data"]


PRODUCT = """
query($handle: String!) {
  productByHandle(handle: $handle) {
    id title
    media(first: 20) { nodes { id ... on MediaImage { image { url } } } }
  }
}
"""

DELETE_MEDIA = """
mutation($productId: ID!, $mediaIds: [ID!]!) {
  productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
    deletedMediaIds
    mediaUserErrors { field message }
  }
}
"""

STAGE = """
mutation($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""

CREATE_MEDIA = """
mutation($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media { id status }
    mediaUserErrors { field message }
  }
}
"""


def post_multipart(url, fields, filename, blob, content_type):
    boundary = "----purelane" + uuid.uuid4().hex
    parts = []
    for name, value in fields:
        parts.append(
            ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
             % (boundary, name, value)).encode()
        )
    parts.append(
        ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
         "Content-Type: %s\r\n\r\n" % (boundary, filename, content_type)).encode()
    )
    parts.append(blob)
    parts.append(("\r\n--%s--\r\n" % boundary).encode())
    body = b"".join(parts)

    # The staged target is Google Cloud Storage behind Cloudflare, and it hands
    # back a 502 or 525 often enough over a domestic connection that a single
    # attempt is not safe here: the product's old media is already deleted by
    # this point, so giving up would leave it with no image at all.
    last = None
    for attempt in range(5):
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def upload_one(product, path, name, alt):
    """Stage, POST and attach one file. Returns the media user errors, if any."""
    blob = open(path, "rb").read()
    ctype = mimetypes.guess_type(name)[0] or "image/png"

    staged = call(STAGE, {"input": [{
        "filename": name,
        "mimeType": ctype,
        "resource": "IMAGE",
        "httpMethod": "POST",
        "fileSize": str(len(blob)),
    }]})
    errs = staged["stagedUploadsCreate"]["userErrors"]
    if errs:
        return errs

    target = staged["stagedUploadsCreate"]["stagedTargets"][0]
    post_multipart(
        target["url"],
        [(p["name"], p["value"]) for p in target["parameters"]],
        name, blob, ctype,
    )

    created = call(CREATE_MEDIA, {
        "productId": product["id"],
        "media": [{
            "originalSource": target["resourceUrl"],
            "mediaContentType": "IMAGE",
            "alt": alt,
        }],
    })
    return created["productCreateMedia"]["mediaUserErrors"]


def main():
    # Media order is the contract the theme reads: image 1 is the flat
    # silhouette that most sections use, image 2 the labelled bottle the shop
    # cards use. They are uploaded in that order, one product at a time, and
    # productCreateMedia appends — so the order here is the order on the
    # product. See snippets/purelane-product-image.liquid.
    flat_dir = os.path.join(IMAGES, "flat")
    label_dir = os.path.join(IMAGES, "label")
    if not os.path.isdir(label_dir):
        sys.exit("Run tools/extract_product_art.py and tools/make_labelled_art.py first.")

    handles = sorted({
        os.path.splitext(f)[0]
        for d in (flat_dir, label_dir) if os.path.isdir(d)
        for f in os.listdir(d) if f.endswith(".png")
    })

    done = failed = 0

    for handle in handles:
        product = call(PRODUCT, {"handle": handle}).get("productByHandle")
        if not product:
            print("  !  %-32s no such product" % handle)
            failed += 1
            continue

        old = [m["id"] for m in product["media"]["nodes"]]
        if old:
            result = call(DELETE_MEDIA, {"productId": product["id"], "mediaIds": old})
            errs = result["productDeleteMedia"]["mediaUserErrors"]
            if errs:
                print("  !  %-32s delete: %s" % (handle, errs))
                failed += 1
                continue
            # Shopify frees the filename asynchronously; uploading the same name
            # immediately gets it silently suffixed _1.
            time.sleep(1.5)

        plan = []
        flat = os.path.join(flat_dir, handle + ".png")
        label = os.path.join(label_dir, handle + ".png")
        if os.path.exists(flat):
            plan.append((flat, handle + ".png", product["title"]))
        if os.path.exists(label):
            # Distinct filename, or the second upload collides with the first
            # and Shopify suffixes it anyway.
            plan.append((label, handle + "-label.png",
                         product["title"] + " — label detail"))

        bad = None
        for path, name, alt in plan:
            errs = upload_one(product, path, name, alt)
            if errs:
                bad = errs
                break
            # Attachments land in call order, but only if they are sequential.
            time.sleep(0.6)

        if bad:
            print("  !  %-32s %s" % (handle, bad))
            failed += 1
            continue

        print("  ok %-32s %s" % (handle, " + ".join(
            os.path.basename(os.path.dirname(p)) for p, _, _ in plan)))
        done += 1

    print("\n%d replaced, %d failed" % (done, failed))


if __name__ == "__main__":
    main()
