#!/usr/bin/env python3
"""
Mirror prepnuggets.com CFA Level 1 study notes.
Same engine as mirror_site.py, different configuration.
"""

import os
import re
import sys
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# ========== CONFIGURATION ==========
SEED_URL = "https://prepnuggets.com/cfa-level-1-study-notes/"
OUTPUT_DIR = Path("d:/Project/aaa_temp/CFA_Notes/offline_prepnuggets")

# Pages to crawl (subpath match)
CRAWL_PATH_PREFIXES = [
    "/cfa-level-1-study-notes/",
    "/quantitative-methods/",
]

# Exact paths
CRAWL_EXACT_PATHS = []

# Asset paths — downloaded but not crawled for links
ASSET_PATH_PREFIXES = [
    "/wp-content/",
    "/wp-includes/",
    "/wp-json/",
]

# External hosts to download
EXTERNAL_HOSTS = [
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
]

DOWNLOAD_EXTERNAL = True
DELAY_SECONDS = 0.3
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://prepnuggets.com/",
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
    full = urllib.parse.urljoin(base_url, url)
    # Handle protocol-relative URLs (//domain/path)
    if full.startswith("//"):
        full = "https:" + full
    parsed = urllib.parse.urlparse(full)
    clean = urllib.parse.urlunparse(parsed._replace(fragment=""))
    return clean


def should_crawl(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc and parsed.netloc != "prepnuggets.com":
        return False
    path = parsed.path or "/"
    ext = os.path.splitext(path)[1].lower()
    if ext and ext in ASSET_EXTENSIONS:
        return False
    for exact in CRAWL_EXACT_PATHS:
        if path == exact or path == exact.rstrip("/"):
            return True
    for prefix in CRAWL_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def should_download(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc or parsed.netloc == "prepnuggets.com":
        path = parsed.path or "/"
        for exact in CRAWL_EXACT_PATHS:
            if path == exact or path == exact.rstrip("/"):
                return True
        for prefix in CRAWL_PATH_PREFIXES:
            if path.startswith(prefix):
                return True
        for prefix in ASSET_PATH_PREFIXES:
            if path.startswith(prefix):
                return True
        return False
    if DOWNLOAD_EXTERNAL:
        for host in EXTERNAL_HOSTS:
            if parsed.netloc == host or parsed.netloc.endswith("." + host):
                return True
    return False


def url_to_local_filepath(url: str) -> Path:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc or "prepnuggets.com"
    path = parsed.path or "/"
    # For query strings, create a unique directory to avoid collisions
    # The raw path already includes query in the URL; we need to handle this
    local = OUTPUT_DIR / host / path.lstrip("/")
    if path.endswith("/") or not os.path.splitext(path)[1]:
        # Check if there's a query string
        if parsed.query:
            # Encode query as a directory name, replacing Windows-invalid chars
            safe_query = parsed.query
            for ch in '|<>"?*:\\/':
                safe_query = safe_query.replace(ch, "-")
            safe_query = safe_query.replace("&", "_").replace("=", "-")[:100]
            local = local.parent / safe_query / "index.html"
        else:
            local = local / "index.html"
    return local


def download_file(url: str) -> tuple:
    try:
        time.sleep(DELAY_SECONDS)
        resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        return resp.content, None
    except requests.RequestException as e:
        return None, str(e)


def extract_links(html: bytes, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    links = {"pages": [], "styles": [], "scripts": [], "images": [], "fonts": [], "other": []}

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

    for tag in soup.find_all("iframe", src=True):
        links["other"].append(normalize_url(tag["src"], base_url))

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
    try:
        rel = os.path.relpath(to_file, from_file.parent)
        return rel.replace("\\", "/")
    except ValueError:
        return "/" + str(to_file.relative_to(OUTPUT_DIR)).replace("\\", "/")


def rewrite_html(html: bytes, base_url: str, page_local_path: Path) -> bytes:
    soup = BeautifulSoup(html, "html.parser")

    def local_href(url: str):
        full = normalize_url(url, base_url)
        # Also try with www prefix
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
    if url in visited_urls:
        return
    visited_urls.add(url)
    try:
        print(f"  [ASSET] {url}")
    except UnicodeEncodeError:
        print(f"  [ASSET] {url.encode('ascii', 'replace').decode('ascii')}")
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
    links = extract_links(content, url)
    all_asset_urls = set(links["styles"] + links["scripts"] + links["images"] +
                         links["fonts"] + links["other"])
    for asset_url in all_asset_urls:
        if should_download(asset_url) and asset_url not in visited_urls:
            download_asset(asset_url)

    # Download CSS-referenced fonts
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

    local_path = url_to_local_filepath(url)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    rewritten = rewrite_html(content, url, local_path)
    local_path.write_bytes(rewritten)
    url_to_local_path[url] = local_path

    new_pages = []
    for page_url in set(links["pages"]):
        if page_url not in visited_urls and should_crawl(page_url):
            new_pages.append(page_url)
    return new_pages


def crawl():
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

    # ---- SECOND PASS ----
    print("\n  [PASS 2] Re-rewriting all HTML with complete link map...")
    html_files = [p for url, p in url_to_local_path.items()
                  if p.suffix == ".html" and "cdn.jsdelivr.net" not in str(p)]
    rewrite_count = 0
    for local_path in html_files:
        orig_url = None
        for u, lp in url_to_local_path.items():
            if lp == local_path:
                orig_url = u
                break
        if not orig_url:
            continue
        try:
            html = local_path.read_bytes()
            rewritten = rewrite_html(html, orig_url, local_path)
            local_path.write_bytes(rewritten)
            rewrite_count += 1
        except Exception as e:
            print(f"    WARN: {e}")

    css_files = [p for url, p in url_to_local_path.items() if p.suffix == ".css"]
    for local_path in css_files:
        orig_url = None
        for u, lp in url_to_local_path.items():
            if lp == local_path:
                orig_url = u
                break
        if not orig_url:
            continue
        try:
            css_bytes = local_path.read_bytes()
            rewritten = rewrite_css(css_bytes, orig_url, local_path)
            local_path.write_bytes(rewritten)
        except Exception as e:
            print(f"    WARN: {e}")
    print(f"    Rewrote {rewrite_count} HTML files + {len(css_files)} CSS files")

    # ---- THIRD PASS: Fix root-relative paths ----
    print("\n  [PASS 3] Fixing root-relative paths...")
    fixed_root = 0
    for local_path in html_files:
        orig_url = None
        for u, lp in url_to_local_path.items():
            if lp == local_path:
                orig_url = u
                break
        if not orig_url:
            continue
        try:
            html = local_path.read_bytes()
            soup = BeautifulSoup(html, "html.parser")
            changed = False
            for tag in soup.find_all(["a", "link", "script", "img", "source"]):
                attr = "href" if tag.name in ("a", "link") else "src"
                if tag.has_attr(attr):
                    val = tag[attr]
                    if val and val.startswith("/") and not val.startswith("//"):
                        target = OUTPUT_DIR / val.lstrip("/")
                        if target.exists():
                            tag[attr] = make_relative_path(local_path, target)
                            changed = True
                        elif (target / "index.html").exists():
                            tag[attr] = make_relative_path(local_path, target / "index.html")
                            changed = True
            if changed:
                local_path.write_bytes(str(soup).encode("utf-8"))
                fixed_root += 1
        except Exception as e:
            print(f"    WARN: {e}")
    print(f"    Fixed {fixed_root} files with root-relative paths")

    # Print summary
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
