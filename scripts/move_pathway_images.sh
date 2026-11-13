#!/usr/bin/env bash
# move_pathway_images.sh
#
# For each pathway folder src/path-*/, move the images that ONLY that pathway
# uses into src/assets/images/<pathway>/ and rewrite the image paths in the
# pathway's .njk pages.
#
# An image is left where it is if anything outside the pathway also references
# it (other pages, layouts, CSS, scripts, README). That is why shared files such
# as hurricane-icon.png stay in src/assets/images/.
#
# Safe to re-run: images already in a subfolder are not matched again.
#
# Usage (from anywhere):
#   scripts/move_pathway_images.sh --dry-run    # show what would happen
#   scripts/move_pathway_images.sh              # do it
#   scripts/move_pathway_images.sh path-creative-resistance   # one pathway only
#
# Notes:
#   - Uses `git mv` when the file is tracked, plain `mv` otherwise.
#   - `sed -i ''` is the macOS form; on Linux change it to `sed -i`.
#   - Assumes image paths are written as '/assets/images/<file>' in single
#     quotes, as in {{ '/assets/images/x.jpg' | url }}.

set -euo pipefail

DRY=0
ONLY=""
for arg in "$@"; do
  case "$arg" in
    --dry-run|-n) DRY=1 ;;
    *) ONLY="${arg%/}" ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

run() { if [ "$DRY" -eq 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

for dir in src/path-*/; do
  name="$(basename "$dir")"
  [ -n "$ONLY" ] && [ "$name" != "$ONLY" ] && continue

  dest="src/assets/images/$name"
  echo "== $name"
  [ "$DRY" -eq 1 ] || mkdir -p "$dest"

  # Unique image filenames this pathway references directly under /assets/images/
  # (the closing quote is required, so already-moved paths with a subfolder don't match)
  files="$(grep -rhoE "/assets/images/[^'/]+'" "src/$name" | sed -E "s#.*/##; s#'\$##" | sort -u || true)"

  for file in $files; do
    # Is the file referenced anywhere outside this pathway's pages?
    shared="$(grep -rlF -- "$file" src scripts README.md .github 2>/dev/null \
      | grep -v "^src/$name/" | grep -v "^scripts/move_pathway_images.sh$" || true)"
    if [ -n "$shared" ]; then
      echo "  shared, left in place: $file"
      continue
    fi

    src_file="src/assets/images/$file"
    if [ ! -f "$src_file" ]; then
      echo "  MISSING on disk: $file"
      continue
    fi

    echo "  move: $file"
    if git ls-files --error-unmatch "$src_file" >/dev/null 2>&1; then
      run git mv "$src_file" "$dest/$file"
    else
      run mv -n "$src_file" "$dest/$file"
    fi
    run sed -i '' "s#/assets/images/$file#/assets/images/$name/$file#g" "src/$name"/*.njk
  done
done

if [ "$DRY" -eq 0 ]; then
  echo "== build check"
  npm run build 2>&1 | tail -1
  # Every image path in pages must exist on disk
  missing=0
  for p in $(grep -rhoE "/assets/images/[^']+" src --include='*.njk' | sort -u); do
    [ -f "src$p" ] || { echo "  MISSING: $p"; missing=1; }
  done
  [ "$missing" -eq 0 ] && echo "  all referenced images exist"
fi
