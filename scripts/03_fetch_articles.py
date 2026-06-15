#!/usr/bin/env python3
"""Fetch X Article (long-form) content via Playwright + Chrome cookies.

Usage:
    03_fetch_articles.py --likes /tmp/x_likes.json --since 2025-10-14 --out /tmp/article_contents.json
"""
import argparse, json, re, sys, time
from datetime import datetime

ARTICLE_RE = re.compile(r'^https?://(x|twitter)\.com/i/article/(\d+)$')


def collect_articles(likes, cutoff):
    out = []
    for l in likes:
        if not l.get("date"):
            continue
        if datetime.strptime(l["date"], "%Y-%m-%d %H:%M:%S") < cutoff:
            continue
        m = ARTICLE_RE.match(l["content"].strip())
        if m:
            out.append({
                "tweet_id": str(l["tweet_id"]),
                "author": l["author"],
                "article_url": l["content"].strip(),
            })
    return out


def extract_article_text(body):
    """Strip X chrome from the body text and return (title, excerpt)."""
    lines = [x.strip() for x in body.split('\n') if x.strip()]
    skip = {'Home', 'Explore', 'Search', 'Notifications', 'Messages', 'Premium', 'Profile',
            'More', 'Post', 'Follow', 'View keyboard shortcuts',
            'To view keyboard shortcuts, press question mark'}
    content = []
    for line in lines:
        if line in skip:
            continue
        if re.match(r'^@\w+$', line) or line == '·':
            continue
        if re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+', line):
            continue
        if re.match(r'^\d+(\.\d+)?[KMB]?$', line):
            continue
        if len(line) < 3:
            continue
        content.append(line)
    title = content[0] if content else ""
    excerpt = '\n'.join(content[1:])[:800] if len(content) > 1 else ""
    return title, excerpt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--likes", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import browser_cookie3
    from playwright.sync_api import sync_playwright

    cutoff = datetime.strptime(args.since, "%Y-%m-%d")
    with open(args.likes) as f:
        likes = json.load(f)
    articles = collect_articles(likes, cutoff)
    print(f"Articles to fetch: {len(articles)}", file=sys.stderr)

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        cj = browser_cookie3.chrome(domain_name=".x.com")
        cookies = [{"name": c.name, "value": c.value, "domain": c.domain, "path": c.path or "/"}
                   for c in cj if c.domain and c.value]
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        for i, art in enumerate(articles):
            try:
                page.goto(art["article_url"], wait_until="domcontentloaded", timeout=15000)
                time.sleep(4)
                body = page.inner_text("body")
                title, excerpt = extract_article_text(body)
                results[art["tweet_id"]] = {"title": title, "excerpt": excerpt, "full_length": len(body)}
                print(f"  [{i+1}/{len(articles)}] @{art['author']}: {title[:80]}", file=sys.stderr)
            except Exception as e:
                results[art["tweet_id"]] = {"title": "", "excerpt": "", "full_length": 0}
                print(f"  [{i+1}/{len(articles)}] @{art['author']} ERROR: {e}", file=sys.stderr)
        browser.close()

    with open(args.out, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    hit = sum(1 for v in results.values() if v["title"])
    print(f"Fetched {hit}/{len(articles)} article titles", file=sys.stderr)


if __name__ == "__main__":
    main()
