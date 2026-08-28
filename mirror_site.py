#!/usr/bin/env python3
"""
Recursive website mirroring script.
Downloads all pages, CSS, JS, fonts, and images recursively,
rewriting links for offline browsing.

Usage: python mirror_site.py
"""

import os
import re
import sys
import time
import hashlib
import urllib.parse
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# ========== CONFIGURATION ==========
SEED_URL = "https://freefellow.org/free/cfa-level-1/"
OUTPUT_DIR = Path("d:/Project/aaa_temp/CFA_Notes/offline_site")

# Only crawl (follow links from) pages whose URL path starts with one of these
CRAWL_PATH_PREFIXES = [
    "/free/cfa-level-1/",    # Main CFA Level 1 content
    "/blog/",                 # Blog posts linked from CFA Level 1 pages
    "/founder/",              # About the founder
    "/cfa/",                  # CFA overview page
]

# Exact paths to crawl (no subpath match — avoids matching /free/everything)
CRAWL_EXACT_PATHS = [
    "/free/",                 # Free practice index page
]

# Asset paths — downloaded but not crawled for links
ASSET_PATH_PREFIXES = [
    "/free/",                 # Shared CSS/JS in /free/ (styles.css, questions.js)
    "/favicon.svg",
    "/quiz-island.js",
    "/utm-forward.js",
    "/_vercel/",
    "/og-images/",
]

# External CDN hosts to download for full offline use
DOWNLOAD_EXTERNAL = True
EXTERNAL_HOSTS = [
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
]

DELAY_SECONDS = 0.3
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WebsiteMirror/1.0)"
}

ASSET_EXTENSIONS = {".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico",
                    ".woff", ".woff2", ".ttf", ".eot", ".pdf", ".xml", ".json",
                    ".webp", ".mp4", ".webm"}

TIMEOUT = 30

# ========== GLOBAL STATE ==========
visited_urls = set()
url_to_local_path = {}
failed_urls = {}
session = requests.Session()
session.headers.update(HEADERS)


def normalize_url(url: str, base_url: str) -> str:
    """Resolve relative URLs, strip fragments, and normalize."""
    full = urllib.parse.urljoin(base_url, url)
    parsed = urllib.parse.urlparse(full)
    clean = urllib.parse.urlunparse(parsed._replace(fragment=""))
    return clean


def should_crawl(url: str) -> bool:
    """Check if this page URL should be crawled for further links."""
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc and parsed.netloc != "freefellow.org":
        return False

    path = parsed.path or "/"

    # Don't crawl asset files
    ext = os.path.splitext(path)[1].lower()
    if ext and ext in ASSET_EXTENSIONS:
        return False

    # Exact path match first
    for exact in CRAWL_EXACT_PATHS:
        if path == exact or path == exact.rstrip("/"):
            return True

    # Prefix match
    for prefix in CRAWL_PATH_PREFIXES:
        if path.startswith(prefix):
            return True

    return False


def should_download(url: str) -> bool:
    """Check if this URL should be downloaded at all."""
    parsed = urllib.parse.urlparse(url)

    # Same domain
    if not parsed.netloc or parsed.netloc == "freefellow.org":
        path = parsed.path or "/"

        # Exact path match
        for exact in CRAWL_EXACT_PATHS:
            if path == exact or path == exact.rstrip("/"):
                return True

        # Crawl prefix match
        for prefix in CRAWL_PATH_PREFIXES:
            if path.startswith(prefix):
                return True

        # Asset prefix match
        for prefix in ASSET_PATH_PREFIXES:
            if path.startswith(prefix):
                return True

        return False

    # External hosts
    if DOWNLOAD_EXTERNAL:
        for host in EXTERNAL_HOSTS:
            if parsed.netloc == host or parsed.netloc.endswith("." + host):
                return True

    return False


