#!/usr/bin/env python3
"""Audit the archive against a fresh scrape: find days that are missing
entirely, and days whose note is missing some of that day's likes.

This catches the "evening likes" failure mode — likes added late on day D
after a sync that day, which a next-day sync starting from D+1 never revisits.

Usage:
    audit.py --likes /tmp/x_likes.json --repo /path/to/daily_research_news
    audit.py --likes /tmp/x_likes.json --repo . --write-affected /tmp/affected_days.json

Exit code is 1 if gaps were found, 0 otherwise — so it can gate CI.
"""
import argparse, glob, json, os, re, sys
from collections import defaultdict

ARCHIVE_START = "2025-10-12"  # nothing before this was ever imported


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--likes", required=True, help="Scraped likes JSON (from 01_scrape_likes.py)")
    ap.add_argument("--repo", required=True, help="Repo root containing YYYY/MM/*.md")
    ap.add_argument("--since", default=ARCHIVE_START)
    ap.add_argument("--write-affected", help="Write the affected-day list here as a JSON array")
    args = ap.parse_args()

    with open(args.likes) as f:
        likes = json.load(f)

    scraped = defaultdict(set)
    for l in likes:
        day = (l.get("date") or "")[:10]
        if day >= args.since:
            scraped[day].add(str(l["tweet_id"]))

    in_repo, have_file = defaultdict(set), set()
    for path in glob.glob(os.path.join(args.repo, "20*/*/*.md")):
        day = os.path.basename(path)[:-3]
        have_file.add(day)
        with open(path) as f:
            in_repo[day] = set(re.findall(r"/status/(\d+)", f.read()))

    missing_day, incomplete = [], []
    for day in sorted(scraped):
        gap = scraped[day] - in_repo[day]
        if not gap:
            continue
        (missing_day if day not in have_file else incomplete).append(
            (day, len(in_repo[day]), len(scraped[day]), len(gap))
        )

    total = sum(g for *_, g in missing_day + incomplete)
    if not total:
        print(f"✓ archive complete — {len(have_file)} day-notes, no gaps since {args.since}")
        return 0

    if missing_day:
        print(f"=== NO NOTE AT ALL ({len(missing_day)} days) ===")
        for day, _, s, _ in missing_day:
            print(f"  {day}: {s} likes, no note")
    if incomplete:
        print(f"=== NOTE EXISTS BUT INCOMPLETE ({len(incomplete)} days) ===")
        for day, r, s, g in incomplete:
            print(f"  {day}: repo {r} → scrape {s}  (+{g})")
    print(f"\nTOTAL MISSING LIKES: {total}")

    affected = sorted(d for d, *_ in missing_day + incomplete)
    if args.write_affected:
        with open(args.write_affected, "w") as f:
            json.dump(affected, f)
        print(f"affected days → {args.write_affected}")
    print("\nBackfill with:")
    print(f"  04_generate_notes.py --likes {args.likes} --titles <titles.json> "
          f"--articles <articles.json> --since {args.since} "
          f"--only-days {args.write_affected or '<day,day,...>'} --vault-dir {args.repo}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
