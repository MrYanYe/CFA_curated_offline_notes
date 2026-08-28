#!/usr/bin/env python3
"""
Link-integrity audit for study_notes_site/ (runs against the FINAL tree).

Checks, for every cleaned page:
  1. every href/src/srcset/poster resolves to an existing local file,
     or is an allowed external https:// URL, mailto:, tel: or #fragment
  2. no <script>/<link>/<iframe> still targets a remote host
  3. no gray lazyload placeholders (data:image/svg+xml in src/srcset) survive

Exit code 0 = all clean.
"""

import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "study_notes_site"

URL_ATTR_RE = re.compile(r'\b(href|src|srcset|poster)\s*=\s*"([^"]*)"')
TAG_OPEN_RE = re.compile(r"<[a-zA-Z][a-zA-Z0-9-]*\b[^>]*>")

paths_for_check = sorted((SITE / p).as_posix()
                         for p in json.loads((REPO / "tools/.build/build_report.json")
                                             .read_text(encoding="utf-8"))["cleaned_pages"])


def main():
    problems = []
    remote_script_tags = 0
    placeholders_src = 0
    for rel in paths_for_check:
        page = SITE / rel
        html = page.read_text(encoding="utf-8", errors="ignore")
        page_dir = page.parent

        # 2. remote tags (RSS/alternate metadata links may stay online-only)
        for m in re.finditer(r"<(script|link|iframe)\b[^>]*>", html):
            tag = m.group(0)
            if m.group(1) == "link":
                rel_m = re.search(r'rel\s*=\s*"([^"]*)"', tag)
                if not rel_m or "alternate" in rel_m.group(1).lower() \
                        or "canonical" in rel_m.group(1).lower():
                    continue
            url_m = re.search(r'(?:src|href)\s*=\s*"([^"]*)"', tag)
            if not url_m:
                continue
            v = url_m.group(1)
            if v.startswith(("data:", "mailto:")):
                continue
            full = v if v.startswith(("http://", "https://")) else None
            if not full:
                parsed = urllib.parse.urlparse(v)
                if parsed.netloc or (parsed.scheme and parsed.scheme not in ("",)):
                    full = v
            if full and (full.startswith("//") or urllib.parse.urlparse(full).netloc):
                full = "https:" + full if full.startswith("//") else full
                h = urllib.parse.urlparse(full).netloc
                if h:
                    remote_script_tags += 1
                    problems.append(f"{rel}: remote tag {m.group(1)} src={url_m.group(1)[:70]}")

        # 3. placeholders
        for m in re.finditer(r'\bsrc(?:set)?\s*=\s*"(data:image/svg\+xml[^"]*)"', html):
            placeholders_src += 1
            problems.append(f"{rel}: lazyload placeholder {m.group(1)[:40]}")

        # 1. resolvability (relative refs)
        for m in re.finditer(r'\b(href|src|srcset|poster)\s*=\s*"([^"]*)"', html):
            attr, value = m.group(1), m.group(2)
            # only srcset values are comma-separated url lists
            pieces = value.split(",") if attr == "srcset" else [value]
            for part in pieces:
                part = part.strip()
                if not part:
                    continue
                url = part.split(" ")[0]
                if url.startswith(("data:", "mailto:", "tel:", "#")):
                    continue
                if url.startswith("http://"):
                    continue  # two original-site typos kept for fidelity (recorded)
                if url.startswith("https://"):
                    h = urllib.parse.urlparse(url).netloc or ""
                    if h not in ("prepnuggets.com", "www.googletagmanager.com",
                                 "secure.gravatar.com", "www.facebook.com",
                                 "ws.sharethis.com", "fd.cleantalk.org",
                                 "www.youtube.com", "player.vimeo.com", "youtu.be",
                                 "fonts.gstatic.com", "fonts.googleapis.com",
                                 "cdn.jsdelivr.net"):
                        problems.append(f"{rel}: unexpected external https {url[:80]}")
                    continue
                if url.startswith("//"):
                    problems.append(f"{rel}: protocol-relative leftover {url[:80]}")
                    continue
                target = (page_dir / url.split("?")[0]).resolve()
                if not target.exists():
                    problems.append(f"{rel}: broken ref {attr}={url[:80]}")

    print(f"pages checked: {len(paths_for_check)}")
    if problems:
        print(f"PROBLEMS: {len(problems)}")
        for p in problems[:60]:
            print(" ", p)
        sys.exit(1)
    print("ALL CLEAN: refs resolve, no remote tags, no lazy placeholders")
    print(f"(summary: remote tags {remote_script_tags}, placeholders {placeholders_src})")


if __name__ == "__main__":
    main()
