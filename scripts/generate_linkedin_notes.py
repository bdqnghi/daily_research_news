#!/usr/bin/env python3
"""Render the normalized LinkedIn collection without inventing reaction dates.

Usage: python3 scripts/generate_linkedin_notes.py
"""
import argparse
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


def normalized_url(url):
    """Compare research links while retaining original URLs in the notes."""
    p = urlsplit(url)
    host = (p.hostname or "").lower().removeprefix("www.")
    path = p.path.rstrip("/")
    if host in {"arxiv.org", "export.arxiv.org"}:
        match = re.search(r"/(?:abs|pdf|html)/([^?#]+)", path)
        if match:
            paper = re.sub(r"v\d+$", "", match[1].removesuffix(".pdf"))
            return f"arxiv.org/abs/{paper}"
    # Query strings can identify distinct papers, videos, or articles.
    query = parse_qs(p.query)
    for key in list(query):
        if key.startswith("utm_") or key in {"fbclid", "gclid", "rcm", "trk"}:
            del query[key]
    suffix = "&".join(f"{k}={v}" for k in sorted(query) for v in query[k])
    return host + path + ("?" + suffix if suffix else "")


def markdown_text(value):
    return re.sub(r"\s+", " ", value).strip().replace("[", "\\[").replace("]", "\\]")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    root = args.repo.resolve()
    source = root / "LinkedIn"
    data = json.loads((source / "data/liked-posts.json").read_text())
    manifest = json.loads((source / "data/import-status.json").read_text())
    posts = data["posts"]
    ids = [p["id"] for p in posts]
    assert len(ids) == len(set(ids)), "Duplicate LinkedIn records"
    assert all(p["reaction"] == "Like" for p in posts), "Only liked posts belong here"
    assert all(p["summary"] and p["author"] for p in posts)

    x_index = defaultdict(set)
    for path in sorted((root / "X").rglob("*.md")):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", path.name):
            for url in re.findall(r"https?://[^\s)>]+", path.read_text()):
                x_index[normalized_url(url)].add(path)

    groups = defaultdict(list)
    for post in posts:
        # A missing like timestamp always groups by the explicitly labelled import date.
        groups[(post.get("liked_on") or post["observed_on"], bool(post.get("liked_on")))].append(post)

    coverage = []
    total_cross_source = 0
    for (day, has_like_date), day_posts in sorted(groups.items()):
        folder = source / day[:4] / day[5:7]
        folder.mkdir(parents=True, exist_ok=True)
        parts_folder = folder / day
        parts_folder.mkdir(exist_ok=True)
        count = math.ceil(len(day_posts) / 25)
        index = [f"# LinkedIn Likes — {day}", "",
                 f"**{'Reaction date' if has_like_date else 'Import date'}:** {day} · **Posts:** {len(day_posts)}", ""]
        if not has_like_date:
            index += ["These are confirmed post likes observed on this date. LinkedIn did not expose the time of each reaction. The displayed publication ages are preserved; this date is not the date you liked every post.", ""]
        index += ["**Coverage:** Partial 2026 backfill. Earlier likes and exact reaction dates await the requested LinkedIn archive.", "",
                  "## Reading batches", ""]
        for part in range(count):
            batch = day_posts[part * 25:(part + 1) * 25]
            output = parts_folder / f"part-{part + 1:02}.md"
            index.append(f"- [Posts {part * 25 + 1}–{part * 25 + len(batch)}]({day}/{output.name})")
            lines = [f"# LinkedIn Likes — {day} · Part {part + 1}", "",
                     f"[Daily index](../{day}.md) · {'Reaction' if has_like_date else 'Import'} date: {day}", "",
                     "Post summaries reflect what the authors discussed or reported; research claims have not been independently verified.", "",
                     "## Key Topics", ""]
            lines += [f"- **{markdown_text(p['author'])}** — {p['summary']}" for p in batch]
            lines += ["", "---", "", "## Liked Posts", ""]
            for post in batch:
                lines += [f"### {markdown_text(post['author'])}", ""]
                if post.get("post_url"):
                    lines.append(f"[Post]({post['post_url']}) · [Author]({post['author_url']})")
                else:
                    lines.append(f"[Author profile]({post['author_url']}) · Post permalink pending export.")
                lines += ["", post["summary"], "",
                          f"**Published:** {post['published_age']} before collection (LinkedIn display). **Your reaction:** Like.", ""]
                for link in post["external_links"]:
                    lines.append(f"📎 [{markdown_text(link['title'])}]({link['url']})")
                matches = sorted({p for link in post["external_links"] for p in x_index.get(normalized_url(link["url"]), set())})
                if matches:
                    total_cross_source += 1
                    lines += ["", "Also linked in X: " + ", ".join(
                        f"[{p.stem}]({os.path.relpath(p, output.parent)})" for p in matches
                    ) + "."]
                lines += ["", "---", ""]
            output.write_text("\n".join(lines))
        (folder / f"{day}.md").write_text("\n".join(index) + "\n")
        coverage.append((day, len(day_posts), count))

    with_url = sum(bool(p.get("post_url")) for p in posts)
    readme = ["# LinkedIn Research News", "",
              f"**{len(posts)} post summaries** from **{manifest['post_like_observations']} post-like observations** collected on {manifest['observed_on']}, using the topic-and-source format of the X archive.", "",
              "## Read the collection", ""]
    readme += [f"- [{day} import]({day[:4]}/{day[5:7]}/{day}.md) — {n} posts in {parts} reading batches." for day, n, parts in coverage]
    readme += ["", "## Coverage and pending work", "",
               "- Status: **partial 2026 backfill**; this collection is not a complete list of all 2026 likes.",
               "- Observed publication ages range from 6 hours to 3 months, placing the captured posts in 2026. Earlier 2026 history remains unverified.",
               f"- {with_url} post permalinks captured; {len(posts) - with_url} still need reconciliation with the export.",
               "- Exact reaction timestamps were unavailable in the activity view. Notes use the explicitly labelled import date instead.",
               "- One activity item was a like on a comment, rather than a like on the post, and was excluded.",
               "- Two pairs with identical author and content are provisionally grouped. Both capture positions are retained for reconciliation against export URLs.",
               f"- {total_cross_source} posts link to research already referenced in X notes; those notes are cross-linked while preserving LinkedIn provenance.",
               "- Short `lnkd.in` links are retained as observed. Their destination titles have not all been resolved.",
               "- The official LinkedIn data archive was requested on October 24, 2026 (America/Los_Angeles). LinkedIn confirmed the request and estimated about 24 hours. No follow-up automation has been scheduled.",
               "", "LinkedIn documents that the export's Reactions file includes reaction type, date, and post URL: [Download your data](https://www.linkedin.com/help/linkedin/answer/a1339364/).", "",
               "## Finish the backfill", "",
               "When the archive is ready, use its Reactions file to select Like events dated in 2026, reconcile the captured posts, retrieve the remaining posts, and group them by actual reaction date. Other files in the account export are not needed for this research archive.", "",
               "## Regenerate notes", "", "```bash", "python3 scripts/generate_linkedin_notes.py", "```", "",
               "The normalized collection is in `data/liked-posts.json`; import coverage is in `data/import-status.json`. Source snapshots used during processing are outside this archive."]
    (source / "README.md").write_text("\n".join(readme) + "\n")
    print(f"Rendered {len(posts)} LinkedIn posts; {with_url} permalinks; {total_cross_source} cross-source matches.")


if __name__ == "__main__":
    main()
