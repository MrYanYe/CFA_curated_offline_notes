#!/usr/bin/env python3
"""
Build CFA_Notes/full_site_single_file.html from study_notes_site/.

Architecture (single file, zero external requests):
  - Static shell = cleaned homepage <body> (header/chrome/sidebar kept; the
    theme JS binds its menu handlers against the real static DOM at load)
  - All other pages stored as chunked JSON: {s: slug, t: title, h: article}
  - Every asset the pages reference (images/fonts/css url()) is embedded as a
    base64 data URI; internal page links become '#/<slug>' hash routes
  - Router: on hashchange replace the <article id="post-..."> element with the
    stored article, restore title, eval article-inline scripts, scroll top

Lossless: original image bytes are embedded untouched (user's choice).
"""

import base64
import io
import json
import mimetypes
import os
import re
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "cfa_l1_offline_notes_site_2026"
OUT_FILE = REPO / "cfa_l1_offline_notes_all_in_one_2026.html"
OUT_COMPRESSED = REPO / "cfa_l1_offline_notes_all_in_one_2026_compressed.html"

CHUNK_BYTES = 4_000_000

COMPRESS_MODE = "--compress" in sys.argv  # module-level: b64() is used widely

COMPRESS_THRESHOLD = 50_000  # bytes; smaller images stay untouched
COMPRESS_QUALITY = 60  # visually lossless for diagrams; original kept too

FONT_MIMES = {"woff2": "font/woff2", "woff": "font/woff", "ttf": "font/ttf",
              "otf": "font/otf", "eot": "application/vnd.ms-fontobject"}
IMAGE_MIMES = {"svg": "image/svg+xml", "webp": "image/webp"}


def b64(path: Path, compress: bool = False):
    ext = path.suffix.lower().lstrip(".")
    mime = FONT_MIMES.get(ext) or IMAGE_MIMES.get(ext) \
        or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = path.read_bytes()
    if compress and ext in ("png", "jpg", "jpeg", "gif", "webp") and len(data) > COMPRESS_THRESHOLD:
        try:
            img = Image.open(io.BytesIO(data))
            if not (ext == "gif" and getattr(img, "is_animated", False)):
                img = img.convert("RGBA" if img.mode in ("P", "RGBA", "LA") else "RGB")
                if img.mode == "RGBA":
                    flat = Image.new("RGB", img.size, (255, 255, 255))
                    flat.paste(img, mask=img.getchannel("A"))
                    img = flat
                out = io.BytesIO()
                img.save(out, "JPEG", quality=COMPRESS_QUALITY)
                candidate = out.getvalue()
                if len(candidate) < len(data):
                    data = candidate
                    mime = "image/jpeg"
        except Exception:  # noqa: BLE001 - keep original on any failure
            pass
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def resolve_site_file(rel_url: str, base_dir: Path):
    """Relative URL in a page/css at base_dir -> site file Path or None."""
    target = (base_dir / rel_url.split("?")[0].split("#")[0]).resolve()
    try:
        target.relative_to(SITE)
    except ValueError:
        return None
    if target.is_dir():
        target = target / "index.html"
    return target if target.is_file() else None


def rewrite_css(css_text: str, css_path: Path) -> str:
    """url(relative) -> data URI; drop @import of live google-fonts css.

    Legacy fallback font formats (.ttf/.eot/.otf) are swapped for the
    same-stem .woff2 where available: modern browsers use woff2 and the
    fallbacks only bloat the bundle.
    """
    def url_sub(m):
        url = m.group(2).strip("'\"")
        if url.startswith(("data:", "#", "http://", "https://")):
            return m.group(0)
        f = resolve_site_file(url, css_path.parent)
        if f is None:
            # inline styles carry depth-relative urls (../wp-content/...) while
            # the true base is the site root - retry rooted at SITE
            f = resolve_site_file(re.sub(r"^(?:\.\./)+", "", url), SITE)
        if f is None:
            return m.group(0)
        if f.suffix.lower() in (".ttf", ".eot", ".otf"):
            w2 = f.with_suffix(".woff2")
            if w2.is_file():
                f = w2
        return f"url({b64(f, COMPRESS_MODE)})"

    css_text = re.sub(r"@import\s+(?:url\()?\s*[\"']?(?:https?:)?//fonts\.googleapis\.com/[^\"')]*?[\"']?\s*\)?\s*;",
                      "", css_text, flags=re.I | re.S)
    return re.sub(r"url\(\s*(['\"]?)([^'\"\\)]*)\1\s*\)", url_sub, css_text, flags=re.I)



