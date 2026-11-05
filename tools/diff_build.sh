#!/bin/sh
# Which pages change: builds REF (default HEAD) in a temporary worktree and the working tree, then lists the
# differing files. Use after refreshing data/ to see what a game update changed, or after a refactor to prove
# nothing did. A change to site.js touches every page (its cache-busting hash is in each one).
set -eu
cd "$(dirname "$0")/.."
ref=${1:-HEAD}
tmp=$(mktemp -d)
trap 'git worktree remove --force "$tmp/base" 2>/dev/null; rm -rf "$tmp"' EXIT
git worktree add -q --detach "$tmp/base" "$ref"
python3 -I "$tmp/base/build.py" --pages 2>/dev/null
python3 -I build.py --pages
if diff -rq "$tmp/base/site" site >"$tmp/diff"; then
    echo "site identical to $ref"
else
    sed "s|$tmp/base/site|$ref|g" "$tmp/diff"
fi
