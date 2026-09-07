#!/usr/bin/env python3
"""
Incremental crawl: add pages that exist on the live site but are missing from
the raw mirror, plus every asset those pages reference.

Discovers missing pages via the public WP REST API (per-page modified times
make it easy to confirm freshness), downloads each missing page and its
referenced local assets into raw_mirror/, then the normal
build_site.py pipeline picks them up automatically.

Usage:  python tools/fetch_new_pages.py
"""

import json
import re
import time as time_mod
import urllib.parse
from pathlib import Path

from scrapling.fetchers import Fetcher

REPO = Path(__file__).resolve().parent.parent
MIRROR = REPO / "raw_mirror"
SITE = REPO / "cfa_l1_offline_notes_site_2026"
BUILD = REPO / "tools" / ".build"

CROSS_DOMAINS = ("cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com")
ASSET_EXTS = re.compile(r"\.(png|jpe?g|gif|svg|webp|woff2?|ttf|otf|eot|pdf|ico|css|js|json|mp4|webm)$",
                        re.I)

JSON_HEADERS = {"Accept": "application/json"}
HTML_HEADERS = {"Accept": "text/html,*/*;q=0.8"}

REQUEST_DELAY = 0.6  # s between requests - stay polite with the origin


def rget(url: str, headers=None, timeout=60):
    """GET via scrapling Fetcher (browser-grade TLS fingerprint)."""
    r = Fetcher.get(url, headers=headers, impersonate="chrome", timeout=timeout)
    time_mod.sleep(REQUEST_DELAY)
    return r.status, (r.body if isinstance(r.body, bytes) else
                      str(r.body or "").encode("utf-8", errors="ignore"))


def rest_pages():
    pages = []
    for i in range(1, 12):
        url = (f"https://prepnuggets.com/wp-json/wp/v2/pages?per_page=100&page={i}"
               f"&_fields=id,slug,link,modified,title&status=publish")
        data = None
        for attempt in range(3):  # transient rate-limit / timeout retry
            try:
                _, body = rget(url, JSON_HEADERS, timeout=60)
                data = json.loads(body.decode("utf-8", errors="ignore"))
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    print(f"  REST page {i} failed after retries: {type(e).__name__}")
                    return pages
        if not isinstance(data, list):
            break
        pages += data
        if len(data) < 100:
            break
    return pages


def notes_slug(link: str):
    m = re.search(r"cfa-level-1-study-notes/(.*)", link.rstrip("/"))
    return m.group(1).strip("/") if m else None


def mirror_target_for(url: str) -> Path | None:
    """Absolute asset/page URL -> its path inside the raw mirror (or None).

    Matches the mirror's convention: a page URL (trailing slash or no file
    extension) maps to <path>/index.html; resources keep their file names.
    """
    p = urllib.parse.urlparse(url)
    path = p.path.split("?")[0]
    if not path:
        return None
    ext = Path(path).suffix
    if ext == "":  # page-style URL -> index.html
        path = path.rstrip("/") + "/index.html"
    if p.netloc == "prepnuggets.com":
        return MIRROR / "prepnuggets.com" / path.lstrip("/")
    if p.netloc in CROSS_DOMAINS:
        return MIRROR / p.netloc / path.lstrip("/")
    return None


def download(url: str):
    target = mirror_target_for(url)
    if target is None or (target.exists() and target.stat().st_size > 0):
        return None
    try:
        status, body = rget(url)
        if status != 200 or not body:
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        return target
    except Exception:
        return None


# pages outside /cfa-level-1-study-notes/ that the live site links to from the
# notes homepage (added to the mirror + built as content pages)
EXTRA_PAGES = ("2027-cfa-level-i-updates", "quantitative-methods")


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    local = {p.relative_to(SITE).as_posix()[:-len("/index.html")].strip("/")
             for p in SITE.rglob("index.html")
             if p.relative_to(SITE).parts[0] not in
             ("wp-content", "wp-includes", "wp-json", "cdn.jsdelivr.net",
              "fonts.googleapis.com", "fonts.gstatic.com")}
    local.discard("")

    rest = rest_pages()
    notes = {notes_slug(p["link"]): p for p in rest if notes_slug(p["link"])}
    missing = sorted(set(notes) - local)
    print(f"REST pages under /cfa-level-1-study-notes: {len(notes)}; "
          f"locally present: {local and len(local)}; missing: {len(missing)}")

    def scan_and_download(html: str):
        """Download every asset a page references (lazyload attrs included)."""
        used = set()
        for m in re.finditer(
                r'(?:src|href|srcset|poster|content|data-lazy-src|data-lazy-srcset|data-src)="([^"]+)"',
                html):
            for part in m.group(1).split(","):
                u = part.strip().split(" ")[0].split("?")[0]
                if u.startswith(("//", "http:/", "https:/")) \
                        and not u.startswith("//www.youtube.com") \
                        and ASSET_EXTS.search(u):
                    full = u if u.startswith("http") else "https:" + u
                    if full not in used:
                        used.add(full)
        new = 0
        for u in sorted(used):
            if download(u):
                new += 1
        return new, len(used)

    def fetch_page(slug: str, base_path: str):
        """Fetch one page + its referenced assets into the mirror.

        Existing pages are not re-downloaded, but their assets are still
        scanned (freshly mirrored pages referenced images via data-lazy-src).
        """
        nonlocal fetched, assets
        url = f"https://prepnuggets.com/{base_path}/{slug}/" if base_path \
            else f"https://prepnuggets.com/{slug}/"
        raw = mirror_target_for(url) or MIRROR / "prepnuggets.com" / \
            f"{base_path}/{slug}/index.html"
        if raw.exists() and raw.stat().st_size > 1000:
            new, n = scan_and_download(raw.read_text(encoding="utf-8", errors="ignore"))
            assets += new
            if new:
                print(f"  +{new} more assets for existing page {slug}")
            return False
        try:
            status, body = rget(url)
        except Exception as e:  # noqa: BLE001
            print(f"  page FAIL {slug}: {type(e).__name__}")
            return False
        if status != 200:
            print(f"  page HTTP {status}: {slug}")
            return False
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(body)
        print(f"  fetched page {slug}")
        new, n = scan_and_download(body.decode("utf-8", errors="ignore"))
        assets += new
        print(f"    +{n} referenced urls, {new} new assets")
        return True

    fetched, assets, skipped = 0, 0, 0
    # scan/re-fetch every known page: existing pages are kept but their
    # asset references (incl. lazyload attrs) are (re)scanned for gaps
    for slug in sorted(notes):
        if fetch_page(slug, "cfa-level-1-study-notes"):
            fetched += 1
        else:
            skipped += 1
    for slug in EXTRA_PAGES:
        if fetch_page(slug, ""):  # top-level URL: https://prepnuggets.com/<slug>/
            fetched += 1

    print(f"done: {fetched} pages fetched, {assets} assets downloaded")
    (BUILD / "fetch_new_pages.json").write_text(
        json.dumps({"pages": len(missing), "fetched": fetched, "assets": assets,
                    "missing": missing}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
