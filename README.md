# Daily Research News

Daily markdown digests of tweets I've liked on X — organized day by day, with key topic summaries, tweet permalinks, and resolved titles for external links (arxiv papers, GitHub repos, blog posts, X Articles).

## Format

Notes are organized into `YYYY/MM/` folders (e.g. `2026/06/2026-06-13.md`). Each `YYYY-MM-DD.md` file contains:

- **Key Topics** — one-line summary per liked tweet
- **Liked Tweets** — full content of each tweet with:
  - Author and permalink
  - Tweet text
  - 📎 External links with resolved titles (papers, repos, blogs)
  - ❤️ Likes / 🔁 Retweets

## Coverage

Daily notes from 2025-10-12 onward, updated periodically.

## Updating

The whole pipeline lives in [`scripts/`](scripts/). To sync new likes:

```bash
./scripts/sync.sh <X_USERNAME> <SINCE_YYYY-MM-DD>
# e.g.
./scripts/sync.sh QuocNghi91 2026-06-14
```

This runs four stages sequentially:

1. **`01_scrape_likes.py`** — `gallery-dl --cookies-from-browser chrome` against `https://x.com/<user>/likes`, dedupes by tweet_id.
2. **`02_fetch_titles.py`** — resolves external URLs to human titles (arxiv API for papers, `<title>` tag for everything else).
3. **`03_fetch_articles.py`** — Playwright + Chrome cookies to render X Articles (long-form posts) and extract title + excerpt.
4. **`04_generate_notes.py`** — writes one `YYYY-MM-DD.md` per day, organized into `YYYY/MM/` folders.

After it finishes, commit and push the new days:

```bash
git add '*.md' && git commit -m "sync: <date range>" && git push
```

### Requirements

- Chrome with active X login (cookies are read from Chrome)
- Python 3 with: `gallery-dl`, `playwright`, `browser_cookie3`, `requests-oauthlib`
- Run `python3 -m playwright install chromium` once

### Design notes

- **Why gallery-dl not the X API:** The `/users/:id/liked_tweets` endpoint is paid-tier only. gallery-dl uses your Chrome session cookies and works on the free path.
- **Why Playwright for articles:** x.com serves a JS-only shell; curl returns no article body. gallery-dl treats article URLs as unsupported.
- **Dedup of external URLs:** `http://` vs `https://` variants of the same URL are treated as one.

See [`scripts/SKILL.md`](scripts/SKILL.md) for the full skill spec (used by Claude Code).