def minify_css(css_text: str) -> str:
    """Whitespace/comment minify - safe for data-URI css (keeps url(...) intact)."""
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    css_text = re.sub(r"\s+", " ", css_text)
    css_text = re.sub(r"\s*([{};:,>])\s*", r"\1", css_text)
    return css_text.strip()


def page_slug(site_rel: str) -> str:
    if site_rel == "index.html":
        return ""  # the homepage; a bare name would slice to 'index.htm'
    return site_rel[: -len("/index.html")] if site_rel.endswith("/index.html") else site_rel


def slug_href(slug: str) -> str:
    return "#/" + (slug + "/" if slug else "")


PUFFY_GIF = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"


def rewrite_body_refs(html: str, base_dir: Path, pages: set, registry: dict) -> str:
    """Page links -> '#/slug'; images -> registry ids (dd in <img data-pn-img>);
    other assets -> inline base64 data URIs.
    """
    def register(f: Path) -> str:
        key = f.relative_to(SITE).as_posix()
        if key not in registry:
            registry[key] = None  # filled at serialization
        return key

    def resolve(url: str):
        if url == "" or url.startswith(("#", "data:", "mailto:", "javascript:", "tel:")):
            return None, None
        if url.startswith(("http://", "https://")):
            return "external", url
        f = resolve_site_file(url, base_dir)
        if f is None:
            # sidebar/menu links are relative to the mirror-page depth, which is
            # one level deeper than the parked site page: retry rooted at SITE
            # (same fallback the css rewrite already uses)
            f = resolve_site_file(re.sub(r"^(?:\.\./)+", "", url), SITE)
        if f is None:
            return None, None
        if f.name == "index.html":
            slug = page_slug(f.relative_to(SITE).as_posix())
            return ("page", slug_href(slug) if (slug in pages or slug == "") else url)
        return "file", f

    tag_re = re.compile(r"<[a-zA-Z][a-zA-Z0-9-]*\b[^>]*>", re.S)

    def sub_tag(m):
        tag = m.group(0)

        # <img ...> images -> registry id
        if tag.lstrip("<").startswith("img"):
            src_m = re.search(r'(?i)\bsrc="([^"]*)"', tag)
            if src_m:
                kind, f = resolve(src_m.group(1))
                if kind == "file":
                    key = register(f)
                    # the mirrorer glued attrs: `width="1188"srcset="..."` (no space).
                    # capture the leading quote/spacer and re-emit it, otherwise
                    # the previous attribute's closing quote gets swallowed
                    tag = re.sub(r'(?i)(["\s])(srcset|data-lazy-srcset)="[^"]*"',
                                 r"\1", tag)
                    tag = re.sub(r'(?i)\bsrc="[^"]*"', f'src="{PUFFY_GIF}"', tag, count=1)
                    tag = tag[:-2] + f' data-pn-img="{key}" />' if tag.rstrip().endswith("/>") \
                        else tag[:-1] + f' data-pn-img="{key}">'
                    return tag

        # <script src=file> -> inline content: data:-URL scripts are blocked
        # by the browser and would leave jQuery undefined
        if tag.lstrip("<").startswith("script"):
            src_m = re.search(r'(?i)\bsrc="([^"]*)"', tag)
            if src_m:
                kind, f = resolve(src_m.group(1))
                if kind == "file" and f.suffix == ".js":
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    return "<script>\n" + content + "\n</script>"

        def sub_attr(am):
            name, value = am.group(1), am.group(2)
            if name in ("src", "href", "poster"):
                kind, f = resolve(value)
                if kind == "external" or kind is None or (kind == "file" and f is None):
                    return am.group(0)
                if kind == "page":
                    return f'{name}="{f}"'
                return f'{name}="{b64(f, COMPRESS_MODE)}"'
            if name == "srcset":
                entries = []
                for chunk in value.split(","):
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    u, rest = chunk.split(" ", 1) if " " in chunk else (chunk, "")
                    kind, f = resolve(u)
                    if kind == "file":
                        entries.append(f"{b64(f, COMPRESS_MODE)} {rest}".rstrip())
                    elif kind in (None, "external"):
                        entries.append(f"{u} {rest}".rstrip())
                return f'srcset="{", ".join(entries)}"' if entries else ""
            return am.group(0)

        return re.sub(r'([a-zA-Z][a-zA-Z0-9-]*)\s*=\s*"([^"]*)"', sub_attr, tag)

    return tag_re.sub(sub_tag, html)


