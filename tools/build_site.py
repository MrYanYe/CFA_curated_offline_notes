#!/usr/bin/env python3
"""
Build the cleaned, reorganized offline CFA study-notes site.

Source (untouched):  offline_prepnuggets/            (raw mirror, 309MB)
Output:              study_notes_site/               (usable offline site)

Per page, in order:
  1. Remove remote <script>/<link> tags (analytics, anti-spam, social trackers)
  2. Remove CleanTalk inline bot-detector <script> blocks
  3. Replace YouTube/Vimeo <iframe> with a static placeholder box
  4. Expand WP-Rocket lazyload: placeholder src/srcset -> real local image
  5. Rewrite every href/src/srcset through the original-URL -> new-local-file
     map, recomputing relative paths from each page's NEW location
  6. Fonts: fonts.googleapis.com */index.html are real CSS -> *.css; rewrite
     url(//fonts.gstatic.com/...) inside CSS and inline <style> to local paths

Deterministic; writes tools/.build/build_report.json.
"""

import json
import os
import re
import shutil
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MIRROR = REPO / "offline_prepnuggets"
SITE = REPO / "study_notes_site"
BUILD = REPO / "tools" / ".build"

LOCAL_HOSTS = ("prepnuggets.com", "cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com")

ATTR_URL_RE = re.compile(r'([a-zA-Z][a-zA-Z0-9-]*)\s*=\s*"([^"]*)"')
PLACEHOLDER_RE = re.compile(r"^data:image/svg\+xml")


def log(msg):
    print(msg, flush=True)


def resolve_url(base_url: str, value: str):
    """Resolve an attribute URL against the page's original absolute URL."""
    value = value.strip()
    if value.startswith(("data:", "mailto:", "tel:", "javascript:", "#", "blob:")):
        return None
    full = urllib.parse.urljoin(base_url, value)
    if full.startswith("//"):
        full = "https:" + full
    return full


def local_url_candidates(full: str):
    """Yield (host, url-decoded-path) candidates for an absolute URL."""
    parsed = urllib.parse.urlparse(full)
    host = parsed.netloc or "prepnuggets.com"
    if host not in LOCAL_HOSTS:
        return
    path = parsed.path.split("?")[0]
    variants = [path]
    decoded = urllib.parse.unquote(path)
    if decoded != path:
        variants.append(decoded)
        variants.append(urllib.parse.unquote(path.replace("+", " ")))
    for v in variants:
        yield host, v


def map_url_to_local(full: str, rename_css: dict):
    """Map absolute URL -> (site_path, raw_mirror_path_exists).

    None = external/unmappable host. Existence is judged against the RAW MIRROR
    (complete, order-independent) instead of the half-written site tree.
    """
    for host, path in local_url_candidates(full):
        if host == "prepnuggets.com":
            if path.startswith("/cfa-level-1-study-notes/"):
                new_path = path[len("/cfa-level-1-study-notes"):]
            else:
                new_path = path
            # cross-domain dirs (fonts.googleapis.com/... ) live at mirror root;
            # after relative resolution a ref to them can carry prepnuggets.com
            raw_candidates = (MIRROR / "prepnuggets.com" / path.lstrip("/"),
                              MIRROR / path.lstrip("/"))
        else:
            new_path = path
            raw_candidates = (MIRROR / host / path.lstrip("/"),)
        if new_path in rename_css:
            new_path = rename_css[new_path]
        if host == "prepnuggets.com":
            local = SITE / new_path.lstrip("/")
        else:
            # other hosts map to site/<host>/<path>; new_path carries no host
            local = SITE / host / new_path.lstrip("/")
        if os.path.splitext(local.name)[1] == "":
            local = local / "index.html"
            raw_candidates = tuple(r / "index.html" if r.suffix == "" else r for r in raw_candidates)
        return local, any(r.exists() for r in raw_candidates)
    return None


EXTERNALIZE_EXTS = (".php", ".json")


