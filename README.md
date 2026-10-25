# Daily Research News

Research news from posts I've liked on X and LinkedIn, with topic summaries, post permalinks, and external research links.

## Sources

- [`X/`](X/) — the existing X archive, including daily notes, newsletters, and research picks.
- [`LinkedIn/`](LinkedIn/README.md) — LinkedIn liked posts and import coverage, focused on 2026.
- [`scripts/`](scripts/) — import and audit tools.

Each source keeps its own provenance, even when the same research appears on both platforms. LinkedIn notes distinguish publication dates from unavailable reaction timestamps.

## Format

X notes are organized into `X/YYYY/MM/` folders (e.g. `X/2026/06/2026-06-13.md`). Each `YYYY-MM-DD.md` file contains:

- **Key Topics** — one-line summary per liked tweet
- **Liked Tweets** — full content of each tweet with:
  - Author and permalink
  - Tweet text
  - 📎 External links with resolved titles (papers, repos, blogs)
  - ❤️ Likes / 🔁 Retweets

## Coverage

X daily notes run from 2025-10-12 onward. The LinkedIn collection is a partial 2026 backfill: [read the collection and pending coverage](LinkedIn/README.md).

## Updating X

The X pipeline lives in [`scripts/`](scripts/). To sync new X likes:

```bash
./scripts/sync.sh <X_USERNAME> [SINCE_YYYY-MM-DD]
# e.g.
./scripts/sync.sh QuocNghi91              # default: re-covers the last 7 days
./scripts/sync.sh QuocNghi91 2026-06-14   # explicit cutoff
```

> ### ⚠️ Always sync with overlap
> Do **not** start from "the day after the last note." Likes made late in the
> evening of day *D* are invisible to a sync run earlier that day, and a
> next-day sync starting at *D+1* never revisits them. This silently dropped
> **71 likes across 37 days** (back to 2025-11-07) before `audit.py` caught it.
> Regeneration is idempotent, so overlap costs nothing — hence the default
> 7-day lookback (override with the `LOOKBACK_DAYS` env var).

This runs five stages sequentially:

1. **`01_scrape_likes.py`** — `gallery-dl --cookies-from-browser chrome` against `https://x.com/<user>/likes`, dedupes by tweet_id.
2. **`02_fetch_titles.py`** — resolves external URLs to human titles (arxiv API for papers, `<title>` tag for everything else).
3. **`03_fetch_articles.py`** — Playwright + Chrome cookies to render X Articles (long-form posts) and extract title + excerpt.
4. **`04_generate_notes.py`** — writes one `YYYY-MM-DD.md` per day, organized into `X/YYYY/MM/` folders.
5. **`audit.py`** — diffs the whole archive against the scrape and reports any day that is missing entirely or missing individual likes.

After it finishes, commit and push the new days:

```bash
git add '*.md' && git commit -m "sync: <date range>" && git push
```

### Repairing gaps

`audit.py` runs automatically at the end of every sync, but can be run standalone
and exits non-zero when it finds gaps (so it can gate CI):

```bash
python3 scripts/audit.py --likes /tmp/x_likes_new.json --repo X \
  --write-affected /tmp/affected_days.json
```

To rebuild only the affected days without touching the other ~200 notes, pass the
list to the generator — `--only-days` accepts a comma-separated list or `@file`
pointing at a JSON array:

```bash
python3 scripts/04_generate_notes.py \
  --likes /tmp/x_likes_new.json --titles <titles.json> --articles <articles.json> \
  --since 2025-10-12 --only-days @/tmp/affected_days.json --vault-dir X
```

**Merge your title/article caches before a backfill.** Regenerating a day rewrites
it completely, so if the cache lacks that day's URLs the note will *lose* its
previously resolved link titles and fall back to raw URLs.

### Requirements

- Chrome with active X login (cookies are read from Chrome)
- Python 3 with: `gallery-dl`, `playwright`, `browser_cookie3`, `requests-oauthlib`
- Run `python3 -m playwright install chromium` once

### Design notes

- **Why gallery-dl not the X API:** The `/users/:id/liked_tweets` endpoint is paid-tier only. gallery-dl uses your Chrome session cookies and works on the free path.
- **Why Playwright for articles:** x.com serves a JS-only shell; curl returns no article body. gallery-dl treats article URLs as unsupported.
- **Dedup of external URLs:** `http://` vs `https://` variants of the same URL are treated as one.

See [`scripts/SKILL.md`](scripts/SKILL.md) for the full skill spec (used by Claude Code).
