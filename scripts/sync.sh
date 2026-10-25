#!/usr/bin/env bash
# Sync new X likes into this repo as daily markdown notes.
#
# Usage:
#   ./sync.sh <X_USERNAME> [SINCE_DATE]
#   ./sync.sh QuocNghi91              # default: re-sync the last 7 days
#   ./sync.sh QuocNghi91 2026-06-14   # explicit cutoff
#
# WHY THE DEFAULT IS A LOOKBACK, NOT "the day after the last note":
#   Likes made late in the evening of day D are missed if you sync on day D
#   and then next sync from D+1 — that day is never revisited. This silently
#   dropped 71 likes across 37 days before it was caught (see audit.py).
#   Regeneration is idempotent, so always re-cover a few days of overlap.
#
# Requires:
#   - Chrome with active X login (cookies are read from Chrome)
#   - Python 3 with: gallery-dl, playwright, browser_cookie3, requests-oauthlib
#   - Run `python3 -m playwright install chromium` once.

set -euo pipefail

USERNAME="${1:?usage: sync.sh <username> [since-YYYY-MM-DD]}"
LOOKBACK_DAYS="${LOOKBACK_DAYS:-7}"
SINCE="${2:-$(date -v-"${LOOKBACK_DAYS}"d +%Y-%m-%d 2>/dev/null || date -d "${LOOKBACK_DAYS} days ago" +%Y-%m-%d)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
X_DIR="$REPO_DIR/X"
TMP=/tmp

echo "→ [1/4] Scraping likes for @$USERNAME"
python3 "$SCRIPT_DIR/01_scrape_likes.py" --username "$USERNAME" --out "$TMP/x_likes_new.json"

echo "→ [2/4] Resolving external link titles (since $SINCE)"
python3 "$SCRIPT_DIR/02_fetch_titles.py" --likes "$TMP/x_likes_new.json" --since "$SINCE" --out "$TMP/url_titles_new.json"

echo "→ [3/4] Fetching X Article content"
python3 "$SCRIPT_DIR/03_fetch_articles.py" --likes "$TMP/x_likes_new.json" --since "$SINCE" --out "$TMP/article_contents_new.json"

echo "→ [4/4] Generating daily notes into $X_DIR (since $SINCE, overlap is intentional)"
python3 "$SCRIPT_DIR/04_generate_notes.py" \
  --likes "$TMP/x_likes_new.json" \
  --titles "$TMP/url_titles_new.json" \
  --articles "$TMP/article_contents_new.json" \
  --since "$SINCE" \
  --vault-dir "$X_DIR"

echo
echo "→ [5/5] Auditing archive for gaps"
python3 "$SCRIPT_DIR/audit.py" --likes "$TMP/x_likes_new.json" --repo "$X_DIR" || true

echo
echo "Changed notes:"
git -C "$REPO_DIR" status --short -- '*.md' | tail -30
