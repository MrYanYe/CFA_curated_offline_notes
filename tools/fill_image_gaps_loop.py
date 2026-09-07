#!/usr/bin/env python3
"""
Slow-loop image backfill (rate-limit friendly): repeatedly collects still
missing image refs from the built site and downloads them over time, writing
to BOTH the site tree and the raw mirror, until clean or max_rounds reached.

Usage:  python tools/fill_image_gaps_loop.py [max_rounds]
"""

import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = (REPO / "site_2026").resolve()
MIRROR = (REPO / "raw_mirror").resolve()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

IMGS = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def collect():
    import re
    found = set()
    for p in SITE.rglob("*.html"):
        if p.relative_to(SITE).parts[0] in ("wp-content", "wp-includes", "wp-json",
                                            "cdn.jsdelivr.net", "fonts.googleapis.com",
                                            "fonts.gstatic.com"):
            continue
        html = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'\b(src|srcset|href|poster)\s*=\s*"([^"]*)"', html):
            attr, value = m.group(1), m.group(2)
            pieces = value.split(",") if attr == "srcset" else [value]
            for part in pieces:
                u = part.strip().split(" ")[0].split("?")[0]
                if not u or u.startswith(("data:", "mailto:", "#", "http:/", "https:/", "//")):
                    continue
                t = (p.parent / u).resolve()
                try:
                    t.relative_to(SITE)
                except ValueError:
                    continue
                if not t.exists() and str(t).lower().endswith(IMGS):
                    found.add(t)
    return found


def fetch_one(url: str, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status == 200:
            return r.read()
    return None


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    for rnd in range(1, rounds + 1):
        targets = sorted(collect())
        if not targets:
            print(f"round {rnd}: CLEAN - no missing images")
            return
        print(f"round {rnd}: {len(targets)} missing images")
        ok = 0
        for t in targets:
            rel = t.relative_to(SITE).as_posix()
            url = "https://prepnuggets.com/" + rel
            try:
                data = fetch_one(url)
                if data:
                    t.parent.mkdir(parents=True, exist_ok=True)
                    t.write_bytes(data)
                    m = MIRROR / rel.replace("/", "\\", 0)  # POSIX rel mirrors map
                    mp = MIRROR / rel
                    mp.parent.mkdir(parents=True, exist_ok=True)
                    mp.write_bytes(data)
                    ok += 1
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1.5)
        print(f"round {rnd}: downloaded {ok}/{len(targets)}")
        if ok == 0:
            time.sleep(120)  # cooled down between fruitless rounds
    print("rounds exhausted")


if __name__ == "__main__":
    main()
