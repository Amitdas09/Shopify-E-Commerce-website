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

The pattern in all four: the failures are never in the interesting logic. They
are in the boring interface between systems — a filter name, a drop's type, a
comma. Everything I actually verify is at those seams.

## What I'd systematise for twenty more of these

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
