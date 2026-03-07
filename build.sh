#!/bin/bash
# Build Limen EPUB from split chapter files.
#
# Usage:
#   ./build.sh              # Run split + build
#   ./build.sh --no-split   # Build only (skip re-splitting)

set -euo pipefail
cd "$(dirname "$0")"

# Re-split unless --no-split is passed
if [[ "${1:-}" != "--no-split" ]]; then
    echo "Splitting Limen.md into chapters..."
    rm -rf book/
    python3 split.py
    echo
fi

echo "Building EPUB..."

# Collect all chapter markdown files in order
FILES="assets/metadata.yaml"

# Add foreword if it exists
if [[ -f assets/00-foreword.md ]]; then
    FILES="$FILES assets/00-foreword.md"
fi

# Add chapters in order
for chapter_dir in book/0[1-9]-* book/[1-9][0-9]-*; do
    if [[ -d "$chapter_dir" ]]; then
        for md in "$chapter_dir"/*.md; do
            FILES="$FILES $md"
        done
    fi
done

COVER_OPTS=""
if [[ -f assets/cover.jpg ]]; then
    COVER_OPTS="--epub-cover-image=assets/cover.jpg"
fi

pandoc $FILES \
    -o limen.epub \
    --css=assets/limen.css \
    --epub-title-page=true \
    --toc \
    --toc-depth=1 \
    $COVER_OPTS

echo "Done: limen.epub"
