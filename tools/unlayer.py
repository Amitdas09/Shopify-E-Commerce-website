"""
Take the Purelane stylesheets back out of @layer.

The layer was introduced to stop the duplicated purelane-core.css — emitted once
per section — from overriding section CSS that came earlier in the document. It
fixed that, and quietly created a much worse problem: unlayered CSS beats
layered CSS outright, at any specificity, so every rule in Dawn's base.css
outranked every Purelane rule.

That is why Dawn's h2/h3 typography won over .d2/.d3 and the display headings
rendered in Dawn's font weights instead of Outfit 800, and why Dawn's
`div:empty { display: none }` hid the whole animated backdrop.

The real fix is ordering, not layers:

  * purelane-core.css moves into theme.liquid's head, immediately after Dawn's
    base.css. Emitted once, and later in source order, so it wins on equal
    specificity without needing a layer.
  * per-section CSS stays with its section in the body, which is after the head,
    so it still wins over core. The original bug cannot come back.

Usage: python tools/unlayer.py
"""

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ORDER = re.compile(r"^@layer\s+purelane-base\s*,\s*purelane-section\s*;\s*$", re.M)
OPEN = re.compile(r"^@layer\s+purelane-(?:base|section)\s*\{\s*$", re.M)


def unwrap(text):
    """Strip the @layer statement, the wrapper block, and one level of indent."""
    text = ORDER.sub("", text)

    m = OPEN.search(text)
    if not m:
        return text, False

    head = text[: m.start()]
    rest = text[m.end():]

    close = rest.rstrip()
    if not close.endswith("}"):
        return text, False
    body = rest.rstrip()[:-1]

    out = []
    for line in body.split("\n"):
        out.append(line[2:] if line.startswith("  ") else line)

    return head.rstrip() + "\n\n" + "\n".join(out).strip() + "\n", True


def main():
    changed = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "assets", "purelane-*.css"))):
        src = open(path, encoding="utf-8").read()
        if "@layer" not in src:
            print("  %-28s no layer" % os.path.basename(path))
            continue

        out, ok = unwrap(src)
        if not ok:
            print("  %-28s COULD NOT UNWRAP" % os.path.basename(path))
            continue

        open(path, "w", encoding="utf-8").write(out)
        braces = out.count("{") - out.count("}")
        print("  %-28s unwrapped   brace balance %+d" % (os.path.basename(path), braces))
        changed += 1

    print("\n%d stylesheets unlayered" % changed)


if __name__ == "__main__":
    main()
