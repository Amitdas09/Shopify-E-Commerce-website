# Purelane — production Shopify sections

The `purelane-homepage.html` prototype, rebuilt as sections for stock Dawn.

The design is the spec and is reproduced as-is. The code is not: where the
original file was wrong for production — semantics, accessibility, performance,
theme-editor safety — it is fixed, and every fix is written up in
[docs/BUILD-NOTES.md](docs/BUILD-NOTES.md).

---

## The five sections

| # | Section | File | Prototype |
|---|---|---|---|
| 01 | Hero | `sections/purelane-hero.liquid` | `section.hero` |
| 02 | Shop / product grid | `sections/purelane-product-grid.liquid` | `#shop` |
| 03 | Best-selling combos | `sections/purelane-combos.liquid` | `#combos` |
| 04 | Bundles | `sections/purelane-bundles.liquid` | `#bundles` |
| 05 | Reviews rail | `sections/purelane-reviews.liquid` | `#reviews` |

Plus `sections/purelane-ambient.liquid` — the fixed mint backdrop with the
caustics and bubbles. It sits behind everything, so it belongs to no single
section and is added once per template. Every content section works whether or
not it is present.

## Shared code

Several sections render the same objects, so they render the same snippets.

```
snippets/
  purelane-assets.liquid          fonts + core CSS + reveal, rendered by every section
  purelane-product-card.liquid    the card in the shop grid
  purelane-product-image.liquid   responsive <img>, or a branded placeholder
  purelane-price.liquid           price / compare-at / computed saving
  purelane-rating.liquid          standard reviews.* metafields, with real SR text
  purelane-review-card.liquid     one quote in the marquee
  purelane-icon.liquid            the five icons, defined once instead of 40+ times
  purelane-water.liquid           caustic layers, ids namespaced per section
```

## Data

Nothing that reads as copy or catalogue is hardcoded. Prices, titles, images and
availability come from products; reviews come from a `purelane_review`
metaobject; the rest are section settings and blocks.

Definitions: [docs/metafields.md](docs/metafields.md).

## Getting it running

[docs/SETUP.md](docs/SETUP.md) — Partner account through to a published theme,
about 45 minutes, all free.

```bash
python tools/make_product_images.py     # product art, redrawn from the design
# tools/seed-products.csv               # 16 products incl. the three edge cases
```

## Reading the notes

- [docs/BUILD-NOTES.md](docs/BUILD-NOTES.md) — what I'd flag about the original,
  what changed and why, what I'd do with more time
- [docs/AI-WORKFLOW.md](docs/AI-WORKFLOW.md) — what I delegated, where it failed
  me, what I'd systematise
- [docs/metafields.md](docs/metafields.md) — every definition to create
- [docs/SETUP.md](docs/SETUP.md) — store setup and the QA checklist

## Verifying

```bash
python tools/verify.py
```

Parses every `{% schema %}` block as JSON, syntax-checks every JS asset, parses
the seed CSV, and recomputes the contrast ratios quoted in the build notes.
