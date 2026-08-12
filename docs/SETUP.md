# Setup, from nothing to a live homepage

Roughly 45 minutes end to end. Every account used here is free.

---

## 1. Partner account and development store

1. Sign up at <https://partners.shopify.com> — free, no card.
2. In the Partner dashboard: **Stores → Add store → Create development store**.
3. Store purpose: **Test and build a theme or app**.
4. Store name: anything, e.g. `purelane-dev`.
5. Under store settings set the currency to **INR** — the design prices in
   rupees, and every price on the page runs through the `money` filter, so the
   store's currency is what renders.

The store is created on the current default theme, which is Dawn.

## 2. You will not be on Dawn — this is expected

**Online Store → Themes** on a new store now reads **Horizon**, not Dawn.
Shopify changed the default theme, so "the one new stores start on" is no longer
Dawn. Horizon is a different architecture entirely and these sections do not
target it.

Do not fight it and do not delete Horizon. Step 4 clones Dawn from Shopify's own
repository and pushes it as a separate theme, which you then publish. That is
both simpler and a stricter reading of "clean install of Dawn" than pulling it
from the theme store.

Nothing else gets installed. The five sections rely on nothing a premium theme
provides.

## 3. Install the Shopify CLI

```bash
npm install -g @shopify/cli@latest
```

Verify with `shopify version`.

## 4. Pull Dawn, then add these sections

From inside this repo:

```bash
bash tools/install-into-dawn.sh ../purelane-store
cd ../purelane-store
```

That clones stock Dawn from Shopify's own repository, copies the 25 Purelane
files in, and swaps the homepage template — keeping Dawn's original at
`templates/index.dawn-original.json` so you can diff it.

Nothing overwrites a stock Dawn file. Every added file is prefixed `purelane-`,
and `templates/index.json` is the only replacement.

```bash
shopify theme dev --store your-store.myshopify.com
```

That opens a live preview on `http://127.0.0.1:9292` and hot-reloads on save.

## 5. Custom data

Create the metafield and metaobject definitions in
[metafields.md](metafields.md) **before** importing products. Definitions have
to exist first or the values have nowhere to land.

## 6. Products

1. **Products → Import**, upload `tools/seed-products.csv`.
2. That creates 16 products, including the three cases the brief asks for:
   - `washing-machine-cleaner` — inventory 0, policy *deny*, so it renders sold out
   - `magic-eraser` — deliberately has no image
   - `kitchen-degreaser-refill-pouch` — a 162-character title
3. Generate the product art and attach it:

```bash
python tools/make_product_images.py     # writes tools/seed-images/*.png
```

Each file is named for its product handle. Open a product, drag its PNG onto the
media area. Skip `magic-eraser` — its missing image is the point, and the theme
renders a branded placeholder that holds the same box.

> The images are redrawn from the prototype's own inline SVG bottles rather than
> sourced as stock photography. The bottles *are* the design; substituting
> photographs would change how the page looks.

## 7. Collections

**Products → Collections → Create collection**, twice, both automated:

| Title | Handle | Condition |
|---|---|---|
| Bestsellers | `bestsellers` | Product tag is equal to `bestsellers` |
| Combos | `combos` | Product tag is equal to `combos` |

The CSV already applies those tags, so both fill immediately.

## 8. Fill in the custom data

For each combo product, set `purelane.combo_items` to the products it contains:

| Combo | Items |
|---|---|
| Kitchen essentials | Kitchen cleaner, Dishwash gel, Tap cleaner |
| Laundry care bundle | Laundry detergent, Washing machine cleaner, Floor cleaner |
| Complete home bundle | Kitchen cleaner, Laundry detergent, Floor cleaner, Toilet cleaner, Liquid handwash |
| Bathroom deep clean | Toilet cleaner, Tap cleaner, Magic eraser |
| Hard water solution kit | Tap cleaner, Toilet cleaner |

Set `purelane.flag` to `Most popular` on Kitchen essentials, and `Best value`
plus `purelane.highlight` = true and `purelane.save_label` = `Biggest saving` on
Complete home bundle. That reproduces the prototype's two ribboned cards.

On the single products, set `purelane.badge` to `Best seller` on the tap and
kitchen cleaners and `Top rated` on the metal cleaner, and give each one a
`purelane.benefit` line — those are the captions under the bottles in a combo
tray.

Then create five or so `purelane_review` entries under **Content → Metaobjects**.

## 9. Wire the homepage

The supplied `templates/index.json` already places all six sections in order and
references the collections and products by handle. Open
**Online Store → Customize** and confirm:

- **Purelane backdrop** is present (it can sit anywhere in the order)
- **Purelane hero** slides point at real products
- **Purelane reviews** has your metaobject entries selected
- **Purelane combos** and **shop grid** point at the two collections
- **Purelane bundles** tiers point at the three combo products

## 10. Push

```bash
shopify theme push --unpublished --theme "Purelane"
```

Then publish it from **Online Store → Themes**, and set a store password under
**Online Store → Preferences** to share the preview.

---

## Checking the work

| What | How |
|---|---|
| Every width from 375px | DevTools responsive mode: 375, 390, 428, 768, 1024, 1200, 1440 |
| Theme editor survival | Add, duplicate, reorder and delete each section. Animations must keep working, and no section may break another. |
| Keyboard | Tab the whole page. Every control reachable, focus always visible, the combo rail and review rail both pannable. |
| Reduced motion | OS setting on. Nothing animates, the review rail becomes a normal scroller, the carousel stops advancing. |
| Sold out and no image | Confirm the two seed products render their states rather than breaking the grid. |
| Core Web Vitals | Lighthouse on the published URL, mobile preset, and PageSpeed Insights for field data. |
