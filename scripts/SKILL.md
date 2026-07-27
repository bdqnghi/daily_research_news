---
name: sync-x-likes-to-obsidian
description: Sync the user's X (Twitter) likes into their Obsidian vault as daily markdown notes. Use when the user asks to export/sync/import their X likes, save likes to Obsidian, or create daily notes from liked tweets. Produces one note per day with key topic summaries, tweet content, permalinks, and resolved titles for any external links (papers, GitHub repos, blog posts, X Articles).
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Sync X Likes to Obsidian

Scrapes the user's X likes, resolves link titles, fetches X Article content, and writes daily markdown notes into their Obsidian vault.

## When to Use

- "Sync my X likes to Obsidian"
- "Export my Twitter likes as markdown"
- "Update my X likes notes"
- "Refresh the likes in my vault"

## Prerequisites

- **Chrome with active X login** — cookies are pulled from Chrome for scraping.
- **Python 3** with packages: `gallery-dl`, `playwright`, `browser_cookie3`, `requests-oauthlib`. Install missing ones with `pip3 install <pkg>`. For Playwright also run `python3 -m playwright install chromium` once.
- **Obsidian vault path** — ask the user if unknown. Default hint: `~/Documents/Obsidian/<vault>/X/`.
- **X username** — needed to build the likes URL.

## Workflow

**ALWAYS sync with overlap — never start from "the day after the last note."** Likes made
late in the evening of day *D* are invisible to a sync run earlier that day, and a next-day
sync starting at *D+1* never revisits them. This silently dropped 71 likes across 37 days
before `audit.py` caught it. Regeneration is idempotent, so overlap is free — default to a
7-day lookback. Compute the cutoff from *today minus 7*, not from the newest note on disk.

The scripts live in `~/.claude/skills/sync-x-likes-to-obsidian/scripts/`. Run them in order; each writes intermediate JSON next to itself so later runs can skip stages that already succeeded.

### Step 1 — Scrape likes

```bash
python3 ~/.claude/skills/sync-x-likes-to-obsidian/scripts/01_scrape_likes.py \
  --username <X_USERNAME> \
  --out /tmp/x_likes.json
```

Uses `gallery-dl --cookies-from-browser chrome --dump-json` on `https://x.com/<user>/likes`. Deduplicates by tweet_id and keeps: tweet_id, author, author_nick, content, date, favorite_count, retweet_count, reply_count, lang.

Expect thousands of entries and only a subset in the desired time window.

### Step 2 — Resolve external link titles

```bash
python3 ~/.claude/skills/sync-x-likes-to-obsidian/scripts/02_fetch_titles.py \
  --likes /tmp/x_likes.json \
  --since YYYY-MM-DD \
  --out /tmp/url_titles.json
```

- Arxiv IDs batched via `export.arxiv.org/api/query` (20 per request).
- Other URLs fetched via `urllib` with a browser UA; uses `<title>` tag or `og:title`. 15 threads in parallel.
- Skips `x.com` / `twitter.com` links (they're handled in step 3).

Typically resolves ~90% of non-article links.

### Step 3 — Fetch X Article content (Playwright)

```bash
python3 ~/.claude/skills/sync-x-likes-to-obsidian/scripts/03_fetch_articles.py \
  --likes /tmp/x_likes.json \
  --since YYYY-MM-DD \
  --out /tmp/article_contents.json
```

X Articles are long-form posts at `x.com/i/article/<id>` — they're pure JS and can't be scraped via curl. Playwright loads each with the user's Chrome cookies (via `browser_cookie3`), waits for DOM, extracts title + excerpt. Some articles require interactive interaction; those fall through to a generic label.

### Step 4 — Generate daily notes

```bash
python3 ~/.claude/skills/sync-x-likes-to-obsidian/scripts/04_generate_notes.py \
  --likes /tmp/x_likes.json \
  --titles /tmp/url_titles.json \
  --articles /tmp/article_contents.json \
  --since YYYY-MM-DD \
  --vault-dir "/Users/<user>/Documents/Obsidian/<vault>/X"
```

Writes one `YYYY-MM-DD.md` per day. Each note has:

- `# X Likes — YYYY-MM-DD` header
- `## Key Topics` — bullet per tweet: `- **@handle** — <summary>` where summary is the first substantive line (skips hashtag-only / emoji-heavy lines). X Articles use the fetched title.
- `## Liked Tweets` — per-tweet block with:
  - `### @handle (Display Name)`
  - `[Tweet](permalink)` — `https://x.com/<handle>/status/<id>`
  - Blockquoted content (x.com inline links stripped)
  - Article tweets get the fetched title in bold + excerpt
  - External links as `📎 [<resolved title>](url)` — falls back to `📎 [Paper: arxiv.org/...](url)` style when a title couldn't be fetched
  - `❤️ <fav> | 🔁 <rt>`

### Step 5 — Audit for gaps

```bash
python3 ~/.claude/skills/sync-x-likes-to-obsidian/scripts/audit.py \
  --likes /tmp/x_likes.json --repo <vault-or-repo-dir> \
  --write-affected /tmp/affected_days.json
```

Diffs every day-note against the scrape and reports days missing entirely or missing
individual likes. Exits non-zero when gaps exist. To repair only those days without
rewriting the rest of the archive, pass them back to step 4 via
`--only-days @/tmp/affected_days.json` (also accepts a comma-separated list).

**Merge title/article caches before any backfill.** Regenerating a day rewrites it
completely — if the cache lacks that day's URLs, the note *loses* previously resolved
link titles and falls back to raw URLs. Merge all prior `url_titles*.json` /
`article_contents*.json` into a master cache first, and when merging article results
never let an empty title overwrite a good one.

## Design Notes

- **Why gallery-dl not the X API**: the `/users/:id/liked_tweets` endpoint requires a paid X API tier. gallery-dl uses your logged-in Chrome cookies and works on the free path.
- **Why Playwright for articles**: x.com serves a JS-only shell; `curl` returns no article body. Even `gallery-dl` treats article URLs as unsupported and leaves the tweet `content` as just the URL.
- **Dedup of external URLs**: `http://` vs `https://` variants of the same URL are treated as one.
- **Cutoff defaults**: if the user says "last N months", compute the cutoff date from today and pass it as `--since`.

## Common Issues

- **gallery-dl "Unsupported URL" for article pages** — expected; articles only work when loaded via Playwright from a tweet permalink.
- **Playwright `networkidle` timeout on x.com** — use `wait_until="domcontentloaded"` + a fixed sleep instead.
- **X API 402 CreditsDepleted** — the paid-tier endpoints are off-limits without a subscription. Do not retry; fall back to scraping.
- **Empty article title + excerpt** — roughly 20–30% of articles need interactive login and won't render in headless. Fall back to the generic "X Article (long-form post)" label and keep the URL.
- **Obsidian MCP hangs** — do not route file writes through an Obsidian MCP; write `.md` files directly to the vault folder. Obsidian auto-picks up filesystem changes.
