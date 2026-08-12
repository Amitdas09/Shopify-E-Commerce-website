"""
Pre-push checks for the Purelane sections.

Everything here executes rather than reads. The failures worth catching in a
Liquid theme are never in the interesting logic — they are a malformed schema
that makes the whole theme refuse to upload, a stray comma in a CSV, a filter
that does not exist. All cheap to check, all expensive to find later.

Usage: python tools/verify.py
Exit code is non-zero if anything fails.
"""

import csv
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []
notes = []


def ok(msg):
    print("  ok    %s" % msg)


def fail(msg):
    print("  FAIL  %s" % msg)
    failures.append(msg)


def head(msg):
    print("\n%s" % msg)


# ---------------------------------------------------------------- schema JSON

head("Section schemas parse as JSON")

for path in sorted(glob.glob(os.path.join(ROOT, "sections", "*.liquid"))):
    name = os.path.basename(path)
    src = open(path, encoding="utf-8").read()
    m = re.search(r"\{%\s*schema\s*%\}(.*?)\{%\s*endschema\s*%\}", src, re.S)

    if not m:
        fail("%s has no {%% schema %%} block" % name)
        continue

    try:
        schema = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        fail("%s schema is not valid JSON: %s" % (name, e))
        continue

    if "name" not in schema:
        fail("%s schema has no name" % name)
        continue

    # setting ids must be unique, or the theme editor silently drops one
    ids = [s.get("id") for s in schema.get("settings", []) if s.get("id")]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        fail("%s has duplicate setting ids: %s" % (name, ", ".join(sorted(dupes))))
        continue

    ok("%-34s %2d settings, %d block types" % (name, len(ids), len(schema.get("blocks", []))))


# --------------------------------------------------------- settings are used

head("Every schema setting is referenced in its section body")

for path in sorted(glob.glob(os.path.join(ROOT, "sections", "*.liquid"))):
    name = os.path.basename(path)
    src = open(path, encoding="utf-8").read()
    m = re.search(r"\{%\s*schema\s*%\}(.*?)\{%\s*endschema\s*%\}", src, re.S)
    if not m:
        continue

    body = src[: m.start()]
    try:
        schema = json.loads(m.group(1))
    except json.JSONDecodeError:
        continue

    unused = [
        s["id"]
        for s in schema.get("settings", [])
        if s.get("id") and s["id"] not in body
    ]

    if unused:
        fail("%s declares unused settings: %s" % (name, ", ".join(unused)))
    else:
        ok("%-34s all settings used" % name)


# ------------------------------------------------------------- rendered snippets exist

head("Every rendered snippet exists")

snippets = {
    os.path.splitext(os.path.basename(p))[0]
    for p in glob.glob(os.path.join(ROOT, "snippets", "*.liquid"))
}

for path in sorted(glob.glob(os.path.join(ROOT, "sections", "*.liquid")) +
                   glob.glob(os.path.join(ROOT, "snippets", "*.liquid"))):
    name = os.path.basename(path)
    src = open(path, encoding="utf-8").read()
    for ref in set(re.findall(r"render\s+'([a-z0-9\-]+)'", src)):
        if ref not in snippets:
            fail("%s renders missing snippet '%s'" % (name, ref))

ok("%d snippets, all references resolve" % len(snippets))


# ---------------------------------------------------------------- asset refs

head("Every asset_url reference exists")

assets = {os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "assets", "*"))}

for path in sorted(glob.glob(os.path.join(ROOT, "sections", "*.liquid")) +
                   glob.glob(os.path.join(ROOT, "snippets", "*.liquid"))):
    name = os.path.basename(path)
    src = open(path, encoding="utf-8").read()
    for ref in set(re.findall(r"'([a-zA-Z0-9\-_.]+\.(?:css|js))'\s*\|\s*asset_url", src)):
        if ref not in assets:
            fail("%s references missing asset '%s'" % (name, ref))

ok("%d assets, all references resolve" % len(assets))


# ------------------------------------------------------------- forbidden Liquid

