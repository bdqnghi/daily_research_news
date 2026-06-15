#!/usr/bin/env python3
"""Scrape X likes via gallery-dl using Chrome cookies.

Usage:
    01_scrape_likes.py --username QuocNghi91 --out /tmp/x_likes.json
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", required=True, help="X username without @")
    ap.add_argument("--out", required=True, help="Output JSON path")
    args = ap.parse_args()

    url = f"https://x.com/{args.username}/likes"
    print(f"Scraping {url} via gallery-dl (Chrome cookies)…", file=sys.stderr)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        raw_path = tmp.name

    with open(raw_path, 'w') as out:
        proc = subprocess.run(
            ["gallery-dl", "--cookies-from-browser", "chrome", url, "--dump-json"],
            stdout=out, stderr=subprocess.PIPE, text=True, timeout=900,
        )
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        sys.exit(1)

    with open(raw_path) as f:
        raw = json.load(f)
    print(f"Raw entries: {len(raw)}", file=sys.stderr)

    seen = set()
    likes = []
    for entry in raw:
        meta = next((x for x in entry if isinstance(x, dict)), None)
        if not meta:
            continue
        tid = meta.get("tweet_id") or meta.get("conversation_id")
        if not tid or tid in seen:
            continue
        seen.add(tid)
        author = meta.get("author") or {}
        if isinstance(author, str):
            author = {"name": author}
        likes.append({
            "tweet_id": tid,
            "author": author.get("name", ""),
            "author_nick": author.get("nick", ""),
            "content": meta.get("content", ""),
            "date": str(meta.get("date", "")),
            "favorite_count": meta.get("favorite_count", 0),
            "retweet_count": meta.get("retweet_count", 0),
            "reply_count": meta.get("reply_count", 0),
            "lang": meta.get("lang", ""),
        })

    Path(args.out).write_text(json.dumps(likes, indent=2, ensure_ascii=False))
    print(f"Saved {len(likes)} unique likes to {args.out}", file=sys.stderr)
    Path(raw_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
