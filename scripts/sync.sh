#!/usr/bin/env bash
# Sync new X likes into this repo as daily markdown notes.
#
# Usage:
#   ./sync.sh <X_USERNAME> <SINCE_DATE>
#   ./sync.sh QuocNghi91 2026-06-14
#
# Requires:
#   - Chrome with active X login (cookies are read from Chrome)
#   - Python 3 with: gallery-dl, playwright, browser_cookie3, requests-oauthlib
#   - Run `python3 -m playwright install chromium` once.

set -euo pipefail

USERNAME="${1:?usage: sync.sh <username> <since-YYYY-MM-DD>}"
SINCE="${2:?usage: sync.sh <username> <since-YYYY-MM-DD>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TMP=/tmp

echo "→ [1/4] Scraping likes for @$USERNAME"
python3 "$SCRIPT_DIR/01_scrape_likes.py" --username "$USERNAME" --out "$TMP/x_likes_new.json"

echo "→ [2/4] Resolving external link titles (since $SINCE)"
python3 "$SCRIPT_DIR/02_fetch_titles.py" --likes "$TMP/x_likes_new.json" --since "$SINCE" --out "$TMP/url_titles_new.json"

echo "→ [3/4] Fetching X Article content"
python3 "$SCRIPT_DIR/03_fetch_articles.py" --likes "$TMP/x_likes_new.json" --since "$SINCE" --out "$TMP/article_contents_new.json"

echo "→ [4/4] Generating daily notes into $REPO_DIR"
python3 "$SCRIPT_DIR/04_generate_notes.py" \
  --likes "$TMP/x_likes_new.json" \
  --titles "$TMP/url_titles_new.json" \
  --articles "$TMP/article_contents_new.json" \
  --since "$SINCE" \
  --vault-dir "$REPO_DIR"

echo
echo "Done. New notes:"
git -C "$REPO_DIR" status --short -- '*.md' | tail -20