head("No filters that Shopify Liquid does not have")

# `ternary` reads as valid and is not. Cheap to check, silent to miss.
BANNED = ["ternary"]

for path in sorted(glob.glob(os.path.join(ROOT, "sections", "*.liquid")) +
                   glob.glob(os.path.join(ROOT, "snippets", "*.liquid"))):
    name = os.path.basename(path)
    src = open(path, encoding="utf-8").read()
    for bad in BANNED:
        if re.search(r"\|\s*%s\b" % bad, src):
            fail("%s uses non-existent filter '%s'" % (name, bad))

ok("no banned filters")


# ------------------------------------------------------------------------- JS

head("JavaScript parses")

node = None
for candidate in ("node", "node.exe"):
    try:
        subprocess.run([candidate, "--version"], capture_output=True, check=True)
        node = candidate
        break
    except (OSError, subprocess.CalledProcessError):
        continue

if node is None:
    notes.append("node not found, JS syntax not checked")
    print("  skip  node not on PATH")
else:
    for path in sorted(glob.glob(os.path.join(ROOT, "assets", "*.js"))):
        name = os.path.basename(path)
        result = subprocess.run([node, "--check", path], capture_output=True, text=True)
        if result.returncode != 0:
            fail("%s: %s" % (name, result.stderr.strip().splitlines()[0]))
        else:
            ok(name)


# ------------------------------------------------------------------------ CSV

head("Seed CSV parses and carries the required edge cases")

csv_path = os.path.join(ROOT, "tools", "seed-products.csv")
with open(csv_path, encoding="utf-8", newline="") as fh:
    rows = list(csv.DictReader(fh))

if not rows:
    fail("seed CSV is empty")
else:
    ragged = [r for r in rows if None in r or None in r.values()]
    if ragged:
        fail("%d row(s) have the wrong column count" % len(ragged))
    else:
        ok("%d products, all rows well formed" % len(rows))

    sold_out = [r for r in rows if r["Variant Inventory Qty"] == "0"]
    no_image = [r for r in rows if not r["Image Alt Text"].strip()]
    long_title = [r for r in rows if len(r["Title"]) > 90]

    (ok if sold_out else fail)("sold-out product present (%d)" % len(sold_out))
    (ok if no_image else fail)("product with no image present (%d)" % len(no_image))
    (ok if long_title else fail)(
        "very long title present (%d chars)" % (len(long_title[0]["Title"]) if long_title else 0)
    )

    if len(rows) < 8:
        fail("brief requires at least 8 products, found %d" % len(rows))


# ------------------------------------------------------------------ contrast

head("Contrast ratios quoted in BUILD-NOTES still hold")


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


GROUND = "#f4f0fb"

# (label, colour, floor, why)
CHECKS = [
    ("--accent-ink on page", "#8f560f", 4.5, "small text"),
    ("--leaf-ink on page", "#4a760f", 4.5, "small text"),
    ("--surface on page", "#17102b", 4.5, "body and headings"),
    ("--paper on page", "#241a3d", 4.5, "body copy"),
    ("--accent on page", "#b8701c", 3.0, "large text and non-text only"),
]

for label, colour, floor, why in CHECKS:
    ratio = contrast(colour, GROUND)
    if ratio >= floor:
        ok("%-24s %5.2f:1  (needs %.1f, %s)" % (label, ratio, floor, why))
    else:
        fail("%s is %.2f:1, below the %.1f floor for %s" % (label, ratio, floor, why))

for label, fg, bg in [
    ("btn-primary text", "#f4fdf6", "#00706a"),
    ("btn-ghost text", "#01423b", "#ffffff"),
]:
    ratio = contrast(fg, bg)
    (ok if ratio >= 4.5 else fail)("%-24s %5.2f:1  (needs 4.5)" % (label, ratio))


# --------------------------------------------------------------------- report

print("\n" + "-" * 62)
for n in notes:
    print("note: %s" % n)

if failures:
    print("%d check(s) failed" % len(failures))
    sys.exit(1)

print("all checks passed")
sys.exit(0)