def url_to_local_filepath(url: str) -> Path:
    """Convert a URL to a local file path under OUTPUT_DIR."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc or "freefellow.org"
    path = parsed.path or "/"

    local = OUTPUT_DIR / host / path.lstrip("/")

    if path.endswith("/") or not os.path.splitext(path)[1]:
        local = local / "index.html"

    return local


def download_file(url: str) -> tuple:
    """Download a URL. Returns (content_bytes, error_string)."""
    try:
        time.sleep(DELAY_SECONDS)
        resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        return resp.content, None
    except requests.RequestException as e:
        return None, str(e)


def extract_links(html: bytes, base_url: str) -> dict:
    """Extract and categorize all links from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = {
        "pages": [],
        "styles": [],
        "scripts": [],
        "images": [],
        "fonts": [],
        "other": [],
    }

    for tag in soup.find_all("a", href=True):
        links["pages"].append(normalize_url(tag["href"], base_url))

    for tag in soup.find_all("link", href=True):
        url = normalize_url(tag["href"], base_url)
        rel = tag.get("rel", [])
        if isinstance(rel, list):
            rel = " ".join(rel)
        if "icon" in rel:
            links["images"].append(url)
        else:
            links["styles"].append(url)

    for tag in soup.find_all("script", src=True):
        links["scripts"].append(normalize_url(tag["src"], base_url))

    for tag in soup.find_all("img", src=True):
        links["images"].append(normalize_url(tag["src"], base_url))

    for tag in soup.find_all("source", src=True):
        links["images"].append(normalize_url(tag["src"], base_url))

    for tag in soup.find_all("video", src=True):
        links["images"].append(normalize_url(tag["src"], base_url))
    for tag in soup.find_all("video", poster=True):
        links["images"].append(normalize_url(tag["poster"], base_url))

    for tag in soup.find_all("style"):
        if tag.string:
            urls = re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', tag.string)
            for u in urls:
                links["fonts"].append(normalize_url(u, base_url))

    for tag in soup.find_all(attrs={"srcset": True}):
        for part in tag["srcset"].split(","):
            part = part.strip().split()[0] if part.strip() else ""
            if part:
                links["images"].append(normalize_url(part, base_url))

    return links


def make_relative_path(from_file: Path, to_file: Path) -> str:
    """Compute a relative path from one local file to another.
    Uses POSIX separators for cross-platform compatibility."""
    try:
        rel = os.path.relpath(to_file, from_file.parent)
        return rel.replace("\\", "/")
    except ValueError:
        # Different drives on Windows — fall back to root-relative
        return "/" + str(to_file.relative_to(OUTPUT_DIR)).replace("\\", "/")


def rewrite_html(html: bytes, base_url: str, page_local_path: Path) -> bytes:
    """Rewrite URLs in HTML to point to local files using relative paths."""
    soup = BeautifulSoup(html, "html.parser")

    def local_href(url: str):
        full = normalize_url(url, base_url)
        if full in url_to_local_path:
            return make_relative_path(page_local_path, url_to_local_path[full])
        return None

    for tag in soup.find_all("a", href=True):
        new = local_href(tag["href"])
        if new:
            tag["href"] = new

    for tag in soup.find_all("link", href=True):
        new = local_href(tag["href"])
        if new:
            tag["href"] = new

    for tag in soup.find_all("script", src=True):
        new = local_href(tag["src"])
        if new:
            tag["src"] = new

    for tag in soup.find_all("img", src=True):
        new = local_href(tag["src"])
        if new:
            tag["src"] = new

    for tag in soup.find_all("source", src=True):
        new = local_href(tag["src"])
        if new:
            tag["src"] = new

    return str(soup).encode("utf-8")


