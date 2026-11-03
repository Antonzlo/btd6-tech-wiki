#!/bin/sh
# Game icons dumped by btd6-knowledge-dumper (F7 in game) -> data/icons/web/<kind>/<id>.webp.
# Usage: tools/game_icons.sh [<game>/GameIcons]. Needs ImageMagick 7 (magick).
set -eu
cd "$(dirname "$0")/.."
src=${1:-$HOME/.local/share/Steam/steamapps/common/BloonsTD6/GameIcons}
web=data/icons/web

for kind in towers upgrades bloons; do
  mkdir -p "$web/$kind"
  magick mogrify -path "$web/$kind" -format webp -trim +repage -resize '128x128>' -strip -quality 88 "$src/$kind"/*.png
done
mkdir -p "$web/buffs" "$web/ui"
magick mogrify -path "$web/buffs" -format webp -trim +repage -resize '128x128>' -strip -quality 88 "$src"/sprites/BuffIcon*.png

one() {  # one <png> <webp>
  magick "$1" -trim +repage -resize '128x128>' -strip -quality 88 "$2"
}
for f in "$src"/powers/*.png; do
  one "$f" "$web/ui/power-$(basename "$f" .png).webp"
done
grep -v '^#' tools/ui_sprites.txt | while read -r key name; do
  if [ -f "$src/sprites/$name.png" ]; then one "$src/sprites/$name.png" "$web/ui/$key.webp"; else echo "no sprite $name for $key"; fi
done
