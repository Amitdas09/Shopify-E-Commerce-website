# Metafield and metaobject definitions

Everything the sections read that Shopify has no native field for. Create these
before importing products, so the CSV and the theme line up on first load.

The guiding rule: if a native field exists, use it. Price, compare-at price,
title, image, availability and URL all come from the product object and are not
duplicated here. Ratings use Shopify's *standard* definitions rather than custom
ones, so any review app populates them without a theme change.

---

## 1. Product metafields

Settings → Custom data → Products → Add definition.

| Namespace and key | Type | Used by | What it is |
|---|---|---|---|
| `purelane.badge` | Single line text | shop grid | The corner pill on a card, e.g. `Best seller`, `Top rated`. Leave empty for no pill. |
| `purelane.benefit` | Single line text | combos | The one-line caption under a bottle in a combo tray, e.g. `Cuts grease instantly`. Falls back to the product title. |
| `purelane.combo_items` | Product reference (list) | combos, bundles | Which products a combo or bundle contains. Drives the tray artwork, the `3 products` count and the auto-written `Includes:` sentence. |
| `purelane.flag` | Single line text | combos | Corner ribbon on a combo card, e.g. `Most popular`, `Best value`. |
| `purelane.save_label` | Single line text | combos | Overrides the computed `You save ₹398` chip, for copy like `Biggest saving`. |
| `purelane.highlight` | True or false | combos | Gives the card the gold border and the solid primary button. |
| `purelane.includes` | Multi line text | combos | The `Includes: …` sentence. If left empty it is generated from `combo_items`, so a card is never half-empty. |

### Standard rating metafields

Do **not** create these by hand. In Settings → Custom data → Products, click
**Add definition → Use a standard definition** and pick:

- `reviews.rating` (type: Rating)
- `reviews.rating_count` (type: Integer)

`snippets/purelane-rating.liquid` reads exactly these. That means Judge.me,
Okendo, Loox, Yotpo and Shopify's own review app all populate the star rating
with no code change, and the rating block hides itself on any product with no
reviews rather than printing `★ 0 · 0 reviews`.

---

## 2. Review metaobject

Settings → Custom data → Metaobjects → Add definition.

**Name:** `Purelane review`  **Type:** `purelane_review`

| Field name | Key | Type | Notes |
|---|---|---|---|
| Title | `title` | Single line text | The bold headline, e.g. `Works like a charm`. |
| Body | `body` | Multi line text | The quote itself. |
| Author | `author` | Single line text | Displayed name. Defaults to `Verified buyer` if empty. |
| Rating | `rating` | Integer | 1–5. Anything outside that range renders as 5. |
| Verified | `verified` | True or false | Shows the tick before the name. |
| Product | `product` | Product reference | Optional. What the review is about. |
| Context | `context` | Single line text | Overrides the trailing `· Laundry detergent`. Falls back to the linked product's title. |

Under **Options**, enable *Storefronts* so the entries are readable by the
theme. The reviews section then lists them in a picker.

### Why a metaobject and not section blocks

Blocks would have worked and would have been less setup. Two reasons against:

1. Reviews outlive the section. The same quote gets used on a product page, a
   landing page and an email. Blocks bind it to one section on one template.
2. A review that names a product should *link* to it. Blocks can hold a product
   picker, but then the relationship is per-placement rather than per-review,
   and it has to be re-picked every time the quote is reused.

---

## 3. Collections

Two collections drive the homepage. Both can be automated on tag.

| Handle | Type | Rule |
|---|---|---|
| `bestsellers` | Automated | Product tag is equal to `bestsellers` |
| `combos` | Automated | Product tag is equal to `combos` |

The seed CSV already carries those tags, so both collections fill themselves on
import.
