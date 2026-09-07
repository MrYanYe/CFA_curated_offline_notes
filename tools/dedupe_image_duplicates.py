#!/usr/bin/env python3
"""
Remove duplicate image instances: on every built page, an <img> whose src
appears for the second time (same file, same size variant) is dropped.

The live origin renders each image exactly once; the raw site dump carried
two instances of every <img> (double logo, double hero, doubled promo cards),
which browsers then show stacked. Keeping the FIRST occurrence matches the
live DOM behavior.

Run standalone (on a finished site tree) or automatically via build_site.py.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site_2026"

IMG_RE = re.compile(r"<img\b[^>]*>", re.S | re.I)
SRC_RE = re.compile(r'(?i)\bsrc="([^"]*)"')


def dedupe_page(html: str) -> str:
    seen = set()

    def sub(m):
        tag = m.group(0)
        src = SRC_RE.search(tag)
        if not src:
            return tag
        value = src.group(1)
        if value.startswith("data:"):  # icons/placeholders: intentional repeats
            return tag
        if value in seen:
            return ""
        seen.add(value)
        return tag

    return IMG_RE.sub(sub, html)


def dedupe_tree(site: Path = SITE) -> int:
    n = 0
    for page in site.rglob("*.html"):
        if page.relative_to(site).parts[0] in ("wp-", "cdn.jsdelivr.net", "fonts."):
            continue
        html = page.read_text(encoding="utf-8", errors="ignore")
        new = dedupe_page(html)
        if new != html:
            page.write_text(new, encoding="utf-8")
            n += 1
    return n


if __name__ == "__main__":
    print("pages de-duplicated:", dedupe_tree())
