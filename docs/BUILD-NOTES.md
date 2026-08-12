# Build notes

The design is reproduced as-is. Everything below is a change to the *code*
behind it, not to how it looks — with three deliberate exceptions, all colour,
all listed under Accessibility, all of which move a value by a few percent to
clear a contrast floor.

---

## What I'd flag about the original file

### The stylesheet is two stylesheets

`purelane-homepage.html` ships two `<style>` blocks. The second, labelled
*VERSION 2 — BRAND COLOURS (light)*, overrides about ninety declarations from
the first, including every colour token. The dark palette in block one never
reaches the screen; the page is the pale mint one.

That matters because reading the file top-down gives you the wrong design. The
resolved values are inlined once in `assets/purelane-core.css`, so what you read
is what paints.

### Duplicate SVG ids, and one layer that was never drawing itself

`.wl-a` and `.wl-b` each carry a `<defs>` block. They are byte-identical — I
diffed them — and both define `id="cg"`, `id="wf"` and `id="wf2"`. Duplicate ids
are invalid HTML, and `url(#cg)` inside `.wl-b` resolves to the *first* match in
the document, so the second caustic layer was silently painting with the first
layer's gradient.

`snippets/purelane-water.liquid` keeps one copy, references it deliberately, and
namespaces every remaining id with the section id so two backdrops cannot
collide.

### The product art was CSS, not content

Fourteen bottles were base64 SVG in CSS custom properties, painted as
`background-image`. Three consequences:

- **LCP.** A `background-image` is invisible to the browser's preload scanner.
  The hero visual could not be discovered early no matter what else was done.
- **Merchant-editable.** Adding a product meant adding a CSS variable.
- **CLS.** No intrinsic dimensions, so cards resized as art resolved.

Now `snippets/purelane-product-image.liquid` renders a real `<img>` with a seven-step
`srcset`, explicit dimensions, `loading="lazy"` everywhere except the first hero
bottle, which gets `fetchpriority="high"`.

### The JavaScript could not survive the theme editor

One IIFE, run once on `DOMContentLoaded`, reaching for `#hstage`, `#hdots`,
`#rot`, `#heroProd`, `#scenes` and `#water` by id. In a real theme:

- two hero sections means duplicate ids, and the second is driven by the first's handler
- adding or reordering a section re-renders it, and the listeners point at detached nodes
- deleting a section leaves `setInterval` running forever

The carousel is now a custom element, which upgrades itself whenever its markup
enters the DOM — including on `shopify:section:load` — and clears its timer in
`disconnectedCallback`. Reveal, marquee and backdrop all listen for the section
lifecycle events and rescan.

### The scroll handler forced layout on every frame

```js
for each zone:
  var top = 0, el = zone;
  while (el) { top += el.offsetTop; el = el.offsetParent; }
```

`offsetTop` forces synchronous layout. This ran once per ancestor, per zone, per
scroll frame, for thirteen zones. It is the single most expensive thing in the
original file after the blend modes.

Replaced with an `IntersectionObserver` banded across the middle of the
viewport. The browser already knows what is on screen.

### A script failure would have blanked the page

`.rv { opacity: 0 }` was unconditional, and only JavaScript ever removed it. A
404 on the script, a CSP block, a thrown error — any of them and the homepage
renders empty. The hidden state now sits behind `.purelane-js`, a class the
script itself adds, so the failure mode is "no animation" instead of "no page".

The reveal also only ever queried `.rv` once, so anything a merchant added later
stayed at `opacity: 0` permanently — in the theme editor that reads as a section
that did not save.

### The reduced-motion block broke the reviews rail

```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: .01ms !important; animation-iteration-count: 1 !important }
}
```

For a marquee, "finish in 0.01ms" means *complete* — the track jumps to
`translate3d(-50%, 0, 0)` and parks there, leaving the right half of the rail
empty. It needs `animation: none`, not a faster animation. With motion reduced
the rail is now a normal horizontal scroller.

### The hero art is not the same art as the cards

