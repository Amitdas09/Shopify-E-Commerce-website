"""
Generate templates/index.json with every Purelane section in the prototype's
order.

Hand-maintaining a 15-section JSON template is how anchors and product handles
drift apart. This keeps the order, the anchor ids and the handle references in
one place that can be re-run.
"""

import collections
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAD = {"padding_top": 34, "padding_bottom": 34}

S = collections.OrderedDict()

S["purelane_backdrop"] = {
    "type": "purelane-ambient",
    "settings": {"show_water": True, "show_vignette": True, "parallax": True},
}

rail = ["reviews Reviews", "ingredients Ingredients", "how How it works",
        "proof Proof", "bundles Bundles", "shop Shop"]
S["purelane_rail"] = {
    "type": "purelane-rail",
    "blocks": {
        "d%d" % i: {"type": "dot", "settings": {"anchor": r.split(" ", 1)[0],
                                                "label": r.split(" ", 1)[1]}}
        for i, r in enumerate(rail, 1)
    },
    "block_order": ["d%d" % i for i in range(1, len(rail) + 1)],
    "settings": {"label": "Section progress"},
}

S["purelane_hero"] = {
    "type": "purelane-hero",
    "blocks": {
        "p1": {"type": "promise", "settings": {"icon": "leaf", "line_1": "Plant", "line_2": "powered"}},
        "p2": {"type": "promise", "settings": {"icon": "shield", "line_1": "Safe for", "line_2": "kids & pets"}},
        "p3": {"type": "promise", "settings": {"icon": "no-chem", "line_1": "Zero harsh", "line_2": "chemicals"}},
        "s1": {"type": "slide", "settings": {
            "label": "Single bottle", "product_1": "kitchen-cleaner-foaming",
            "saving_style": "percent"}},
        "s2": {"type": "slide", "settings": {
            "label": "Any 2 products", "product_1": "tap-cleaner-limescale-remover",
            "product_2": "kitchen-cleaner-foaming",
            "price_product": "hard-water-solution-kit", "saving_style": "amount"}},
        "s3": {"type": "slide", "settings": {
            "label": "Any 3 products", "product_1": "tap-cleaner-limescale-remover",
            "product_2": "copper-bronze-brass-cleaner", "product_3": "kitchen-cleaner-foaming",
            "price_product": "kitchen-essentials-combo", "saving_style": "amount"}},
    },
    "block_order": ["p1", "p2", "p3", "s1", "s2", "s3"],
    "settings": {
        "heading": "Clean\nThat", "heading_highlight": "Lasts", "show_rule": True,
        "subheading": "Homecare that works on the toughest grime, made from plants. "
                      "Kind to your home, your family and the world outside it.",
        "button_1_label": "Shop now", "button_1_link": "/#shop",
        "button_2_label": "How it works", "button_2_link": "/#how",
        "stage_label": "Purelane bundles", "autoplay_seconds": 4, "scene_depth": 1,
    },
}

S["purelane_reviews"] = {"type": "purelane-reviews", "settings": dict(PAD, **{
    "kicker": "That" + "’" + "s what they said",
    "average_rating": "4.8", "rating_caption": "from 8,000+ reviews",
    "reach_prefix": "Loved by", "reach_number": "12 lakh+", "reach_suffix": "homes",
    "rail_label": "Customer reviews", "anchor_id": "reviews", "scene_depth": 1})}

ings = [("coconut", "Coconut", "Plant-derived cleansers that lift grease"),
        ("orange-peel", "Orange peel", "Natural degreaser and fresh citrus lift"),
        ("soap-nut", "Soap nut", "A traditional plant foaming agent"),
        ("neem", "Neem", "Time-tested antibacterial from the tree"),
        ("lemongrass", "Lemongrass", "Clean fragrance with nothing synthetic")]
S["purelane_ingredients"] = {
    "type": "purelane-ingredients",
    "blocks": {"i%d" % i: {"type": "ingredient", "settings": {"art": a, "name": n, "text": t}}
               for i, (a, n, t) in enumerate(ings, 1)},
    "block_order": ["i%d" % i for i in range(1, 6)],
    "settings": dict(PAD, **{"heading": "Sourced from nature", "show_rule": True,
                             "anchor_id": "ingredients", "scene_depth": 2}),
}

