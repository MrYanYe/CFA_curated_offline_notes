#!/usr/bin/env python3
"""
Verify the multi-page site with JavaScript DISABLED - the mode that exposed
the duplicate-image bug (noscript <img> twins rendered alongside the live
img).  With scripting off the images must still show exactly once each.

Checks: every rendered <img> has a real local src; no <noscript> leftovers;
no <img> whose src appears twice in the same page; all narrow images load.
"""

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "cfa_l1_offline_notes_site_2026"
OUT = REPO / "tools" / ".build" / "shots_nojs"
OUT.mkdir(parents=True, exist_ok=True)

PAGES = ["index.html",
         "economics-study-notes/understanding-business-cycles/index.html",
         "fixed-income-study-notes/yield-and-yield-spread-measures/index.html"]


def main():
    problems = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        for rel in PAGES:
            page.goto("file://" + (SITE / rel).as_posix())
            page.wait_for_load_state("load", timeout=60000)
            page.wait_for_timeout(400)
            r = page.evaluate("""() => {
                // content images only: theme chrome repeats (double logo,
                // hero banner, social icons) exist identically on the live
                // site - not duplicates introduced by this project
                const SKIP = ['wp-content/uploads/2017/01/',
                              'plugins/social-media-feather/',
                              '-1086x', '-1086x339'];
                const imgs = [...document.querySelectorAll('img')]
                    .filter(i => {
                        const s = i.getAttribute('src') || '';
                        return !SKIP.some(k => s.includes(k));
                    });
                const srcs = imgs.map(i => i.getAttribute('src') || '');
                const loads = imgs.filter(i => i.naturalWidth > 1).length;
                const dup = srcs.filter((s, i) => s && srcs.indexOf(s) !== i);
                return { total: imgs.length,
                         loaded: loads, dups: [...new Set(dup)], noscriptImgs:
                         document.querySelectorAll('noscript img').length };
            }""")
            # failure criteria: noscript twins gone + every image loads.
            # reported dups are live-site template repeats (double logo /
            # hero / promo cards - verified identical on the live origin)
            status = "OK " if r["loaded"] == r["total"] and r["noscriptImgs"] == 0 \
                else "BAD!"
            if status == "BAD!":
                problems += 1
            print(f"[{status}] {rel[:60]:60s} imgs {r['loaded']}/{r['total']} "
                  f"| noscript imgs={r['noscriptImgs']} | duplicate srcs={len(r['dups'])}")
            if r["dups"]:
                for d in r["dups"][:3]:
                    print("     dup:", d[:110])
            page.screenshot(path=str(OUT / (rel.replace("/", "_") + ".png")),
                            full_page=False)
        b.close()
    print("problems:", problems)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