def rewrite_srcset_or_url(value: str, base_url: str, abs_dir: Path, renames: dict, report: dict):
    """Rewrite one attribute value (a srcset is a comma list of 'url [desc]')."""
    if value.lstrip().startswith(("data:", "mailto:", "tel:", "#")):
        return value  # data: URIs contain commas: never split them
    out = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        entries = chunk.split(" ")
        url = entries[0]
        rest = " ".join(entries[1:])
        full = resolve_url(base_url, url)
        if full is None:
            out.append((url, rest))
            continue
        mapped = map_url_to_local(full, renames)
        if mapped is None:
            if full.startswith("//"):
                full = "https:" + full
            out.append((full, rest))
            continue
        local, raw_exists = mapped
        if not raw_exists:
            parsed = urllib.parse.urlparse(full)
            ext = os.path.splitext(parsed.path.lower())[1]
            page_like = ext == "" or ext in EXTERNALIZE_EXTS
            if page_like:
                report["externalized_urls"].append((str(local), full))
                out.append((full, rest))
                continue
            report["assets_missing_from_mirror"].append((str(local), full))
        rel = os.path.relpath(local, abs_dir).replace("\\", "/")
        out.append((rel, rest))
    return ", ".join((u + (" " + r if r else "")).rstrip() for u, r in out)


def rewrite_attr_urls(html: str, base_url: str, abs_page_dir: Path, renames: dict, report: dict):
    tag_re = re.compile(r"<[a-zA-Z][a-zA-Z0-9-]*[^>]*>", re.S)

    def sub_tag(m):
        def sub_attr(am):
            name, value = am.group(1), am.group(2)
            if name not in ("href", "src", "srcset", "poster", "ping"):
                return am.group(0)
            return f'{name}="{rewrite_srcset_or_url(value, base_url, abs_page_dir, renames, report)}"'
        return ATTR_URL_RE.sub(sub_attr, m.group(0))

    return tag_re.sub(sub_tag, html)


def strip_noncache_networks(html: str) -> str:
    """Remove remote tags + CleanTalk inline JS.

    script/link/img/source/iframe with a non-local host src get removed:
    they can never load offline, but browsers DO wait for them on the load
    event (each network timeout). Only <a href> stays online-resolvable.
    """
    html = re.sub(
        r"<script[^>]*>\s*var\s+ctPublic(?:Functions)?\s*=\s*\{[^<]*?</script>",
        "", html, flags=re.S)
    html = re.sub(
        r"<script\b[^>]*>\s*[^<]*apbct[^<]*</script>",
        "", html, flags=re.S)
    # anti-spam leftovers: any inline script still referencing ctPublic/sharethis
    for ident in ("ctPublic", "sharethis", "stWidget", "stlib", "channel-platform",
                  "cdn-cgi", "cleantalk", "fd-api", "st_insights"):
        html = re.sub(
            rf"<script\b[^>]*src=\"[^\"]*{ident}[^\"]*\"[^>]*></script>", "", html, flags=re.S | re.I)
        html = re.sub(
            rf"<script\b(?![^>]*src=)[^>]*>[^<]*{ident}[^<]*</script>", "", html, flags=re.S | re.I)
    # google-fonts quick links (css2 endpoints) are superseded by the mirrored
    # family-*/style.css; drop them to avoid file://host lookup
    html = re.sub(
        r'<link\b[^>]*href="[^"]*fonts\.googleapis\.com/css\?[^"]*"[^>]*>\s*', "", html, flags=re.S | re.I)

    def attr_is_remote(attr, value):
        full = resolve_url("https://prepnuggets.com/", value)
        if not full:
            return False
        host = urllib.parse.urlparse(full).netloc
        return bool(host and host not in LOCAL_HOSTS)

    def tag_sub(m):
        tag = m.group(0)
        for attr in ("src", "href", "data-src", "data-lazy-src", "poster"):
            am = re.search(f'{attr}="([^"]*)"', tag, flags=re.I)
            if am and attr_is_remote(attr, am.group(1)):
                return ""
        for am in re.finditer(r'(?i)\bsrcset="([^"]*)"', tag):
            if any(attr_is_remote("srcset", p.strip().split(" ")[0])
                   for p in am.group(1).split(",") if p.strip()):
                return ""
        return tag

    html = re.sub(r"<(?:script|link|img|source|embed|video|audio|iframe)\b[^>]*>",
                  tag_sub, html, flags=re.S)
    html = re.sub(r'<link[^>]*rel="(?:preconnect|dns-prefetch|pingback)"[^>]*>\s*', "", html, flags=re.I)
    return html