def rewrite_css(css_bytes: bytes, css_url: str, css_local_path: Path) -> bytes:
    """Rewrite url() references in CSS to point to local files."""
    try:
        css_text = css_bytes.decode("utf-8", errors="replace")
    except Exception:
        return css_bytes

    def replace_url(match):
        inner = match.group(1).strip()
        quote = ""
        url_part = inner
        if inner.startswith('"') and inner.endswith('"'):
            url_part = inner[1:-1]
            quote = '"'
        elif inner.startswith("'") and inner.endswith("'"):
            url_part = inner[1:-1]
            quote = "'"

        full_url = normalize_url(url_part, css_url)
        if full_url in url_to_local_path:
            local = make_relative_path(css_local_path, url_to_local_path[full_url])
            return f'url({quote}{local}{quote})'
        return match.group(0)

    css_text = re.sub(r'url\(([^)]+)\)', replace_url, css_text)
    return css_text.encode("utf-8")


def download_asset(url: str):
    """Download a non-HTML asset and save it."""
    if url in visited_urls:
        return
    visited_urls.add(url)

    print(f"  [ASSET] {url}")
    content, error = download_file(url)

    if error:
        print(f"          FAILED: {error}")
        failed_urls[url] = error
        return

    local_path = url_to_local_filepath(url)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    ext = os.path.splitext(local_path.name)[1].lower()
    if ext == ".css":
        content = rewrite_css(content, url, local_path)

    local_path.write_bytes(content)
    url_to_local_path[url] = local_path


def process_page(url: str, content: bytes) -> list:
    """Process a downloaded HTML page and return new page URLs to crawl."""
    links = extract_links(content, url)

    # Download all referenced assets
    all_asset_urls = set(links["styles"] + links["scripts"] + links["images"] +
                         links["fonts"] + links["other"])
    for asset_url in all_asset_urls:
        if should_download(asset_url) and asset_url not in visited_urls:
            download_asset(asset_url)

    # Download fonts referenced from within downloaded CSS
    for css_url in set(links["styles"]):
        if css_url in url_to_local_path:
            css_path = url_to_local_path[css_url]
            if css_path.exists():
                try:
                    css_text = css_path.read_text(encoding="utf-8", errors="replace")
                    font_urls = re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', css_text)
                    for fu in font_urls:
                        full_fu = normalize_url(fu, css_url)
                        if should_download(full_fu) and full_fu not in visited_urls:
                            download_asset(full_fu)
                except Exception:
                    pass

    # Rewrite and save HTML
    local_path = url_to_local_filepath(url)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    rewritten = rewrite_html(content, url, local_path)
    local_path.write_bytes(rewritten)
    url_to_local_path[url] = local_path

    # Return new page links to crawl
    new_pages = []
    for page_url in set(links["pages"]):
        if page_url not in visited_urls and should_crawl(page_url):
            new_pages.append(page_url)

    return new_pages


def crawl():
    """Main crawl loop."""
    print("=" * 70)
    print(f"Mirroring: {SEED_URL}")
    print(f"Output:    {OUTPUT_DIR}")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    to_crawl = [SEED_URL]
    page_count = 0

    while to_crawl:
        url = to_crawl.pop(0)

        if url in visited_urls:
            continue

        print(f"\n  [PAGE {page_count + 1}] {url}")
        visited_urls.add(url)

        content, error = download_file(url)

        if error:
            print(f"          FAILED: {error}")
            failed_urls[url] = error
            continue

        new_pages = process_page(url, content)
        page_count += 1

        local = url_to_local_path.get(url, Path("?"))
        relative = local.relative_to(OUTPUT_DIR) if local != Path("?") else "?"
        print(f"          -> {relative}")

        for p in new_pages:
            if p not in visited_urls and p not in to_crawl:
                to_crawl.append(p)

        print(f"          Queue: {len(to_crawl)} pending")

    print("\n" + "=" * 70)
    print("MIRROR COMPLETE")
    print(f"  Pages crawled:  {page_count}")
    print(f"  Total files:    {len(url_to_local_path)}")
    print(f"  Failed:         {len(failed_urls)}")
    print(f"  Output:         {OUTPUT_DIR}")
    if failed_urls:
        print("\n  Failed URLs:")
        for u, err in sorted(failed_urls.items()):
            print(f"    {u}")
            print(f"      -> {err}")
    print("=" * 70)


if __name__ == "__main__":
    crawl()