def extract_article(html: str):
    m = re.search(r"<article\b[^>]*>(.*?)</article>", html, re.S)
    return m.group(1) if m else None


# On click: inline-embed over http(s); over file:// open the watch page.
# YouTube refuses /embed/ without a Referer (Error 153) - every file:// page -
# while watch pages play fine with no referrer; see build_site.py notes.
VIDEO_PLAYER_JS = ("(function(){document.addEventListener('click',function(e){"
                   "var t=e.target.closest?e.target.closest('.pn-video-player'):null;"
                   "if(!t||t.dataset.loaded)return;t.dataset.loaded='1';"
                   "var src=t.dataset.src||'',m,watch='';"
                   "if((m=src.match(/(?:youtube(?:-nocookie)?\\.com\\/embed\\/|youtu\\.be\\/|youtube\\.com\\/watch\\?v=)([A-Za-z0-9_-]+)/)))watch='https://www.youtube.com/watch?v='+m[1];"
                   "else if((m=src.match(/(?:player\\.)?vimeo\\.com\\/video\\/(\\d+)/)))watch='https://vimeo.com/'+m[1];"
                   "if(location.protocol==='file:'){if(watch)window.open(watch,'_blank');return;}"
                   "t.innerHTML='<iframe src=\"'+encodeURI(src)+'\" width=\"100%\" height=\"100%\" "
                   "frameborder=\"0\" allow=\"autoplay; encrypted-media; picture-in-picture; fullscreen\" "
                   "allowfullscreen style=\"position:absolute;inset:0;\"></iframe>'"
                   "+(watch?'<a href=\"'+watch+'\" target=\"_blank\" rel=\"noopener\" "
                   "style=\"position:absolute;bottom:8px;left:12px;color:#fff;opacity:.8;"
                   "font-size:12px;text-decoration:underline;z-index:5;\">Open</a>':'');});})();")