This one only showed up once the sections were rendered and looked at.

The prototype uses two different bottle drawings for the same products.
`#shop` and `#combos` use `p-kitchen`, `p-tap`, `p-dish` and friends, at an
aspect ratio around **0.64**. The hero uses `p-kbtl`, `p-tbtl` and `p-mbtl` —
the same bottles redrawn much taller and narrower, around **0.32**.

The hero stage geometry depends on that. It sizes each bottle by height
(`.hs1 .a { height: 100% }`) and lets width fall out of the artwork. Three
bottles at 0.32 fit a 560px stage. Three bottles at 0.64 are about twice the
stage width and spill across the headline.

Shopify gives a product one featured image. So the first normally-proportioned
photo a merchant uploads breaks the hero. The stage now carries a width ceiling
per position and leans on `object-fit: contain` with
`object-position: center bottom`, which holds the composition and the baseline
at any ratio.

### Duplicated base CSS silently beat the section CSS

Every section requests `purelane-core.css` so it can stand alone. That means
the browser sees the base rules once per section on the page — and the *last*
copy sits after the first section's own stylesheet.

`.purelane .glass-2 { position: relative }` and
`.purelane-hero .badges { position: absolute }` have identical specificity, so
source order decided it, and the shop grid's copy of core.css — five sections
further down the document — won. The hero badge rail dropped out of position
entirely.

Both files now declare `@layer purelane-base, purelane-section;` and put their
rules in the matching layer. Layer order is set by the first declaration and is
immune to how many times either file is emitted, or in what order.

This is the class of bug that only appears once more than one section is on the
page, which is exactly what a prototype never tests.

---

## What I changed, and why

### Accessibility

| Issue | Fix |
|---|---|
| Auto-advancing carousel and infinite marquee paused on `:hover` / `:focus-within` only — neither exists on touch. | Explicit pause/play buttons on both. WCAG 2.2.2. The marquee remembers the choice for the session. |
| Inactive carousel slides sat at `opacity: 0` but stayed in the accessibility tree, so all three price flags were announced at once. | `visibility: hidden`, transitioned so the fade is unchanged. |
| `★★★★★` as literal glyphs — announced as "black star" five times. | Stars are `aria-hidden`; a real sentence sits beside them: *"Rated 4.8 out of 5 from 237 reviews."* |
| The five reviews were pasted twice in the source to make the loop seamless, so every quote was announced twice. | Second pass is generated and `aria-hidden`. |
| `.comborail` and `.revrail` scroll horizontally but were unreachable without a mouse. | `tabindex="0"`, `role="region"`, an accessible name, and a focus ring. |
| `#shop` went `h2` → `h4`. | Card heading is `h3` and configurable per caller. |
| Cards were entirely inert: no links, and "Add to cart" was a bare `<button>` with no form. | Title is a real link with a full-card hit area; the button is a real `/cart/add` form that works with JavaScript off. |
| Sold-out products had no state. | Disabled control reading *Sold out*, plus a pill. |
| `--accent` `#b8701c` on the pale ground is **3.48:1** — under the 4.5:1 floor for small text, and it was carrying 9px uppercase labels. | Added `--accent-ink` `#8f560f` (**5.33:1**) for text. `--accent` is unchanged for borders, rings and fills. Same for `--leaf` `#4f7d10` (4.38:1) → `--leaf-ink` `#4a760f` (4.81:1). |
| — | `.tier .price` deliberately keeps `--accent`: at 27px/700 it is WCAG "large text", where the floor is 3:1 and 3.48 clears it. Left exactly as designed. |

Ratios computed against `#f4f0fb` and the `#f7f3fc` glass average, sRGB relative
luminance.

### Performance

- Icons were inlined 40+ times, about 9KB of duplicated markup. One snippet now.
- Hero headline is not wrapped in a reveal. It is the LCP element on most
  viewports and the prototype would have started it at `opacity: 0` with a 7px blur.
- Anything already inside the viewport on first paint is marked revealed without
  animating, rather than transitioning in.
