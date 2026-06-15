#!/usr/bin/env python3
"""Fetch titles for external URLs found in likes (arxiv via API, others via <title>).

Usage:
    02_fetch_titles.py --likes /tmp/x_likes.json --since 2025-10-14 --out /tmp/url_titles.json
"""
import argparse, json, re, ssl, sys, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

ssl._create_default_https_context = ssl._create_unverified_context
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def collect_urls(likes, cutoff):
    urls = set()
    for l in likes:
        if not l.get("date"):
            continue
        if datetime.strptime(l["date"], "%Y-%m-%d %H:%M:%S") < cutoff:
            continue
        for u in re.findall(r'https?://[^\s\)\]>]+', l["content"]):
            u = u.rstrip('.,;:')
            if 'x.com' in u or 'twitter.com' in u:
                continue
            urls.add(u)
    return urls


def fetch_arxiv_titles(arxiv_urls):
    """Batch-resolve arxiv IDs via export.arxiv.org API."""
    ids = {}
    for u in arxiv_urls:
        m = re.search(r'(\d{4}\.\d{4,5})', u)
        if m:
            ids.setdefault(m.group(1), []).append(u)
    out = {}
    id_list = list(ids.keys())
    for i in range(0, len(id_list), 20):
        batch = id_list[i:i+20]
        query = ','.join(batch)
        try:
            req = urllib.request.Request(
                f"http://export.arxiv.org/api/query?id_list={query}&max_results={len(batch)}",
                headers={"User-Agent": UA})
            xml = urllib.request.urlopen(req, timeout=15).read().decode()
            root = ET.fromstring(xml)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                t = entry.find('atom:title', ns)
                e = entry.find('atom:id', ns)
                if t is not None and e is not None:
                    aid = re.search(r'(\d{4}\.\d{4,5})', e.text)
                    if aid and aid.group(1) in ids:
                        title = ' '.join(t.text.split())
                        for u in ids[aid.group(1)]:
                            out[u] = title
        except Exception as e:
            print(f"  arxiv batch error: {e}", file=sys.stderr)
    return out


def fetch_one(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=8).read(50000).decode('utf-8', errors='ignore')
        m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            title = re.sub(r'\s*[|·–—-]\s*(GitHub|Medium|Substack|YouTube|HuggingFace).*$', '', title)
            return url, title
        m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if m:
            return url, m.group(1).strip()
    except Exception:
        pass
    return url, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--likes", required=True)
    ap.add_argument("--since", required=True, help="YYYY-MM-DD cutoff")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cutoff = datetime.strptime(args.since, "%Y-%m-%d")
    with open(args.likes) as f:
        likes = json.load(f)

    urls = collect_urls(likes, cutoff)
    print(f"Unique external URLs: {len(urls)}", file=sys.stderr)

    arxiv = {u for u in urls if 'arxiv.org' in u}
    other = urls - arxiv

    titles = fetch_arxiv_titles(arxiv)
    print(f"Arxiv resolved: {len(titles)}/{len(arxiv)}", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=15) as pool:
        for fut in as_completed([pool.submit(fetch_one, u) for u in other]):
            u, t = fut.result()
            if t and 3 < len(t) < 200:
                titles[u] = t

    print(f"Total resolved: {len(titles)}/{len(urls)}", file=sys.stderr)
    with open(args.out, 'w') as f:
        json.dump(titles, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