def main():
    out_file = OUT_COMPRESSED if COMPRESS_MODE else OUT_FILE
    skip_roots = ("wp-content", "wp-includes", "wp-json",
                  "cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com")
    content_pages = []
    for p in SITE.rglob("index.html"):
        rel = p.relative_to(SITE).as_posix()
        if rel == "index.html":
            continue
        if rel.split("/")[0] in skip_roots:
            continue
        content_pages.append(p)
    href_targets = {page_slug(p.relative_to(SITE).as_posix()) for p in content_pages}

    homepage = (SITE / "index.html").read_text(encoding="utf-8", errors="ignore")
    hp_meta = re.search(r"<title>(.*?)</title>", homepage, re.S)
    hp_title = hp_meta.group(1).strip() if hp_meta else "CFA Level 1 Study Notes (Offline)"

    # ---- css/js bundles from the homepage head, in DOM order ----
    head_m = re.search(r"<head>(.*?)</head>", homepage, re.S | re.I)
    head_inner = head_m.group(1) if head_m else ""
    bundle_css, bundle_js = [], []
    bundle_js.insert(0, VIDEO_PLAYER_JS)

    for m in re.finditer(r"<(link|script|style)\b([^>]*)>", head_inner, re.S):
        kind, attrs = m.group(1), m.group(2)
        if kind == "style":
            inner_end = head_inner.find("</style>", m.end())
            inner = head_inner[m.end():inner_end] if inner_end != -1 else ""
            bundle_css.append(rewrite_css(inner, SITE))
            continue
        if kind == "link":
            href_m = re.search(r'href="([^"]*)"', attrs)
            if not href_m:
                continue
            rel_m = re.search(r'rel="([^"]*)"', attrs)
            if rel_m and "stylesheet" not in rel_m.group(1):
                continue
            f = resolve_site_file(href_m.group(1), SITE)
            if f and f.suffix == ".css":
                bundle_css.append(rewrite_css(f.read_text(encoding="utf-8", errors="ignore"), f))
        else:
            src_m = re.search(r'src="([^"]*)"', attrs)
            if src_m:
                f = resolve_site_file(src_m.group(1), SITE)
                if f:
                    bundle_js.append(f.read_text(encoding="utf-8", errors="ignore"))
            else:
                type_m = re.search(r'type="([^"]*)"', attrs)
                if type_m and type_m.group(1).lower() not in (
                        "", "text/javascript", "application/javascript", "module"):
                    continue  # application/ld+json, application/json, ...: not JS
                inner_end = head_inner.find("</script>", m.end())
                inline = head_inner[m.end():inner_end] if inner_end != -1 else ""
                bundle_js.append(inline)

    # ---- articles & shell: refs rewritten; images deduped via a registry ----
    registry = {}
    page_styles = {}
    chunks, current_chunk, current_bytes = [], [], 0
    for p in sorted(content_pages, key=lambda x: x.relative_to(SITE).as_posix()):
        html = p.read_text(encoding="utf-8", errors="ignore")
        title_m = re.search(r"<title>(.*?)</title>", html, re.S)
        article = extract_article(html)
        if article is None:
            print(f"WARN no article extracted: {p.name}")
            continue
        slug = page_slug(p.relative_to(SITE).as_posix())
        article = rewrite_body_refs(article, p.parent, href_targets, registry)
        # keep the page's own Notes Navigation sidebar alongside the article:
        # the single-file shell is the homepage, which has no such sidebar
        from bs4 import BeautifulSoup  # noqa: PLC0415
        soup = BeautifulSoup(html, "html.parser")
        sb_div = soup.find(class_="x-sidebar")  # aside or div
        sb = "".join(map(str, sb_div.contents)) if sb_div else ""
        sb_cls = " ".join(sb_div.get("class") or []) if sb_div else ""
        if sb:
            sb = rewrite_body_refs(sb, p.parent, href_targets, registry)
        # the homepage shell is a full-width template: its body classes (e.g.
        # page-template-template-layout-full-width-php) pin .x-main to width:auto
        # via ".page-template-...-php .x-main{width:auto}". Every routed page
        # must carry its own body classes (page-template-default +
        # x-content-sidebar-active) or its 80% content column collapses to full
        # width. The alternative (override in CSS) is brittle: these selectors
        # are 0-2-0 and any customizer reorder breaks it again.
        page_body_m = re.search(r'<body\b[^>]*class="([^"]*)"', html)
        page_body_cls = page_body_m.group(1) if page_body_m else ""
        # collect this page's inline <style> blocks (customizer CSS drives
        # e.g. the Notes Navigation current-item highlight) - the homepage
        # shell alone does not carry them
        for st_m in re.finditer(r"<style\b[^>]*>(.*?)</style>", html, re.S):
            inner = st_m.group(1).strip()
            if inner and len(inner) > 80:
                key = abs(hash(inner))
                if key not in page_styles:
                    page_styles[key] = minify_css(rewrite_css(inner, SITE))

        # the page's main-container class list drives the column rules
        # (.x-main.full = 100% width, .x-main.left = 80% + sidebar column) -
        # the homepage shell alone would stretch article banners full-width
        main_classes = ""
        m_div = soup.find(class_="x-main")
        if m_div:
            main_classes = " ".join(m_div.get("class") or [])
        item_json = json.dumps({"s": slug,
                                "t": title_m.group(1).strip() if title_m else slug,
                                "h": article,
                                "n": sb,
                                "m": main_classes,
                                "b": page_body_cls,
                                "c": sb_cls}, ensure_ascii=True)
        # JSON strings must never contain a literal </script> (it would close
        # the wrapping <script> tag and break parsing)
        if "</script" in item_json or "<script" in item_json:
            item_json = item_json.replace("</script", "<\\/script").replace("<script", "<\\u003cscript")
        if current_bytes + len(item_json) > CHUNK_BYTES and current_chunk:
            chunks.append(current_chunk)
            current_chunk, current_bytes = [], 0
        current_chunk.append(item_json)
        current_bytes += len(item_json)
    if current_chunk:
        chunks.append(current_chunk)

    # ---- shell body (keep <body> attributes: the theme styles against them) ----
    body_m = re.search(r"<body([^>]*)>(.*)</body>", homepage, re.S | re.I)
    shell_body = rewrite_body_refs(body_m.group(2) if body_m else "", SITE, href_targets, registry)
    body_attrs = " " + body_m.group(1).strip() if body_m and body_m.group(1).strip() else ""

    # serialize the image registry as {"key":"data uri", ...} pairs, chunked
    img_chunks, cur, cur_n = [], [], 0
    for k in registry:
        pair = f"{json.dumps(k)}:{json.dumps(b64(SITE / k, COMPRESS_MODE))}"
        if cur_n + len(pair) > CHUNK_BYTES and cur:
            img_chunks.append(cur)
            cur, cur_n = [], 0
        cur.append(pair)
        cur_n += len(pair)
    if cur:
        img_chunks.append(cur)

    css_bundle = "\n".join(bundle_css + list(page_styles.values()))
    # no featured-thumb override: the theme CSS + the image's own intrinsic
    # ratio must size the banner exactly as in the multi-file pages (a fixed
    # ratio meant every banner got the same 31.2% geometry). The body-class /
    # x-main.left restore below is what keeps the banner inside the 80% column.

    data_scripts = "\n".join(
        f'<script>window.__PN_CHUNK_{i} = [{",".join(chunk)}];</script>'
        for i, chunk in enumerate(chunks))
    data_scripts += f'\n<script>window.__PN_CHUNKS = {len(chunks)};</script>'
    data_scripts += "\n".join(
        f'<script>window.__PN_IMG_{i} = {{{",".join(chunk)}}};</script>'
        for i, chunk in enumerate(img_chunks))
    data_scripts += f'\n<script>window.__PN_IMG_CHUNKS = {len(img_chunks)};</script>'

    router_js = """<script>
(function () {
  "use strict";
  var PAGES = {};
  for (var i = 0; i < window.__PN_CHUNKS; i++) {
    var arr = window["__PN_CHUNK_" + i];
    if (!arr) { continue; }
    for (var j = 0; j < arr.length; j++) {
      if (arr[j].s != null && !(arr[j].s in PAGES)) { PAGES[arr[j].s] = { t: arr[j].t, h: arr[j].h, n: arr[j].n || '', m: arr[j].m || '', b: arr[j].b || '', c: arr[j].c || '' }; }
    }
    window["__PN_CHUNK_" + i] = null;
  }
  delete window.__PN_CHUNKS;
  var IMG = {};
  for (var i2 = 0; i2 < window.__PN_IMG_CHUNKS; i2++) {
    var o = window["__PN_IMG_" + i2];
    if (o) { for (var k in o) { IMG[k] = o[k]; } }
    window["__PN_IMG_" + i2] = null;
  }
  delete window.__PN_IMG_CHUNKS;
  window.__PN_DEBUG = { PAGES: PAGES, IMG: IMG };
  function applyImages(root) {
    var imgs = (root || document).querySelectorAll('img[data-pn-img]');
    for (var i3 = 0; i3 < imgs.length; i3++) {
      var key = imgs[i3].getAttribute('data-pn-img');
      if (IMG[key]) { imgs[i3].src = IMG[key]; }
      else {
        (window.__PN_BAD = window.__PN_BAD || []).push({
          key: key, codes: key.split('').map(function (c) { return c.charCodeAt(0); })
        });
        imgs[i3].removeAttribute('data-pn-img');
      }
    }
  }
  var INIT = { article: null, title: document.title, mainClass: '', bodyClass: document.body.className };
  var MAIN = document.querySelector('.x-main');
  if (MAIN) { INIT.mainClass = MAIN.className; }
  function captureInit() {
    var art = document.querySelector('article[id^="post-"]');
    if (art) { INIT.article = art.outerHTML; }
  }
  function render(slug) {
    if (!slug) {
      // back to the static homepage: restore its original chrome + content
      var cur = document.querySelector('article[id^="post-"]');
      if (cur && INIT.article) { cur.outerHTML = INIT.article; }
      if (MAIN && INIT.mainClass) { MAIN.className = INIT.mainClass; }
      document.body.className = INIT.bodyClass;
      document.title = INIT.title;
      restoreSidebar('', '', false);
      applyImages(document);
      window.scrollTo(0, 0);
      return;
    }
    var page = PAGES[slug];
    if (!page) { return; }
    var art = document.querySelector('article[id^="post-"]');
    if (!art) { return; }
    art.outerHTML = '<article id="post-' + slug.replace(/[^A-Za-z0-9_-]/g, "")
                    + '" class="pn-single-file-page">' + page.h + '</article>';
    if (page.m && MAIN) { MAIN.className = page.m; }
    if (page.b) { document.body.className = page.b; }
    if (page.t) { document.title = page.t; }
    restoreSidebar(page.n || '', page.c, !!page.n);
    var fresh = document.querySelector('article[id^="post-"]');
    if (fresh) {
      applyImages(fresh);
      var scripts = fresh.querySelectorAll('script');
      for (var s = 0; s < scripts.length; s++) {
        try { (0, eval)(scripts[s].textContent); } catch (e) { /* non-fatal */ }
      }
    }
    window.scrollTo(0, 0);
  }
  function restoreSidebar(navHtml, navCls, show) {
    var host = document.getElementById('pn-sidebar');
    if (!host) { return; }
    host.innerHTML = navHtml;
    if (navCls) { host.className = navCls; }
    host.style.display = show ? '' : 'none';  // homepage has no sidebar at all
  }
  function placeSidebar() {
    var host = document.getElementById('pn-sidebar');
    if (!host) {
      host = document.createElement('div');
      host.id = 'pn-sidebar';
      // no inline sizing: the theme CSS widths it, same as the page's own
      // .x-sidebar (inline styles would win over the customizer and break
      // the content 80% / sidebar calc(100%-2.463%-80%) split)
      host.className = 'x-sidebar right';
    }
    if (!host.parentNode) {
      // sibling AFTER .x-main, exactly where the original pages place
      // .x-sidebar: as a child of .x-main it would take its 17.5% from the
      // 80% column (165px) instead of the outer container (213px), and on
      // mobile it would stack above the article instead of below it
      var main = document.querySelector('.x-main');
      if (main && main.parentNode) { main.parentNode.insertBefore(host, main.nextSibling); }
      else { document.body.appendChild(host); }
    }
  }
  placeSidebar();
  captureInit();
  applyImages(document);
  function fromHash() {
    var h = location.hash.replace(/^#\\/?/, "");
    var slug = decodeURIComponent(h.split("#")[0]).replace(/\\/$/, "");
    render(slug);
  }
  window.addEventListener("hashchange", fromHash);
  if (location.hash && location.hash !== "#/") { fromHash(); }
})();
</script>"""

    parts = [
        '<!DOCTYPE html>\n<html class="no-js" lang="en-US">\n<head>\n',
        '<meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>',
        "<title>%s</title>" % hp_title,
        # one <style> per original file: a parse error inside one file cannot
        # swallow the rules of the files that follow it; per-page inline styles
        # (customizer CSS) ride along
        *[f"<style>{c}</style>" for c in bundle_css + list(page_styles.values())],
        # one <script> per original file, placed in <head> (their original
        # position): body inline scripts rely on jQuery being defined first
        *[f"<script>{j}</script>" for j in bundle_js],
        "</head>\n<body" + body_attrs + ">\n",
        shell_body,
        'style="position:fixed;bottom:4px;left:8px;z-index:9999;font-size:11px;color:#888;'
        'background:rgba(255,255,255,.85);padding:2px 8px;border-radius:4px;'
        'box-shadow:0 1px 2px rgba(0,0,0,.15);">CFA offline build v2026-09-07</div>',
        "\n" + data_scripts + "\n",
        router_js,
        "\n</body></html>\n",
    ]
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts))
    print(f"done: {out_file.name} = {os.path.getsize(out_file) / 1e6:.1f} MB, "
          f"pages={len(content_pages)}, chunks={len(chunks)}, "
          f"css_bundle={len(css_bundle) / 1e6:.1f} MB, js_files={len(bundle_js)}")


if __name__ == "__main__":
    main()