pillars = [("leaf", "Less scrubbing",
            "A foaming formulation. The foam clings to grease and lifts it, so you wipe instead of scrub.", "/#shop"),
           ("shield", "Clean ingredients",
            "No sulphates, no chlorine, no synthetic fragrance. Nothing on the label you would not want near your food.", "/#ingredients"),
           ("no-chem", "Safe around everyone",
            "Gentle on hands, safe around kids and pets, and it leaves no toxic residue on the surfaces you touch every day.", "/#proof")]
S["purelane_pillars"] = {
    "type": "purelane-pillars",
    "blocks": {"c%d" % i: {"type": "pillar", "settings": {
        "icon": ic, "heading": h, "text": t,
        "button_label": "Learn more", "button_link": u}}
        for i, (ic, h, t, u) in enumerate(pillars, 1)},
    "block_order": ["c1", "c2", "c3"],
    "settings": dict(PAD, **{"anchor_id": "how", "scene_depth": 2}),
}

stats = [("99.9%", "Germ kill", "Tested against germs and bacteria"),
         ("0%", "Sulphates", "No SLS, chlorine or parabens"),
         ("100%", "Plant based", "Cleansers derived from plants"),
         ("4.8", "Rated", "Across 8,000+ verified reviews")]
S["purelane_proof"] = {
    "type": "purelane-proof",
    "blocks": {"t%d" % i: {"type": "stat", "settings": {"figure": f, "label": l, "text": x}}
               for i, (f, l, x) in enumerate(stats, 1)},
    "block_order": ["t1", "t2", "t3", "t4"],
    "settings": dict(PAD, **{
        "kicker": "Why it works",
        "heading": "Tough on grime.\nGentle on everything else.",
        "text": "Every formula is built on plant-derived cleansers and essential oils. "
                "It behaves exactly like the cleaner you are used to, minus the things "
                "you never signed up for.",
        "button_label": "See the ingredient list", "button_link": "/#ingredients",
        "products": ["kitchen-cleaner-foaming", "tap-cleaner-limescale-remover",
                     "laundry-detergent", "toilet-cleaner", "floor-cleaner", "dishwash-gel"],
        "rotator_label": "Purelane products", "rotate_seconds": 3,
        "anchor_id": "proof", "scene_depth": 3}),
}

S["purelane_combos"] = {"type": "purelane-combos", "settings": dict(PAD, **{
    "kicker": "Pre-built to save you money", "heading": "Best selling combos", "show_rule": True,
    "subheading": "Swipe through the boxes people order most. Each one is already priced "
                  "below buying the same products on their own.",
    "source": "collection", "collection": "combos", "combos_to_show": 6,
    "button_label": "Shop bundle",
    "fine_print": "Inclusive of all taxes · COD available",
    "swipe_cue": "Swipe for more combos",
    "rail_note": "Tapping “Shop bundle” opens the bundle picker with these products "
                 "already added. You can still swap anything before you pay.",
    "anchor_id": "combos", "scene_depth": 3})}

tiers = [("Starter", 2, "hard-water-solution-kit",
          "Pick any two products\nFree shipping across India", False),
         ("Most popular", 3, "kitchen-essentials-combo",
          "Pick any three products\nCovers kitchen and laundry\nFree shipping across India", True),
         ("Whole home", 5, "complete-home-bundle",
          "Pick any five products\nEvery room in one order\nFree shipping across India", False)]
S["purelane_bundles"] = {
    "type": "purelane-bundles",
    "blocks": {"b%d" % i: {"type": "tier", "settings": {
        "tag": tag, "quantity": q, "quantity_label": "Products", "product": p,
        "features": f, "highlight": hl,
        "button_label": "Build this box", "button_link": "/#shop"}}
        for i, (tag, q, p, f, hl) in enumerate(tiers, 1)},
    "block_order": ["b1", "b2", "b3"],
    "settings": dict(PAD, **{
        "kicker": "Build your bundle", "heading": "One box. Every room.",
        "subheading": "Mix and match across kitchen, laundry, home and skin. One flat "
                      "price, no code needed, free shipping either way.",
        "anchor_id": "bundles", "scene_depth": 3}),
}

