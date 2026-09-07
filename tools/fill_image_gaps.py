#!/usr/bin/env python3
"""
Targeted image backfill: download every image referenced by the built site
but absent from the mirror (WP lazyload attrs and srcset sizes included).

Reads the authoritative broken-ref list from verify_links.py logic, downloads
each asset (mirror path = site path), retries on transient refusals, and falls
back to the largest existing same-prefix variant + ref rewrite when the exact
file is gone from the origin.

Usage:  python tools/fill_image_gaps.py
"""

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_missing import rewrite_refs_to_existing  # noqa: E402
from fetch_new_pages import download  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SITE = (REPO / "cfa_l1_offline_notes_site_2026").resolve()


def collect_broken():
    found = {}
    for p in SITE.rglob("*.html"):
        if p.relative_to(SITE).parts[0] in ("wp-content", "wp-includes", "wp-json"):
            continue
        html = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'\b(href|src|srcset|poster)\s*=\s*"([^"]*)"', html):
            attr, value = m.group(1), m.group(2)
            pieces = value.split(",") if attr == "srcset" else [value]
            for part in pieces:
                u = part.strip().split(" ")[0].split("?")[0]
                if not u or u.startswith(("data:", "mailto:", "#", "http:/", "https:/", "//")):
                    continue
                rel = Path(u).as_posix()
                target = (p.parent / rel).resolve()
                try:
                    target.relative_to(SITE)
                except ValueError:
                    continue
                if not target.exists():
                    found[target] = True
    return found


def main():
    broken = collect_broken()
    print(f"broken image targets: {len(broken)}")
    ok = fail = fallback = 0
    for target in sorted(broken):
        rel = target.relative_to(SITE).as_posix()
        url = "https://prepnuggets.com/" + rel if rel.startswith("wp-") else "https://" + rel
        if download(url):
            ok += 1
            continue
        # exact file gone from origin: keep trying size variants for a while
        if target.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            if rewrite_refs_to_existing(target, url):
                fallback += 1
                continue
        fail += 1
        print(f"  FAIL {rel} ({url})")
    print(f"downloaded: {ok}, fallback-rewrites: {fallback}, failed: {fail}")


if __name__ == "__main__":
    main()