def replace_video_iframes(html: str) -> str:
    iframe_re = re.compile(
        r"<iframe\b([^>]*?)>.*?</iframe>|<iframe\b([^>]*?)/?>",
        re.S | re.I)

    def has_remote_video(attrs: str):
        src = re.search(r'src="([^"]*)"', attrs, flags=re.I)
        return bool(src and re.search(
            r"(?:youtube\.com|youtube-nocookie\.com|youtu\.be|vimeo\.com|bilibili\.com|mp4\b)",
            re.search(r'(?:https?://)?//?[^"]*', src.group(1), flags=re.I).group(0) if src.group(1) else ""))

    def sub(m):
        attrs = m.group(1) or m.group(2) or ""
        if not has_remote_video(attrs):
            # keep iframe as-is; src rewriting happens in the attr pass
            return m.group(0)
        src = re.search(r'src="([^"]*)"', attrs, flags=re.I)
        title_attr = re.search(r'title="([^"]*)"', attrs, flags=re.I)
        width = re.search(r'width="(\d+)"', attrs, flags=re.I)
        height = re.search(r'height="(\d+)"', attrs, flags=re.I)
        w = width.group(1) if width else "560"
        h = height.group(1) if height else "315"
        title = (title_attr.group(1) if title_attr else "Video").replace("&", "&amp;").replace("<", "&lt;")
        return (
            f'<div class="pn-video-offline" style="width:100%;max-width:{w}px;aspect-ratio:{w}/{h};'
            f'margin:1em auto;background:#e9ecf1;border:1px solid #d5dae2;border-radius:8px;'
            f'display:flex;align-items:center;justify-content:center;padding:12px;box-sizing:border-box;">'
            f'<p style="text-align:center;color:#5a6472;margin:0;">\U0001F39B <b>{title}</b><br>'
            f'<span style="font-size:.85em;color:#8a93a2;">Video (offline)</span></p></div>')

    return iframe_re.sub(sub, html)


def sanitize_srcset(value: str) -> str:
    """Drop gray SVG placeholder entries from a srcset string."""
    parts = [p.strip() for p in value.split(",")]
    cleaned = [p for p in parts if not PLACEHOLDER_RE.match(p.split(" ")[0])]
    return ", ".join(cleaned)


