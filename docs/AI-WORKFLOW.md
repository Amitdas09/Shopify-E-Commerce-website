# AI workflow notes

## What I delegated

**Reading the file properly.** 151KB, 1,716 lines, with 22KB of base64 and 22KB
of SVG path data in single lines. The first useful thing an agent did was
mechanical: list every `<section>` and its id, find where each `<style>` block
started and ended, and pull the longest lines out of the way so the actual CSS
was readable. That reframed the task — it surfaced immediately that there were
*two* stylesheets and that the second one repainted the whole design, which is
the fact the entire build depends on.

**Structural diffing.** Two findings came from asking for a comparison rather
than a reading: that `wl-a` and `wl-b` carry byte-identical `<defs>` blocks with
colliding ids, and that the resolved V1+V2 cascade collapses to one set of
values. Both are the kind of thing you skim past by eye in a 1,700-line file and
that a `diff` answers in a second.

**Mechanical transforms.** The water layers were extracted from the prototype by
script, not retyped — deduplicate the `<defs>`, namespace six ids, add
`aria-hidden`, write the snippet. Retyping 22KB of path data by hand is how you
introduce a bug that nobody finds for a month.

**Generating the product art.** The design's bottles are SVG rounded rectangles
in per-product shades. A script redraws that geometry as raster at 1600px so it
can be uploaded as real product images. Faster than sourcing photography and
strictly more accurate, because the bottles *are* the design.

**Arithmetic I would otherwise have asserted.** Every contrast ratio in
BUILD-NOTES is computed, not estimated. That is what turned "the accent looks a
bit light" into "3.48:1, and here is a replacement at 5.33:1 that only applies
where the colour carries text".

## Where it failed me

**It wanted to build the wrong thing.** The first instruction I gave was
essentially "make this look amazing, use Framer Motion and real photos". A model
that optimises for agreeableness builds that. The brief says twice that a
redesign is an automatic no, and Framer Motion cannot run in a Liquid theme at
all. The most valuable thing in the session was the agent stopping to say the
request and the brief were in direct conflict, before writing a line. I now
treat "restate the constraints back to me before you start" as a required first
step, not a nicety.

**Confident wrong Liquid.** It reached for a `ternary` filter, which Shopify
Liquid does not have, and wrote `image_tag` with a `style:` argument mangled
through `replace`. Both looked plausible. Both would have failed at theme upload
with an unhelpful error. Liquid is exactly the shape of language models get
wrong: enough like Django and Jinja to be fluent, different enough to be broken.

**Metaobject field access.** It wrote `review.title` throughout, which renders
correctly and is still wrong — bare access returns a metafield drop, which is
never `blank`, so every `| default:` fallback silently never fires. It works
until a field is empty, and then it does not. Caught by reasoning about the
types, not by looking at the output.

**Unquoted CSV.** The seed row with the deliberately long title contained a
comma and was not quoted, so it parsed as 22 columns instead of 21. Caught in
two seconds by parsing the file; would have been a confusing failed import.

**A fix that made things worse, confidently.** Core CSS is emitted once per
section so a section can stand alone, so the page carries N copies, and the last
copy sits after the first section's own stylesheet. Two rules of equal
specificity — `.purelane .glass-2` and `.purelane-hero .badges`, both (0,2,0) —
resolved the wrong way and dropped the hero badge rail out of position. Wrapping
everything in `@layer` fixed that collision and quietly created a worse one:
unlayered CSS beats layered CSS at *any* specificity, so every collision with
Dawn's own rules started resolving Dawn's way. Plain `h2 { font-weight: 400 }`
outranked `.purelane .d2 { font-weight: 800 }` and every section heading
rendered thin. It took a screenshot diff to see it and a second look at the
cascade to understand why. The real fix was ordering — emit core once from
`<head>` after Dawn's `base.css` — which is less clever and cannot rebound.

**Reading the prototype's intent, not just its bytes.** Its shop shelf holds
eight cards drawn two different ways: four flat silhouettes, four fully drawn
labelled bottles. I read that as one art set, rasterised the flat ones
faithfully, and shipped eight placeholder cards. Then I over-corrected and made
everything labelled, flattening a distinction the design uses deliberately —
flat wherever a product is one of a group, labelled where it is the subject. A
model is good at "what does this file contain" and bad at "which half of this
did the designer mean". Both passes were confidently wrong in opposite
directions.

