#!/usr/bin/env python3
"""Generate daily markdown notes from likes + titles + article contents.

Usage:
    04_generate_notes.py --likes /tmp/x_likes.json --titles /tmp/url_titles.json \
        --articles /tmp/article_contents.json --since 2025-10-14 \
        --vault-dir "/Users/me/Documents/Obsidian/Personal/X"
"""
import argparse, json, re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

X_ARTICLE_RE = re.compile(r'^https?://(x|twitter)\.com/i/article/\d+$')
X_LINK_RE = re.compile(r'https?://(x|twitter)\.com/\S+')


def extract_urls(text):
    urls = re.findall(r'https?://[^\s\)\]>]+', text)
    for a in re.findall(r'arxiv\.?\s*org/abs/[\d.]+', text):
        clean = "https://" + a.replace(" ", "")
        if clean not in urls:
            urls.append(clean)
    external, seen = [], set()
    for u in urls:
        u = u.rstrip('.,;:')
        if 'x.com' in u or 'twitter.com' in u:
            continue
        norm = re.sub(r'^https?://', '', u).rstrip('/')
        if norm in seen:
            continue
        seen.add(norm)
        external.append(u)
    return external


def label_url(url):
    if 'arxiv.org' in url: return 'Paper'
    if 'github.com' in url: return 'GitHub'
    if any(x in url for x in ['blog', 'medium.com', 'substack', 'hashnode']): return 'Blog'
    if any(x in url for x in ['youtube.com', 'youtu.be']): return 'Video'
    if 'huggingface.co' in url: return 'HuggingFace'
    return 'Link'


def is_article_only(content):
    return bool(X_ARTICLE_RE.match(content.strip()))


def clean_content(content):
    c = X_LINK_RE.sub('', content).strip()
    return re.sub(r'\n{3,}', '\n\n', c)


def get_article_url(content):
    m = re.search(r'https?://(x|twitter)\.com/i/article/\d+', content)
    return m.group(0) if m else None


def summarize_topic(content):
    cleaned = clean_content(content)
    if len(cleaned) < 10:
        return None
    best = []
    for line in cleaned.split('\n'):
        line = line.strip()
        if not line:
            continue
        if len(re.sub(r'#\w+', '', line).strip()) < 15:
            continue
        alpha = sum(1 for c in line if c.isalpha()) / max(len(line), 1)
        if alpha < 0.3:
            continue
        best.append(line)
        if len(' '.join(best)) > 150:
            break
    if not best:
        return None
    s = ' '.join(best)
    return s[:147] + "..." if len(s) > 150 else s


def generate_note(day, day_likes, url_titles, articles):
    lines = [f"# X Likes — {day}\n", "## Key Topics"]
    for l in day_likes:
        author = l['author']
        content = l['content']
        if is_article_only(content):
            art = articles.get(str(l['tweet_id']), {})
            title = art.get("title", "")
            lines.append(f"- **@{author}** — {title}" if title else f"- **@{author}** — X Article (long-form post)")
            continue
        summary = summarize_topic(content)
        lines.append(f"- **@{author}** — {summary}" if summary else f"- **@{author}** — (media/short post)")

    lines.append("\n---\n## Liked Tweets\n")

    for l in day_likes:
        author = l['author']
        nick = l['author_nick'] or author
        tid = l['tweet_id']
        content = l['content'].strip()
        tweet_url = f"https://x.com/{author}/status/{tid}"

        lines.append(f"### @{author} ({nick})")
        lines.append(f"[Tweet]({tweet_url})\n")

        if is_article_only(content):
            art_url = get_article_url(content)
            art = articles.get(str(tid), {})
            title, excerpt = art.get("title", ""), art.get("excerpt", "")
            if title:
                lines.append(f"**{title}**\n")
                if excerpt:
                    display = excerpt[:400] + ("..." if len(excerpt) > 400 else "")
                    display = display.replace('\n', '\n> ')
                    lines.append(f"> {display}\n")
            else:
                lines.append(f"> 📄 X Article (long-form post)\n")
            if art_url:
                lines.append(f"📎 [{title or 'X Article'}]({art_url})\n")
        else:
            display = clean_content(content)
            if len(display) > 400:
                display = display[:397] + "..."
            display = display.replace('\n', '\n> ')
            lines.append(f"> {display}\n")

            ext = extract_urls(content)
            if ext:
                for u in ext:
                    title = url_titles.get(u)
                    if title:
                        lines.append(f"📎 [{title}]({u})")
                    else:
                        short = re.sub(r'^https?://(www\.)?', '', u)
                        lines.append(f"📎 [{label_url(u)}: {short}]({u})")
                lines.append("")

        lines.append(f"❤️ {l['favorite_count']} | 🔁 {l['retweet_count']}\n")
        lines.append("---\n")
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--likes", required=True)
    ap.add_argument("--titles", required=True)
    ap.add_argument("--articles", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--vault-dir", required=True)
    args = ap.parse_args()

    cutoff = datetime.strptime(args.since, "%Y-%m-%d")
    with open(args.likes) as f:
        likes = json.load(f)
    with open(args.titles) as f:
        url_titles = json.load(f)
    with open(args.articles) as f:
        articles = json.load(f)

    by_day = defaultdict(list)
    for l in likes:
        if not l.get("date"):
            continue
        if datetime.strptime(l["date"], "%Y-%m-%d %H:%M:%S") < cutoff:
            continue
        by_day[l["date"][:10]].append(l)

    vault = Path(args.vault_dir)
    vault.mkdir(parents=True, exist_ok=True)
    count = 0
    for day in sorted(by_day.keys()):
        note = generate_note(day, by_day[day], url_titles, articles)
        year, month = day[:4], day[5:7]
        out_dir = vault / year / month
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{day}.md").write_text(note, encoding='utf-8')
        count += 1
    print(f"Wrote {count} notes to {vault}")


if __name__ == "__main__":
    main()