S["purelane_shop"] = {"type": "purelane-product-grid", "settings": dict(PAD, **{
    "kicker": "Bestsellers", "heading": "Loved by 30,000 homes", "show_rule": True,
    "source": "collection", "collection": "bestsellers", "products_to_show": 8,
    "columns_desktop": 4, "show_rating": True,
    "anchor_id": "shop", "scene_depth": 3})}

S["purelane_range"] = {"type": "purelane-range", "settings": dict(PAD, **{
    "kicker": "The full range", "heading": "Every room, one shelf",
    "text": "Floors, taps, kitchen, laundry, bathroom and hands. Plant-based formulas "
            "that replace every harsh bottle under your sink.",
    "hint": "Swipe to see the full shelf", "source": "collection",
    "collection": "bestsellers", "products_to_show": 10,
    "anchor_id": "range", "scene_depth": 3})}

why = [("check", "Save up to 45%", "Versus buying the same products separately"),
       ("shield", "One flat price", "No calculators, no comparing carts"),
       ("leaf", "Curated by experts", "Products picked to work well together"),
       ("truck", "Free shipping always", "Included on every bundle, all India")]
S["purelane_whybundles"] = {
    "type": "purelane-why-bundles",
    "blocks": {"w%d" % i: {"type": "reason", "settings": {"icon": ic, "heading": h, "text": t}}
               for i, (ic, h, t) in enumerate(why, 1)},
    "block_order": ["w1", "w2", "w3", "w4"],
    "settings": dict(PAD, **{"kicker": "The smarter way to shop",
                             "heading": "Why bundles beat buying single",
                             "anchor_id": "whybundles", "scene_depth": 4}),
}

cats = [("bestsellers", "kitchen-cleaner-foaming", "Kitchen bundle", "Grease, dishes & more"),
        ("combos", "toilet-cleaner", "Bathroom bundle", "Deep clean & disinfect"),
        ("combos", "laundry-detergent", "Laundry bundle", "Softer, fresher wash"),
        ("combos", "tap-cleaner-limescale-remover", "Hard water bundle", "Melt away limescale")]
S["purelane_categories"] = {
    "type": "purelane-categories",
    "blocks": {"k%d" % i: {"type": "category", "settings": {
        "collection": c, "product": p, "heading": h, "text": t}}
        for i, (c, p, h, t) in enumerate(cats, 1)},
    "block_order": ["k1", "k2", "k3", "k4"],
    "settings": dict(PAD, **{"kicker": "Bundle categories",
                             "heading": "Find the right bundle for you",
                             "anchor_id": "categories", "scene_depth": 4}),
}

trust = [("leaf", "Plant derived\nformulas"), ("check", "Recyclable\npackaging"),
         ("shield", "Safe for\nkids & pets"), ("truck", "Made in\nIndia")]
S["purelane_trust"] = {
    "type": "purelane-trust",
    "blocks": {"r%d" % i: {"type": "point", "settings": {"icon": ic, "text": t}}
               for i, (ic, t) in enumerate(trust, 1)},
    "block_order": ["r1", "r2", "r3", "r4"],
    "settings": dict(PAD, **{"scene_depth": 4}),
}

S["purelane_signup"] = {"type": "purelane-signup", "settings": dict(PAD, **{
    "kicker": "Join the Purelane Club",
    "heading": "Get ₹100 off your first bundle",
    "text": "Plus first access to new launches and restocks.",
    "placeholder": "your@email.com", "button_label": "Get my ₹100 off",
    "success_text": "Thanks. Check your inbox for the code.",
    "scene_depth": 4})}


def main():
    doc = {"sections": S, "order": list(S)}
    path = os.path.join(ROOT, "templates", "index.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("%d sections written to templates/index.json\n" % len(S))
    for key, val in S.items():
        blocks = len(val.get("blocks", {}))
        print("  %-26s %-28s %s" % (key, val["type"],
                                    ("%d blocks" % blocks) if blocks else ""))


if __name__ == "__main__":
    main()
