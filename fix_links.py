#!/usr/bin/env python3
"""
Second-pass link fixer: re-reads all downloaded HTML files and rewrites
internal links using the complete url_to_local_path mapping.
Also converts paths to relative (not root-relative) for file:// browsing.
"""

import os
import re
import urllib.parse
from bs4 import BeautifulSoup
from pathlib import Path

OUTPUT_DIR = Path("d:/Project/aaa_temp/CFA_Notes/offline_site")


def normalize_url(url: str, base_url: str) -> str:
    full = urllib.parse.urljoin(base_url, url)
    parsed = urllib.parse.urlparse(full)
    return urllib.parse.urlunparse(parsed._replace(fragment=""))


def url_to_local_filepath(url: str) -> Path:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc or "freefellow.org"
    path = parsed.path or "/"
    local = OUTPUT_DIR / host / path.lstrip("/")
    if path.endswith("/") or not os.path.splitext(path)[1]:
        local = local / "index.html"
    return local


def build_url_map() -> dict:
    """Build a mapping of original URL -> local file path from existing files."""
    url_map = {}
    for html_file in OUTPUT_DIR.rglob("*.html"):
        # Skip CDN index.html (root of cdn domains)
        parts = html_file.relative_to(OUTPUT_DIR).parts
        if parts[0] in ("cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"):
            # Only skip the root index.html, not actual content
            if len(parts) <= 2:
                continue

        # Reconstruct the original URL
        host = parts[0]
        path_parts = list(parts[1:])
        if path_parts[-1] == "index.html":
            path_parts = path_parts[:-1]

        path = "/" + "/".join(path_parts)
        if path_parts:
            path += "/"

        url = f"https://{host}{path}"
        url_map[url] = html_file

        # Also add without trailing slash
        url_no_slash = f"https://{host}{('/' + '/'.join(path_parts)) if path_parts else ''}"
        if url_no_slash != url:
            url_map[url_no_slash] = html_file

    # Also map all other files (CSS, JS, fonts, images)
    for f in OUTPUT_DIR.rglob("*"):
        if f.is_dir():
            continue
        # Skip HTML files already processed
        if f.suffix == ".html":
            continue

        parts = f.relative_to(OUTPUT_DIR).parts
        if len(parts) < 2:
            continue
        host = parts[0]
        path = "/" + "/".join(parts[1:])
        url = f"https://{host}{path}"
        url_map[url] = f

    return url_map


def make_relative_path(from_file: Path, to_file: Path) -> str:
    try:
        rel = os.path.relpath(to_file, from_file.parent)
        return rel.replace("\\", "/")
    except ValueError:
        return "/" + str(to_file.relative_to(OUTPUT_DIR)).replace("\\", "/")


def rewrite_html(filepath: Path, url_map: dict):
    """Re-rewrite a single HTML file with the complete URL map."""
    # Reconstruct base URL
    parts = filepath.relative_to(OUTPUT_DIR).parts
    host = parts[0]
    path_parts = list(parts[1:])
    if path_parts and path_parts[-1] == "index.html":
        path_parts = path_parts[:-1]
    path = "/" + "/".join(path_parts)
    if path_parts:
        path += "/"
    base_url = f"https://{host}{path}"

    html = filepath.read_bytes()
    soup = BeautifulSoup(html, "html.parser")

    def local_href(raw_url: str) -> str | None:
        # Handle root-relative paths (from first-pass rewriting)
        if raw_url.startswith("/") and not raw_url.startswith("//"):
            # Treat as a path relative to OUTPUT_DIR
            target = OUTPUT_DIR / raw_url.lstrip("/")
            if target.exists():
                return make_relative_path(filepath, target)
            # Try adding index.html
            target_html = target / "index.html"
            if target_html.exists():
                return make_relative_path(filepath, target_html)
            return None

        # Handle absolute URLs
        full = normalize_url(raw_url, base_url)
        # Try with and without trailing slash
        if full in url_map:
            return make_relative_path(filepath, url_map[full])
        # Try without trailing slash
        if full.endswith("/"):
            alt = full.rstrip("/")
            if alt in url_map:
                return make_relative_path(filepath, url_map[alt])
        # Try with trailing slash (for pages)
        if not full.endswith("/") and not os.path.splitext(full)[1]:
            alt = full + "/"
            if alt in url_map:
                return make_relative_path(filepath, url_map[alt])
        return None

    changed = False

    for tag in soup.find_all("a", href=True):
        new = local_href(tag["href"])
        if new and new != tag["href"]:
            tag["href"] = new
            changed = True

    for tag in soup.find_all("link", href=True):
        new = local_href(tag["href"])
        if new and new != tag["href"]:
            tag["href"] = new
            changed = True

    for tag in soup.find_all("script", src=True):
        new = local_href(tag["src"])
        if new and new != tag["src"]:
            tag["src"] = new
            changed = True

    for tag in soup.find_all("img", src=True):
        new = local_href(tag["src"])
        if new and new != tag["src"]:
            tag["src"] = new
            changed = True

    for tag in soup.find_all("source", src=True):
        new = local_href(tag["src"])
        if new and new != tag["src"]:
            tag["src"] = new
            changed = True

    if changed:
        filepath.write_bytes(str(soup).encode("utf-8"))

    return changed


def rewrite_css(filepath: Path, url_map: dict):
    """Re-rewrite a CSS file's url() references."""
    parts = filepath.relative_to(OUTPUT_DIR).parts
    host = parts[0]
    path = "/" + "/".join(parts[1:])
    base_url = f"https://{host}{path}"

    try:
        css_text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False

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

        full_url = normalize_url(url_part, base_url)
        if full_url in url_map:
            local = make_relative_path(filepath, url_map[full_url])
            return f'url({quote}{local}{quote})'
        return match.group(0)

    new_css = re.sub(r'url\(([^)]+)\)', replace_url, css_text)
    if new_css != css_text:
        filepath.write_text(new_css, encoding="utf-8")
        return True
    return False


def main():
    print("Building URL map from downloaded files...")
    url_map = build_url_map()
    print(f"  {len(url_map)} URLs mapped")

    # Fix HTML files (skip cdn/font root index.html files)
    html_files = [f for f in OUTPUT_DIR.rglob("*.html")
                  if not (len(f.relative_to(OUTPUT_DIR).parts) <= 2
                          and f.relative_to(OUTPUT_DIR).parts[0]
                          in ("cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"))]
    html_changed = 0
    for f in html_files:
        try:
            if rewrite_html(f, url_map):
                html_changed += 1
                print(f"  FIXED: {f.relative_to(OUTPUT_DIR)}")
        except Exception as e:
            print(f"  ERROR: {f.relative_to(OUTPUT_DIR)}: {e}")

    # Fix CSS files
    css_files = list(OUTPUT_DIR.rglob("*.css"))
    # Also fix Google Fonts CSS (saved as .html due to query params in URL)
    gf_css = OUTPUT_DIR / "fonts.googleapis.com" / "css2" / "index.html"
    if gf_css.exists():
        css_files.append(gf_css)
    css_changed = 0
    for f in css_files:
        try:
            if rewrite_css(f, url_map):
                css_changed += 1
        except Exception as e:
            print(f"  ERROR: {f.relative_to(OUTPUT_DIR)}: {e}")

    print(f"\nDone! HTML fixed: {html_changed}, CSS fixed: {css_changed}")
    print(f"Total HTML files: {len(html_files)}, CSS files: {len(css_files)}")


if __name__ == "__main__":
    main()
