#!/usr/bin/env python3
"""
Backfill crawler: fetch assets referenced by the cleaned site but absent from
the raw mirror, from the live site.

Usage:
  python tools/fetch_missing.py [--report tools/.build/build_report.json]

Falls back per image derivative: if <name>-WxH.ext cannot be fetched, try the
base <name>.ext / smaller derivatives, and finally rewrite the site's
references to the closest existing file, so no image stays grey.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "cfa_l1_offline_notes_site_2026"
BUILD = REPO / "tools" / ".build"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def fetch(url: str, dest: Path, timeout=30) -> str:
    """Download url into dest. Returns 'ok' | 'http-<code>' | 'error'."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if resp.status != 200:
                return f"http-{resp.status}"
            dest.write_bytes(data)
            return "ok"
    except Exception as e:  # noqa: BLE001 - report any failure verbatim
        return f"error {type(e).__name__}"


def size_candidates(url: str):
    """For a wp image derivative https://.../name-1184x646.jpg yield candidate urls."""
    parts = urllib.parse.urlsplit(url)
    m = re.match(r"^(.+)-(\d+)x(\d+)(\.[A-Za-z0-9]+)$", parts.path)
    if not m:
        return [url]
    base, w, h, ext = m.groups()
    full_base = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, f"{base}{ext}", parts.query, parts.fragment))
    return [url, full_base]


def rewrite_refs_to_existing(local: Path, full: str) -> bool:
    """All fetch attempts failed: point page references at the closest existing file.

    Tries <name>.ext and smaller derivatives already present under SITE; rewrites
    every cleaned page reference to that file name. Returns True if a fallback
    target was found and rewrites applied.
    """
    missing_name = local.name
    m = re.match(r"^(.+)-(\d+)x(\d+)(\.[A-Za-z0-9]+)$", missing_name)
    if m:
        base, w, h, ext = m.groups()
    else:
        stem, ext = os.path.splitext(missing_name)
        base = stem  # base-name image: fall back to its largest size variant
    pattern = f"{base}*{ext or os.path.splitext(missing_name)[1]}"
    siblings = [p for p in local.parent.glob(pattern) if p.is_file()] if local.parent.exists() \
        else [p for p in SITE.rglob(pattern) if p.is_file()]
    if not siblings:
        return False
    fallback = max(siblings, key=lambda p: p.stat().st_size)
    fallback_name = fallback.name
    n = 0
    for page in SITE.rglob("*.html"):
        html = page.read_text(encoding="utf-8", errors="ignore")
        if missing_name in html:
            html = html.replace(missing_name, fallback_name)
            page.write_text(html, encoding="utf-8")
            n += 1
    print(f"ref rewrite: {missing_name} -> {fallback_name} in {n} pages")
    return True


def main():
    report_path = Path(sys.argv[sys.argv.index("--report") + 1]) if "--report" in sys.argv \
        else BUILD / "build_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    missing = report["assets_missing_from_mirror"]
    if not missing:
        print("no missing assets to fetch")
        return

    ok = failed = rewrite_used = 0
    for local, full in missing:
        dest = Path(local)
        attempts = size_candidates(full) if dest.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") \
            else [full]
        status = None
        for cand in attempts:
            status = fetch(cand, dest)
            if status == "ok":
                ok += 1
                print(f"fetch ok   {full}  ->  {local}")
                break
        if status != "ok":
            if rewrite_refs_to_existing(dest, full):
                rewrite_used += 1
            else:
                failed += 1
                print(f"fetch FAIL {full} ({status})  ->  {local}")

    print(f"fetched ok: {ok}, ref-rewrite: {rewrite_used}, failed: {failed}")


if __name__ == "__main__":
    main()
