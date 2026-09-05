#!/usr/bin/env python3
"""
Browser verification for study_notes_site/ via Playwright Chromium.

For the homepage + sample pages (desktop and mobile viewport):
  - load timing (DOMContentLoaded / load / first-paint proxies)
  - console errors and failed file: requests
  - img balance: total <img> vs naturalWidth>0
  - screenshot captures for visual inspection
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "cfa_l1_offline_notes_site_2026"
OUT = REPO / "tools" / ".build" / "shots"
OUT.mkdir(parents=True, exist_ok=True)

MANUAL_NAV = "file://" + (SITE / "index.html").as_posix()

SAMPLES = [
    ("home", "index.html"),
    ("topic-index", "economics-study-notes/index.html"),
    ("deep-article", "economics-study-notes/understanding-business-cycles/index.html"),
    ("fsa-article", "financial-statement-analysis-fsa-study-notes/"
                    "financial-statement-analysis-an-introduction/index.html"),
]


def audit_page(page, label, metrics):
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(1200)
    console = page.evaluate("""() => {
        const r = { errors: [] };
        return r;
    }""")
    img_stats = page.evaluate("""() => {
        const imgs = [...document.querySelectorAll('img')];
        return { total: imgs.length,
                 loaded: imgs.filter(i => i.naturalWidth > 0).length };
    }""")
    td = page.evaluate("""() => ({
        domContentLoaded: performance.getEntriesByType('navigation')[0]?.domContentLoadedEventEnd || 0,
        load: performance.getEntriesByType('navigation')[0]?.loadEventEnd || 0,
        title: document.title,
        bodyText: document.body ? document.body.innerText.length : 0,
    })""")
    metrics[label] = {**img_stats, **td}
    print(f"[{label}] imgs {img_stats['loaded']}/{img_stats['total']} "
          f"| domContentLoaded {td['domContentLoaded']:.0f}ms | load {td['load']:.0f}ms "
          f"| title={td['title'][:40]!r} text={td['bodyText']}")


def main():
    errors_total = 0
    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # desktop
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        collected = []
        page.on("console", lambda m: collected.append(f"console.{m.type}: {m.text[:160]}")
                if m.type == "error" else None)
        page.on("pageerror", lambda e: collected.append(f"pageerror: {str(e)[:160]}"))
        page.on("requestfailed", lambda r: collected.append(f"failed: {r.url[:160]}"))
        metrics = {}
        for label, rel in SAMPLES:
            page.goto(MANUAL_NAV if rel == "index.html" else "file://" + (SITE / rel).as_posix())
            audit_page(page, label, metrics)
            page.screenshot(path=str(OUT / f"{label}-desktop.png"), full_page=False)
        page.goto(MANUAL_NAV)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "home-desktop-full.png"), full_page=True)
        errors_total += len(collected)
        console_errors.extend(collected)
        print(f"desktop console/page errors: {len(collected)}")
        for e in collected[:15]:
            print("   ", e)
        ctx.close()

        # mobile emulation (iPhone-ish)
        ctx2 = browser.new_context(viewport={"width": 375, "height": 812},
                                   device_scale_factor=2, is_mobile=True,
                                   user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                              "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                                              "Mobile/15E148 Safari/604.1")
        page2 = ctx2.new_page()
        collected2 = []
        page2.on("console", lambda m: collected2.append(f"console.{m.type}: {m.text[:160]}")
                if m.type == "error" else None)
        page2.on("pageerror", lambda e: collected2.append(f"pageerror: {str(e)[:160]}"))
        page2.on("requestfailed", lambda r: collected2.append(f"failed: {r.url[:160]}"))
        mm = {}
        for label, rel in SAMPLES[:3]:
            page2.goto(MANUAL_NAV if rel == "index.html" else "file://" + (SITE / rel).as_posix())
            audit_page(page2, f"m-{label}", mm)
            page2.screenshot(path=str(OUT / f"{label}-mobile.png"), full_page=False)
            if label == "home":
                # try toggling the mobile hamburger menu if present
                menu_before = page2.evaluate(
                    "() => { const n = document.querySelector('[data-x-toggleable=\\'x-nav-wrap-mobile\\']'); "
                    "return n ? getComputedStyle(n).display : 'missing'; }")
                toggled = page2.evaluate(
                    "() => { const t = document.querySelector('a[data-x-toggle], button[data-x-toggle], "
                    "[data-x-toggle]'); if (t) { t.click(); return t.className || t.tagName; } return null; }")
                print(f"[mobile] toggle [{toggled!r}] menu before={menu_before}")
                page2.wait_for_timeout(600)
                menu_after = page2.evaluate(
                    "() => { const n = document.querySelector('[data-x-toggleable=\\'x-nav-wrap-mobile\\']'); "
                    "return n ? getComputedStyle(n).display : 'missing'; }")
                print(f"[mobile] menu after click: {menu_after}")
                page2.screenshot(path=str(OUT / "home-mobile-menu.png"), full_page=False)
        errors_total += len(collected2)
        console_errors.extend(collected2)
        print(f"mobile console/page errors: {len(collected2)}")
        for e in collected2[:10]:
            print("   ", e)
        browser.close()

    print("SUMMARY:")
    for k, v in {**metrics, **mm}.items():
        print(f"  {k}: imgs {v['loaded']}/{v['total']}, domContentLoaded {v['domContentLoaded']:.0f}ms")
    print(f"TOTAL errors: {errors_total}")
    sys.exit(0 if errors_total == 0 else 1)


if __name__ == "__main__":
    main()