- Fonts load `media="print"` / `onload="this.media='all'"` so they never block
  the first render, with a `<noscript>` fallback.
- The carousel and the backdrop only run while on screen.
- Four full-viewport layers using `mix-blend-mode` with an SVG `feTurbulence`
  filter are the most expensive thing on the page. The second caustic layer and
  the bubbles come off below 760px, as in the original, and the whole water
  effect is a checkbox a merchant can trade for rendering time.

### Merchant control

Nothing that reads as copy or catalogue is hardcoded. Headings, kickers,
sub-copy, button labels and links, fine print, the swipe cue, the rail note,
anchor ids, padding, column count and per-slide autoplay timing are all
settings. Promise badges and bundle tiers are blocks.

Prices are the important one. The prototype had ₹200/₹299/₹499/₹799 typed into
the markup in eleven places. Every one now derives from a product:

- the hero price flag reads a real product — for a multi-pack slide, point it at
  the bundle product that actually sells it
- combo savings are `compare_at_price − price`, formatted with `money`
- the bundle tier's *"Flat ₹166 per product"* is computed from the real price
  divided by the tier quantity, so it cannot go stale

### Reuse

`purelane-product-card` is shared by the shop grid and available to anything
else that renders a product. `purelane-product-image`, `purelane-price`,
`purelane-rating` and `purelane-icon` are used by every section. Combos and
bundles both read the same `purelane.combo_items` metafield, so a bundle's
contents are configured once regardless of which section draws it.

### Theme editor

Each section renders standalone and assumes nothing about its neighbours. The
backdrop is its own section rather than markup welded into `theme.liquid`, so it
can be added, removed or reordered like anything else — and every content
section still works when it is absent. Sections declare their depth with
`data-purelane-scene`; the backdrop discovers them, and re-discovers them on
`shopify:section:load` and `:unload`.

---

## Seeing it before there is a store

`tools/preview.py` renders the real section files to a static page with the
Shopify objects and filters shimmed and the seed catalogue loaded.
`tools/shoot.py` then screenshots it at 375 through 1440 and reports any
JavaScript error.

It is a preview, not an emulator — Shopify's renderer is the authority. But
three of the findings above came out of it and out of nothing else: the hero art
ratio, the cascade-layer collision, and `limit` being unusable as a variable
name because it collides with the `for` tag's keyword argument. All three read
as correct code. None of them survive being looked at.

Two divergences to know about when reading its output:

- python-liquid treats `nil != blank` as **true**; Shopify treats nil as blank.
  Object tests are therefore written as truthiness (`{% if img %}`), which means
  the same thing in both and is the right test for a drop anyway.
- A missing metafield returns Undefined rather than nil, so the preview supplies
  an empty string instead. Without that it renders empty badge pills the real
  store would never show.

---

## What I'd do with more time

1. **Self-host the fonts.** Two woff2 subsets in `assets/` removes a third-party
   connection from the critical path. It is the largest remaining LCP win.
2. **Real field data.** Everything above is reasoned from the code and from lab
   runs. I would want a week of CrUX before claiming a Core Web Vitals number.
3. **Cart drawer integration.** The add-to-cart form is a real form and works
   unenhanced. Wiring it to Dawn's `cart-notification` / `cart-drawer` would
   remove the page reload.
4. **A bundle builder.** "Build this box" currently links to the bundle product.
   The design implies a picker that pre-fills a tier and lets you swap items —
   that is a cart-transform or a bundles app, and a real scoping conversation.
5. **The remaining eight sections.** Ingredients, how-it-works, proof, range,
   why-bundles, categories, trust bar and signup. The card, price, rating, image
   and icon snippets already cover most of what they need.
6. **Visual regression tests.** Playwright screenshots at 375/768/1200 against
   the prototype, run in CI, so "pixel-accurate" stays true after the next edit.
7. **A per-section CSS budget.** Right now each section ships its own file. At
   six sections that is six requests; I would want to measure whether inlining
   the critical slice beats the caching.
