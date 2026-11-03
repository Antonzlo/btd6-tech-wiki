#!/bin/sh
# Icons the game does not have: a source icon with a red "not allowed" sign over it.
# Run after fetch_icons.py and the webp conversion. Needs ImageMagick 7 (magick).
set -eu
cd "$(dirname "$0")/.."
out=data/icons/web/ui

ban() {  # ban <source image> <output name>
  magick "$1" -resize 112x112 -gravity center -background none -extent 128x128 \
    \( -size 128x128 xc:none -fill none -stroke '#d93a36' -strokewidth 8 \
       -draw 'circle 64,64 64,8' -draw 'line 24,24 104,104' \) -composite \
    -quality 88 "$out/$2.webp"
}

ban data/KnowledgeLayout/icons/ManaShield.webp nomana
ban data/icons/raw/ui/knowledge.png noknowledge
