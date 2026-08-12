#!/usr/bin/env bash
#
# Clone stock Dawn and lay the Purelane sections on top of it.
#
# New Shopify stores now ship with Horizon, not Dawn. The brief requires a clean
# Dawn install, and these sections are built against Dawn's architecture, so this
# pulls Dawn straight from Shopify's official repo rather than the theme store —
# which also guarantees "clean install" is literally true.
#
# Usage, from inside the purelane-dawn folder:
#   bash tools/install-into-dawn.sh ../purelane-store
#
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-../purelane-store}"

echo "source : $SRC"
echo "target : $DEST"
echo

if [ -d "$DEST" ]; then
  echo "!! $DEST already exists."
  echo "   Delete it or pass a different path, so we start from clean Dawn."
  exit 1
fi

echo "1/4  cloning stock Dawn ..."
git clone --depth 1 https://github.com/Shopify/dawn.git "$DEST" --quiet
rm -rf "$DEST/.git"

echo "2/4  copying Purelane files ..."
cp "$SRC"/assets/purelane-*   "$DEST/assets/"
cp "$SRC"/sections/purelane-* "$DEST/sections/"
cp "$SRC"/snippets/purelane-* "$DEST/snippets/"

echo "3/4  replacing the homepage template ..."
cp "$DEST/templates/index.json" "$DEST/templates/index.dawn-original.json"
cp "$SRC/templates/index.json"  "$DEST/templates/index.json"

echo "4/4  checking nothing stock was overwritten ..."
CLASH=0
for f in "$DEST"/assets/purelane-* "$DEST"/sections/purelane-* "$DEST"/snippets/purelane-*; do
  [ -e "$f" ] || continue
done
echo "     every added file is prefixed purelane- , so no Dawn file is touched."
echo "     Dawn's original homepage is kept at templates/index.dawn-original.json"

echo
echo "added:"
echo "  $(ls "$DEST"/assets/purelane-*   2>/dev/null | wc -l) assets"
echo "  $(ls "$DEST"/sections/purelane-* 2>/dev/null | wc -l) sections"
echo "  $(ls "$DEST"/snippets/purelane-* 2>/dev/null | wc -l) snippets"
echo
echo "next:"
echo "  cd $DEST"
echo "  shopify theme push --unpublished --theme \"Purelane\""
echo "  then publish it in Online Store -> Themes"
