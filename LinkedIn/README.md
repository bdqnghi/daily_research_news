# LinkedIn Research News

**427 post summaries** from **429 post-like observations** collected on 2026-10-24, using the topic-and-source format of the X archive.

## Read the collection

- [2026-10-24 import](2026/10/2026-10-24.md) — 427 posts in 18 reading batches.

## Coverage and pending work

- Status: **partial 2026 backfill**; this collection is not a complete list of all 2026 likes.
- Observed publication ages range from 6 hours to 3 months, placing the captured posts in 2026. Earlier 2026 history remains unverified.
- 50 post permalinks captured; 377 still need reconciliation with the export.
- Exact reaction timestamps were unavailable in the activity view. Notes use the explicitly labelled import date instead.
- One activity item was a like on a comment, rather than a like on the post, and was excluded.
- Two pairs with identical author and content are provisionally grouped. Both capture positions are retained for reconciliation against export URLs.
- 19 posts link to research already referenced in X notes; those notes are cross-linked while preserving LinkedIn provenance.
- Short `lnkd.in` links are retained as observed. Their destination titles have not all been resolved.
- The official LinkedIn data archive was requested on October 24, 2026 (America/Los_Angeles). LinkedIn confirmed the request and estimated about 24 hours. No follow-up automation has been scheduled.

LinkedIn documents that the export's Reactions file includes reaction type, date, and post URL: [Download your data](https://www.linkedin.com/help/linkedin/answer/a1339364/).

## Finish the backfill

When the archive is ready, use its Reactions file to select Like events dated in 2026, reconcile the captured posts, retrieve the remaining posts, and group them by actual reaction date. Other files in the account export are not needed for this research archive.

## Regenerate notes

```bash
python3 scripts/generate_linkedin_notes.py
```

The normalized collection is in `data/liked-posts.json`; import coverage is in `data/import-status.json`. Source snapshots used during processing are outside this archive.
