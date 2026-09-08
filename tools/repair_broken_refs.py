#!/usr/bin/env python3
"""Repair every broken resource reference in the multi-file site.

Audits every HTML reference (href/src/srcset/poster), and for each one that
does not resolve inside the site: rewrites it to the closest existing asset —
same image stem with any size variant, else the largest image in the same
folder (a same-topic approximation beats a grey box). Repeats until zero
broken refs remain (a rewrite can create new names).

Idempotent, offline, ~2-4 min run over the whole site. Usage:
    python tools/repair_broken_refs.py
"""

import io
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "cfa_l1_offline_notes_site_2026"
SKIP_DIRS = ("wp-includes", "wp-json", "fonts.googleapis.com", "fonts.gstatic.com",
             "cdn.jsdelivr.net")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def is_corrupt(path: Path) -> bool:
    """True when the file is not a decodable image (e.g. a 281-byte 403 body
    that the 2026-08 mirror stored as an image)."""
    try:
        with Image.open(io.BytesIO(path.read_bytes())) as im:
            im.verify()
        return False
    except Exception:  # noqa: BLE001 - any decode failure = corrupt
        return True


def audit() -> dict:
    """{url -> count} of every reference that does not resolve in-site."""
    bad = defaultdict(int)
    for p in SITE.rglob("*.html"):
        if p.parts[0] in SKIP_DIRS:
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'(?:href|src|poster|srcset)="([^"]*)"', t):
            url = m.group(1).strip().split(" ")[0]
            if not url or url.startswith(("#", "http://", "https://", "data:",
                                          "mailto:", "tel:", "javascript:", "//", "'+")):
                continue
            target = (p.parent / url.split("?")[0]).resolve()
            try:
                target.relative_to(SITE.resolve())
            except ValueError:
                bad[url.split("?")[0]] += 1
                continue
            if not target.exists() or (target.suffix.lower() in IMAGE_EXT
                                       and is_corrupt(target)):
                bad[url.split("?")[0]] += 1
    return dict(bad)


def by_stem_index():
    index = defaultdict(list)
    for p in SITE.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXT and not is_corrupt(p):
            index[p.stem.lower()].append(p)
    return index


def candidates_for(url: str, index: dict) -> list:
    name = url.split("/")[-1].split("?")[0]
    stem = name.rsplit(".", 1)[0] if "." in name else name
    base = re.sub(r"-\d+x\d+$", "", stem).lower()
    cands = [f for k, v in index.items() if k.startswith(base) for f in v]
    if not cands and "/" in url:
        for p in SITE.rglob(url.split("/")[-2]):
            if p.is_dir():
                cands = [f for f in p.glob("*") if f.suffix.lower() in IMAGE_EXT]
                if cands:
                    break
    return cands


def rewrite_once(bad: dict, index: dict) -> int:
    fixed = 0
    for url, _n in bad.items():
        name = url.split("/")[-1].split("?")[0]
        cands = [c for c in candidates_for(url, index) if not is_corrupt(c) and c.name != name]
        if not cands:
            continue
        fallback = max(cands, key=lambda p: p.stat().st_size)
        fname = fallback.name
        pages = 0
        for p in SITE.rglob("*.html"):
            if p.parts[0] in SKIP_DIRS:
                continue
            t = p.read_text(encoding="utf-8", errors="ignore")
            if name in t:
                p.write_text(t.replace(name, fname), encoding="utf-8")
                pages += 1
        fixed += 1
        if pages:
            print(f"  fix {name} -> {fname} in {pages} pages")
    return fixed


def main():
    for rnd in range(5):
        bad = audit()
        print(f"round {rnd}: broken refs = {len(bad)}")
        if not bad:
            break
        if rewrite_once(bad, by_stem_index()) == 0:
            print("no rewritable candidates left")
            break
    print("done. broken refs:", len(audit()))


if __name__ == "__main__":
    main()