def expand_lazyload(html: str) -> str:
    """data-lazy-src/-srcset -> src/-srcset; drop gray SVG placeholders.

    placeholders can appear as the FIRST entry of a srcset with real URL
    candidates following - every data:image/svg+xml entry is removed.
    """
    def img_sub(m):
        tag = m.group(0)
        def get(attr):
            am = re.search(f'{attr}="([^"]*)"', tag, flags=re.I)
            return am.group(1) if am else None
        lazy_src = get("data-lazy-src")
        lazy_srcset = get("data-lazy-srcset")
        src = get("src")
        if PLACEHOLDER_RE.match(src or "") or not src:
            if lazy_src:
                tag = re.sub(r'(?i)\bsrc="[^"]*"', f'src="{lazy_src}"', tag, count=1)
        if lazy_srcset:
            tag = re.sub(r'(?i)\bsrcset="[^"]*"', "", tag, count=1)
            tag = tag[:-2] + f' srcset="{lazy_srcset}" />' if tag.rstrip().endswith("/>") \
                else tag[:-1] + f' srcset="{lazy_srcset}">'
        for attr in ("data-lazy-src", "data-lazy-srcset", "data-lazy-sizes", "data-srcset", "data-src"):
            tag = re.sub(rf'(?i)\s{attr}="[^"]*"', "", tag)
        # remove any leftover data:image/svg entries inside srcset (as candidates)
        def strip_placeholder(am):
            cleaned = sanitize_srcset(am.group(1))
            return f'srcset="{cleaned}"' if cleaned else ""
        tag = re.sub(r'(?i)\ssrcset="([^"]*)"', strip_placeholder, tag)
        return tag

    html = re.sub(r"<img\b[^>]*>", img_sub, html)
    html = re.sub(r"<source\b[^>]*>",
                  lambda m: re.sub(r'(?i)\sdata-lazy-srcset="([^"]*)"',
                                   r' srcset="\1"', m.group(0)), html)

    # some images (site logo) have only a placeholder src; their real src sits
    # in a <noscript><img> twin -> adopt it into the live img
    twin_re = re.compile(
        r"(<img\b[^>]*\bsrc=\"data:image/svg\+xml[^\"]*\"[^>]*?/>)\s*"
        r"<noscript>\s*(<img\b[^>]*\bsrc=\"([^\"]+)\"[^>]*?/>)"
        r"\s*</noscript>",
        re.S)

    def twin_sub(m):
        outer, noscript_tag, real_src = m.group(1), m.group(2), m.group(3)
        outer = re.sub(r'(?i)\bsrc="[^"]*"', f'src="{real_src}"', outer, count=1)
        return outer + noscript_tag

    html = twin_re.sub(twin_sub, html)
    return html
    # same placeholder cleanup on <source srcset>
    html = re.sub(r"<source\b[^>]*>",
                  lambda m: re.sub(r'(?i)\ssrcset="([^"]*)"',
                                   lambda am: f'srcset="{sanitize_srcset(am.group(1))}"'
                                   if sanitize_srcset(am.group(1)) else "", m.group(0)), html)
    return html


def rewrite_inline_style_urls(html: str, abs_page_dir: Path, renames: dict, report: dict):
    """url(//fonts.gstatic.com/...) inside page <style> blocks -> local relative."""
    def url_sub(m):
        u = m.group(2)
        full = resolve_url("https://prepnuggets.com/", u.strip("'\""))
        if full is None:
            return m.group(0)
        mapped = map_url_to_local(full, renames)
        if mapped is None:
            return m.group(0)
        local, raw_exists = mapped
        if not raw_exists:
            report["assets_missing_from_mirror"].append((str(local), full))
        rel = os.path.relpath(local, abs_page_dir).replace("\\", "/")
        return f"url({rel})"

    return re.sub(r"url\(\s*(['\"]?)((?:https?:)?//(?:fonts\.gstatic\.com|prepnuggets\.com)/[^)'\"]+)\1\s*\)",
                  url_sub, html, flags=re.I)


def clean_page(html: str, base_url: str, abs_page_dir: Path, renames: dict, report: dict) -> str:
    html = strip_noncache_networks(html)
    html = replace_video_iframes(html)
    html = expand_lazyload(html)
    html = rewrite_attr_urls(html, base_url, abs_page_dir, renames, report)
    html = rewrite_inline_style_urls(html, abs_page_dir, renames, report)
    # @import of live google-fonts css endpoints -> already mirrored locally
    html = re.sub(r"@import\s+(?:url\()?['\"]?(?:https?:)?//fonts\.googleapis\.com/[^\"')]*['\"]?\)?\s*;",
                  "", html, flags=re.I | re.S)
    return html


def copy_tree(src: Path, dst: Path):
    for dp, dn, fn in os.walk(src):
        rel = Path(dp).relative_to(src)
        target = dst / rel
        target.mkdir(parents=True, exist_ok=True)
        for f in fn:
            shutil.copy(Path(dp) / f, target / f)