**Trusting my own earlier conclusion.** I called a null `onlineStoreUrl` a red
herring, explained by the storefront password. It was not — the products
genuinely were not on the Online Store publication. That wrong call sat in my
notes for several rounds and shaped everything I looked at next. Cached
conclusions are more dangerous than cached pages.

The pattern in all of these: the failures are never in the interesting logic.
They are in the boring interface between systems — a filter name, a drop's type,
a comma, a cascade rule, an assumption I made two hours earlier. Everything I
actually verify is at those seams.

## What the platform got wrong, and how I found it

Worth separating from the AI failures, because these were the expensive ones and
none of them announce themselves.

**Section-group and template JSON silently lose new settings.** Push a section's
Liquid and its group JSON together and Shopify validates the JSON against the
schema it already holds — so any setting the live schema does not yet know is
dropped on write, with no error. The footer's link columns rendered a heading
over nothing for exactly this reason. Push the Liquid first, then the JSON.

**`metaobject_list` does not bind from a JSON template.** Five correct GIDs in
`templates/index.json`, five storefront-readable entries, and
`section.settings.reviews` still resolved to an empty drop that reports `size 0`
and iterates zero times. `shop.metaobjects.purelane_review.values` returned all
five from the same page. The setting appears to bind only when saved through the
theme editor. The section now treats an empty picker as "show every published
entry", which is both a working homepage and better merchant behaviour.

**The CSV importer drops the inventory tracker column.** Every variant imported
untracked, which makes the seeded quantities decorative — Shopify neither
decrements them nor blocks a sale. Silent. Found by reading the store back
rather than trusting the import summary.

**The storefront caches the homepage for minutes after a push.** I debugged a
stale page more than once, including one round where I concluded a data problem
was a Liquid problem. Every storefront check in these tools now sends
`Cache-Control: no-cache`.

**Admin truth and storefront truth are different truths.** The longest chase in
the build: Admin reported `availableForSale: true` and
`sellableOnlineQuantity: 142` while Liquid reported the variant unavailable with
an empty quantity, and every product showed Sold out. Neither number is wrong —
Admin has no buyer context and the storefront does. It resolved to two settings
outside the theme entirely: the default location was not fulfilling online
orders, and the shop shipped only to `["US"]` while the storefront resolved
`countryCode: IN`. The lesson I would carry forward is to instrument the actual
renderer early — one temporary Liquid comment printing `product.available` and
`variant.inventory_quantity` answered in one push what six API queries could
not.

## What I'd systematise for twenty more of these

**Instrument the renderer, not the API.** The fastest debugging tool in this
build was a one-line HTML comment printing what Liquid could actually see,
pushed and read back. Where the platform has two views of the same fact — Admin
and storefront — asking the API harder only ever confirms the view that is not
the problem. A reusable `{% render 'purelane-debug' %}` snippet, off by default,
is the first thing I would add for the next build.

**A verification pass that runs, not reads.** Everything checkable was checked
by executing something: every `{% schema %}` block parsed as JSON, every JS file
through `node --check`, the CSV through a parser, the contrast ratios computed,
the generated image opened and looked at. None of that is clever. All of it is
the difference between "should work" and "does". This becomes a script that runs
before every push and is the first thing I would write for project two.

**A prototype triage step.** Every one of these arrives as a fast HTML file, and
the same questions pay off every time: how many stylesheets and do they
override each other; which ids are global; what is hardcoded that is really
catalogue data; where does the JS assume it runs once; what breaks under
`prefers-reduced-motion`. That is a checklist an agent can run unsupervised and
report on, and it produces the "what I'd flag" section as a by-product.

**A house section skeleton.** Schema shape, `data-purelane-scene` hook, the
standalone-assets render, the design-mode empty state, padding settings, anchor
id. Six sections here shared one shape; the twentieth should not be rediscovering
it. That plus the shared snippets is most of what makes the second build fast.

**Keep the spec, not just the code.** The useful artifact from this build is not
the Liquid — it is BUILD-NOTES: what the original got wrong and what the fix
was. It is what an agent needs as context to do the next one, and it is what a
client actually reads.

**Do not let it choose the architecture alone.** Whether a combo is a product or
a metaobject, whether reviews are blocks or entries, whether the backdrop is a
section or theme markup — those decide what a merchant can and cannot do a year
from now. An agent will pick whichever is fastest to write. I pick those, then
delegate the writing.
