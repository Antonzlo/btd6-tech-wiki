#!/bin/sh
# Game icons dumped by btd6-knowledge-dumper (F7 in game) -> data/icons/web/<kind>/<id>.webp.
# Usage: tools/game_icons.sh [<game>/GameIcons]. Needs ImageMagick 7 (magick).
set -eu
cd "$(dirname "$0")/.."
src=${1:-$HOME/.local/share/Steam/steamapps/common/BloonsTD6/GameIcons}
web=data/icons/web

for kind in towers upgrades bloons heroes abilities achievements geraldo maps; do
  mkdir -p "$web/$kind"
  [ -d "$src/$kind" ] || continue
  magick mogrify -path "$web/$kind" -format webp -trim +repage -resize '128x128>' -strip -quality 88 "$src/$kind"/*.png
done
rm -rf "$web/buffs"
mkdir -p "$web/buffs" "$web/ui"

one() {  # one <png> <webp>
  magick "$1" -trim +repage -resize '128x128>' -strip -quality 88 "$2"
}
# buffs: the iconName from data/Buffs; some sprites are named differently, try the usual variants
grep -ho '"iconName": "[^"]*"' data/Buffs/*.json | cut -d'"' -f4 | sort -u | while read -r n; do
  rest=${n#Map}; rest=${rest#BuffIcon}; rest=${rest#Buff}
  found=
  if [ -f "$src/buffs/$n.png" ]; then one "$src/buffs/$n.png" "$web/buffs/$n.webp"; continue; fi
  for c in "$n" "BuffIcon$rest" "$rest" "${rest}Icon" "${rest}UpgradeIcon"; do
    if [ -f "$src/sprites/$c.png" ]; then one "$src/sprites/$c.png" "$web/buffs/$n.webp"; found=1; break; fi
  done
  if [ -z "$found" ]; then  # e.g. BuffIconOvercharge -> BuffIconBoomerangOvercharge
    c=$(ls "$src/sprites/" | grep -m1 "^BuffIcon.*$rest\.png$" || true)
    if [ -n "$c" ]; then one "$src/sprites/$c" "$web/buffs/$n.webp"; else echo "no sprite for buff $n"; fi
  fi
done
for f in "$src"/powers/*.png; do
  one "$f" "$web/ui/power-$(basename "$f" .png).webp"
done
grep -v '^#' tools/ui_sprites.txt | while read -r key name; do
  if [ -f "$src/sprites/$name.png" ]; then one "$src/sprites/$name.png" "$web/ui/$key.webp"; else echo "no sprite $name for $key"; fi
done