def rewrite_css_urls(report: dict):
    """Every .css in the site: url(//fonts.gstatic.com|...prepnuggets.com) -> local.

    (Skipped before only for fonts.googleapis.com css; wp-content cached css
    holds @font-face blocks that would otherwise hang offline.)
    """
    for css_file in SITE.rglob("*.css"):
        css = css_file.read_text(encoding="utf-8", errors="ignore")
        if not any(h in css for h in ("fonts.gstatic.com", "prepnuggets.com", "fonts.googleapis.com")):
            continue

        def url_sub(m):
            u = m.group(2)
            full = resolve_url("https://prepnuggets.com/", u.strip("'\""))
            if full is None:
                return m.group(0)
            mapped = map_url_to_local(full, {})
            if mapped is None:
                return m.group(0)
            local, raw_exists = mapped
            if not raw_exists:
                report["assets_missing_from_mirror"].append((str(local), full))
            rel = os.path.relpath(local, css_file.parent).replace("\\", "/")
            return f"url({rel})"

        css = re.sub(r"url\(\s*(['\"]?)((?:https?:)?//(?:fonts\.gstatic\.com|prepnuggets\.com)/[^)'\"]+)\1\s*\)",
                     url_sub, css, flags=re.I)
        # @import of live google-fonts css endpoints - already mirrored locally
        css = re.sub(r"@import\s+(?:url\()?['\"]?(?:https?:)?//fonts\.googleapis\.com/[^\"')]*['\"]?\)?\s*;", "", css, flags=re.I)
        css_file.write_text(css, encoding="utf-8")


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    BUILD.mkdir(parents=True, exist_ok=True)
    report = {"externalized_urls": [], "assets_missing_from_mirror": [], "cleaned_pages": []}

    # filesystem names carved from URL paths can contain literal '%' escapes
    # (e.g. fonts.googleapis.com/family-Roboto%20Condensed%3A...).  Under
    # file:// a browser URL-decodes them -> such files are unreachable.
    # Migrate every %-name to a decoded Windows-safe name and remember the
    # (old, new) pairs for a global reference pass.
    name_pairs = []

    def safe_name(name: str) -> str:
        decoded = urllib.parse.unquote(name)
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f\s]', "_", decoded).strip("_") or name
        return safe if safe != name else name

    # copy static asset trees verbatim (relative internals stay consistent)
    for sub in ("wp-content", "wp-includes", "wp-json"):
        src = MIRROR / "prepnuggets.com" / sub
        if src.exists():
            copy_tree(src, SITE / sub)
            log(f"copied {sub}/")
    for host in ("fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net"):
        src = MIRROR / host
        if src.exists():
            copy_tree(src, SITE / host)
            log(f"copied {host}/")

    for p in sorted(SITE.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if "%" not in p.name:
            continue
        safe = safe_name(p.name)
        if safe == p.name or p.with_name(safe).exists():
            continue
        p.rename(p.with_name(safe))
        name_pairs.append((p.name, safe))
        log(f"percent-name migration: {p.name} -> {safe}")

    # drop mirrorer-generated nav index.html inside asset domains; fix fonts css names
    for h in ("cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"):
        nav = SITE / h / "index.html"
        if nav.exists():
            nav.unlink()
            log(f"dropped {h}/index.html (mirror nav page)")
    # fonts.googleapis.com: mirrored 'index.html' files ARE CSS content ->
    # rename to *.css so browsers apply them under file:// MIME sniffing
    rename_css = {}
    fam_root = MIRROR / "fonts.googleapis.com"
    if fam_root.exists():
        for fam in fam_root.iterdir():
            idx = fam / "index.html"
            if idx.exists():
                safe_fam = next((s for o, s in name_pairs if o == fam.name), fam.name)
                rename_css[f"/fonts.googleapis.com/{fam.name}/index.html"] = \
                    f"/fonts.googleapis.com/{safe_fam}/style.css"
    for fam in (SITE / "fonts.googleapis.com").iterdir():
        idx = fam / "index.html"
        if idx.exists():
            idx.rename(fam / "style.css")
            log(f"fonts css: {fam.name}/index.html -> style.css")

    rewrite_css_urls(report)

    # content pages: lift cfa-level-1-study-notes/* up to the site root
    notes_src = MIRROR / "prepnuggets.com" / "cfa-level-1-study-notes"
    pages = [p for p in notes_src.rglob("*.html")]
    qm_src = MIRROR / "prepnuggets.com" / "quantitative-methods" / "index.html"
    if qm_src.exists():
        pages.append(qm_src)
    log(f"content pages to clean: {len(pages)}")

    for src_page in pages:
        parts = src_page.relative_to(MIRROR / "prepnuggets.com").parts
        if parts[0] == "quantitative-methods":
            new_page = SITE / "quantitative-methods" / "index.html"
            base_url = "https://prepnuggets.com/quantitative-methods/"
        else:
            rel = src_page.relative_to(notes_src)
            parent = rel.parent
            if parent.as_posix() == "." and rel.name == "index.html":
                new_page = SITE / "index.html"
            else:
                new_page = SITE / parent / "index.html"
            base_url = "https://prepnuggets.com/cfa-level-1-study-notes/" + parent.as_posix() + "/"
        new_rel = new_page.relative_to(SITE).as_posix()
        report["cleaned_pages"].append(new_rel)
        html = src_page.read_text(encoding="utf-8", errors="ignore")
        html = clean_page(html, base_url, new_page.parent, rename_css, report)
        new_page.parent.mkdir(parents=True, exist_ok=True)
        new_page.write_text(html, encoding="utf-8")
    log(f"cleaned {len(report['cleaned_pages'])} pages")

    # strip mirrored-font-css leftovers: dropped nav index.html refs on cleaned pages
    cleaned = set(report["cleaned_pages"])
    nav_re = re.compile(r'<link\b[^>]*href="[^"]*(?:cdn\.jsdelivr\.net|fonts\.googleapis\.com|fonts\.gstatic\.com)/[^"]*index\.html"[^>]*>\s*',
                        flags=re.I)
    for rel in cleaned:
        p = SITE / rel
        html = p.read_text(encoding="utf-8", errors="ignore")
        p.write_text(nav_re.sub("", html), encoding="utf-8")

    # rewrite every reference to the migrated percent-names (pages, css, js)
    if name_pairs:
        n = 0
        for f in (p2 for p2 in SITE.rglob("*") if p2.suffix.lower() in
                  (".html", ".css", ".js", ".json", ".txt", ".xml")):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeError):
                continue
            new = text
            for old, safe in name_pairs:
                new = new.replace(old, safe)
            if new != text:
                f.write_text(new, encoding="utf-8")
                n += 1
        log(f"percent-name ref rewrite applied to {n} files")

    # deterministic fallback: for missing image derivatives point references at
    # the largest same-prefix variant already on disk (zero network needed)
    from fetch_missing import rewrite_refs_to_existing  # noqa: PLC0415
    rewrote = 0
    for local, full in report["assets_missing_from_mirror"]:
        if Path(local).suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            if rewrite_refs_to_existing(Path(local), full):
                rewrote += 1
    log(f"sibling-ref rewrites applied: {rewrote}")
    report["sibling_ref_rewrites"] = rewrote

    (BUILD / "build_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    size_mb = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fn in os.walk(SITE) for f in fn) / 1e6
    log(f"done. study_notes_site size: {size_mb:.1f} MB")
    log(f"externalized urls: {len(report['externalized_urls'])}; "
        f"assets missing from mirror: {len(report['assets_missing_from_mirror'])} (backfill next)")


if __name__ == "__main__":
    main()
