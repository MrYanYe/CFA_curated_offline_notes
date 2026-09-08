#!/usr/bin/env python3
"""Localize protocol-relative //... references in the multi-file site
(after the 2026-09 fixes) and drop tracker tags that survived.

The X theme emits href='//prepnuggets.com/...' with single quotes. The
pre-2026-09-08 build rewrite handled only double quotes, so these stayed
as '//...' and file:// browsers resolved them to file://prepnuggets.com/...
(fails -> whole theme CSS missing -> unstyled pages with a flat menu).

For every html file:
  - tracker tags (cleantalk/sharethis/googletagmanager/etc) are removed
  - '//prepnuggets.com/...', cdn.jsdelivr.net, fonts.googleapis.com/gstatic
    refs are rewritten to their local file if one exists, else https://
  - any other '//host' attr ref becomes https://

Usage: python tools/fix_protocol_relative_refs.py
"""

import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "cfa_l1_offline_notes_site_2026"
SKIP_DIRS = ("wp-includes", "wp-json", "fonts.googleapis.com", "fonts.gstatic.com",
             "cdn.jsdelivr.net")

# '//host/...' quoted refs, either quote style, anywhere in a tag attribute zone
REF_IN_ATTR = re.compile(r"""(["'])(//[^"']+)\1""")
LOCAL_PREFIX = "/cfa-level-1-study-notes"
# tracker hosts: the cleaned site must never (attempt to) load them
TRACKER_HOSTS = ("fd.cleantalk.org", "ws.sharethis.com", "www.googletagmanager.com",
                 "platform.twitter.com", "graph.facebook.com")
TRACKER_TAG_RE = re.compile(
    r"<(?:script|link|img)\b[^>]*\bsrc\s*=\s*[\"']//(?:" + "|".join(TRACKER_HOSTS) +
    r")[^\"']*[\"'][^>]*>")


def main():
    n = 0
    for p in SITE.rglob("*.html"):
        if p.parts[0] in SKIP_DIRS:
            continue
        data = p.read_text(encoding="utf-8", errors="ignore")
        original = data
        data = TRACKER_TAG_RE.sub("", data)

        def sub(m):
            quote, url = m.group(1), m.group(2)
            rest = url[2:]  # strip //
            host = rest.split("/")[0]
            path = rest.split("?")[0].split("/", 1)[1] if "/" in rest else ""
            if host == "prepnuggets.com" and path.startswith(LOCAL_PREFIX):
                path = path[len(LOCAL_PREFIX):]
            if host in ("prepnuggets.com", "cdn.jsdelivr.net",
                        "fonts.googleapis.com", "fonts.gstatic.com"):
                local = SITE / host / path.lstrip("/")
                if local.is_file():
                    rel = os.path.relpath(local, p.parent).replace("\\", "/")
                    return quote + rel + quote
                local2 = SITE / path.lstrip("/")  # prepnuggets assets park at root
                if local2.is_file():
                    rel = os.path.relpath(local2, p.parent).replace("\\", "/")
                    return quote + rel + quote
            # no local counterpart (wp-login.php, ?p=..., external page): https
            return quote + "https:" + url + quote

        data = REF_IN_ATTR.sub(sub, data)
        if data != original:
            p.write_text(data, encoding="utf-8")
            n += 1
    print(f"pages updated: {n}")
    left = 0
    for p in SITE.rglob("*.html"):
        if p.parts[0] in SKIP_DIRS:
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"""["']//""", t):
            left += 1
    print(f"pages still containing quoted '//' refs: {left}")


if __name__ == "__main__":
    main()
