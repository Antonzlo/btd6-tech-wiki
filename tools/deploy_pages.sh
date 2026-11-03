#!/bin/sh
# Build for GitHub Pages and push site/ to the gh-pages branch as one signed commit (no CI, main untouched).
set -eu
cd "$(dirname "$0")/.."
python3 -I build.py --pages
touch site/.nojekyll
git fetch -q origin gh-pages 2>/dev/null || true
GIT_INDEX_FILE="$(git rev-parse --absolute-git-dir)/pages-index"
export GIT_INDEX_FILE
rm -f "$GIT_INDEX_FILE"
git --work-tree=site add -A -f .
tree=$(git write-tree)
parent=$(git rev-parse -q --verify refs/remotes/origin/gh-pages || true)
commit=$(git commit-tree -S ${parent:+-p "$parent"} -m "pages: build of $(git rev-parse --short HEAD)" "$tree")
git push -q origin "$commit:refs/heads/gh-pages"
rm -f "$GIT_INDEX_FILE"
echo "pushed $commit"
