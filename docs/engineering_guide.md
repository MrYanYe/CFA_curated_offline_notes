# CFA Level 1 Offline Notes — Engineering Guide

> Full engineering documentation for reproducing, running, verifying and
> modifying the project — written for engineers and coding agents.
> English first; 中文版本在英文部分之后.

---

## 0. What this project is

A fully-offline mirror of **https://prepnuggets.com/cfa-level-1-study-notes/** —
CFA Level 1 study notes site (2026 curriculum, 387 article pages + homepage,
~4000 images). Deliverables:

| Deliverable | Form | Entry / size |
|---|---|---|
| `cfa_l1_offline_notes_site_2026/` | multi-file static site | `…/index.html` (309 MB) — desktop-only rendering guaranteed |
| `cfa_l1_offline_notes_all_in_one_2026.html` | single file (hash routing) | the file (143.8 MB) — **preferred, best compatibility** |
| `cfa_l1_offline_notes_all_in_one_2026_compressed.html` | single file, JPEG q60 | the file (93.3 MB, <100 MB) |
| `cfa_l1_offline_notes_all_in_one_2026.html.zip` | plain zip (96.8 MB; compression got below 100 MB, so no volumes) | repo root |

### Git branches

- `master` — deliverable state. **Contains NO `prepnuggets_raw_mirror`**
  (build input, 4924 files / 309 MB). Rebuilds that need the mirror:
  `git checkout mirror-archive`.
- `mirror-archive` — keeps `prepnuggets_raw_mirror` intact.

### Size budget policy

- `cfa_l1_offline_notes_all_in_one_2026.html` (>100 MB) is **gitignored** and
  delivered as split-volume zip. `…_compressed.html` (93.3 MB) stays tracked.
- Shipped paths stay under the Windows 260-char MAX_PATH even in deeply
  nested copy targets (measured: 219 chars at this checkout; ~178 rel to
  repo root → 82-char budget for the copy target root).

---

## 1. Repository layout

```
cfa_curated_offline_notes/                     ← repo root
├── README.md                             ← user docs (bilingual, EN first)
├── docs/
│   ├── engineering_guide.md              ← this file
│   ├── slug_rename_map.md                ← old→new compressed segment names
│   └── readme_images/                    ← verification screenshots
├── cfa_l1_offline_notes_site_2026/       ← deliverable ① (built)
├── cfa_l1_offline_notes_all_in_one_2026.html               ← deliverable ② (gitignored)
├── cfa_l1_offline_notes_all_in_one_2026_compressed.html
├── cfa_l1_offline_notes_all_in_one_2026/ ← split-volume zip (gitignored)
├── serve_local.cmd                       ← Windows double-click local viewer
├── tools/
│   ├── build_site.py                     ← mirror → multi-file site
│   ├── build_single_file.py              ← site → single file(s)
│   ├── fetch_missing.py                  ← re-download missing assets (curl, Referer)
│   ├── fetch_new_pages.py                ← REST diff + page/assets backfill
│   ├── verify_links.py                   ← static gate (quote-agnostic)
│   ├── verify_browser.py                 ← Playwright smoke + screenshots
│   ├── verify_no_js.py                   ← duplicate-image count with JS off
│   ├── repair_broken_refs.py             ← audit→nearest-valid-image loop (0-broken target)
│   ├── fix_protocol_relative_refs.py     ← localize //host refs, drop tracker tags
│   ├── dedupe_image_duplicates.py        ← per-page one-copy dedupe helper
│   ├── fill_image_gaps.py / _loop.py     ← gap fill helpers
│   ├── serve.py                          ← local HTTP server (inline video)
│   └── .build/                           ← gitignored scratch: reports, shots
│       ├── verify_single_file_cross_device.py    ← 5-context + identity suite
│       └── *.txt                         ← generated lists/reports
└── prepnuggets_raw_mirror/               ← ONLY on branch mirror-archive
```

---

## 2. Pipeline in full detail

```
raw mirror ──► build_site.py ──► multi-file site ──► verify_links.py
     │                │                                  │
     │                └──► build_single_file.py ──► single file(s)
     │                                                  │
fetch_new_pages.py / fetch_missing.py / repair_broken_refs.py
     └────────────── repairs (offline or network) ──────┘
```

### 2.1 Full reproduce sequence

```bash
cd cfa_curated_offline_notes

# 0) get the mirror (only on the archive branch)
git checkout mirror-archive          # or: git checkout mirror-archive -- prepnuggets_raw_mirror

# 1) build the multi-file site (deterministic, wipes the site dir)
python tools/build_site.py

# 2) network backfill, in order
python tools/fetch_new_pages.py      # REST diff: new/changed pages + their assets
python tools/fetch_missing.py        # missing assets (curl, Referer, bounded)
python tools/fix_protocol_relative_refs.py   # //host refs + tracker tags (offline)
python tools/repair_broken_refs.py   # audit→nearest-valid loop until "broken refs: 0"

# 3) gate
python tools/verify_links.py         # MUST print ALL CLEAN

# 4) single-file builds
python tools/build_single_file.py            # lossless original
python tools/build_single_file.py --compress # JPEG q60/threshold 50KB → <100 MB

# 5) runtime verification
python tools/.build/verify_single_file_cross_device.py            # 5 contexts + 7 routes
python tools/.build/verify_single_file_cross_device.py --identity # content equality only

# 6) optional: local viewer
python tools/serve.py
```

Timing on a dev machine: build_site ~3 min; fetch steps 5–20 min (network
dominated); repair ~3–6 min; verify_links ~1 min; single builds ~4 min each;
full suite ~20 min (7 routes × 5 contexts).

### 2.2 Tool-by-tool contract

| Tool | Input | Output | Key facts |
|---|---|---|---|
| `build_site.py` | mirror | site_2026 | wipes site; per-page cleanup order: remote tags → video boxes → lazyload expand → URL mapping (quote-agnostic) → fonts/css localize; writes `tools/.build/build_report.json`; deterministic |
| `fetch_new_pages.py` | live REST + site | mirror additions + downloaded assets | MIRROR const must point at `prepnuggets_raw_mirror`; scans pages + lazyload attrs |
| `fetch_missing.py` | build_report.json | site files | curl.exe with `--connect-timeout 6 --max-time 25` + **Referer** (hotlink protection!); extension whitelist skips page-like entries; size_candidates tries base file after derivative |
| `fix_protocol_relative_refs.py` | site html/css | localized refs | both quote styles; prepnuggets/jsdelivr/fonts → local relpath if exists else `https:`; TRACKER_HOSTS tags dropped |
| `repair_broken_refs.py` | site | rewritten refs | audit (missing + PIL-undecodable) → candidates: same-stem valid variants >> same-folder non-brand; brand badges dropped (tags removed); exact-URL replacement (no recursion); loops ≤5; target 0 |
| `verify_links.py` | site | PASS/FAIL | quote-agnostic attr regex; checks existence, case-sensitivity, external allowlist, protocol-relative leftover, remote tags, lazy placeholders |
| `verify_single_file_cross_device.py` | single + site | report | contexts: chromium desktop/Android phone/Android tablet, webkit desktop/iOS; routes: home, economics/understanding-cycles, fsa/financial-introduction, economics topic, quant-methods/probability-concepts/joint-rule, portfolio/…/returns-beta, ethics/guidance-vii; identity mode compares article innerText |
| `serve.py` | site | localhost viewer | prints LAN URL for phones; inline-iframes videos over http(s) |

### 2.3 build_report.json schema

```json
{
  "cleaned_pages": ["economics/understanding-cycles/index.html", ...],
  "externalized_urls": [[ "local/path", "https://original" ], ...],
  "assets_missing_from_mirror": [[ "site/relative/path", "https://original" ], ...]
}
```
- `externalized_urls`: page-like URLs (`.php`/`.json`/no-extension) whose raw
  mirror counterpart is absent → kept as external links (fed/glossary/privacy).
- `assets_missing_from_mirror`: 6000+ entries incl. URL-alias accounting
  (page URLs under renamed topics) — only entries with an asset extension are
  fetchable; the rest are skip-listed.

---

## 3. Architecture

### 3.1 Multi-file site (`build_site.py`)

Core: `map_url_to_local(full, rename_css) -> (site_path, mirror_file_exists)`.
Every href/src/srcset/poster/css url goes through it and is re-emitted as a
**relative** path from the page's final location. Cleanup per page:

1. strip remote `<script>/<link>/<img>/<iframe>` (non-local hosts + CleanTalk
   inline scripts) — quote-agnostic
2. replace YouTube/Vimeo `<iframe>` with `.pn-video-player` (click-to-play
   behavior: file:// → watch tab, http(s) → inline embed; keep the two player
   JS copies in `build_site.video_player_script()` and
   `build_single_file.VIDEO_PLAYER_JS` **byte-identical**)
3. expand WP-Rocket lazyload: grey svg placeholder → real local path
   (placeholder src/srcset, `data-lazy-*`, noscript twins)
4. rewrite every URL attr via `map_url_to_local` (both `'` and `"` quote forms)
5. fonts: localize google fonts css + `url(//fonts.gstatic.com/…)`; `%`-escaped
   filenames get safe names; `dist/index.html` etc. get content pages

### 3.2 Single file (`build_single_file.py`)

= homepage `<body>` shell + chunked JSON of every other page + base64 registry.

- **Shell**: cleaned homepage body (header/nav chrome); CSS bundle 34.8 MB
  (per-file `<style>` blocks, deduped by content hash, minified).
- **Per-page JSON** (chunks of 4,000,000 bytes):
  `{s: slug, t: title, h: article, n: sidebar html, m: x-main classes,
    b: body classes, c: sidebar classes}`
- **Registry**: `IMG[site-relative-key] = base64 data uri`. `<img>` tags are
  rewritten to a 1×1 GIF + `data-pn-img="key"`; `applyImages()` fills bytes at
  runtime. Only the **src** size variant is embedded; srcset is stripped
  (`PUFFY_GIF` placeholder). `__PN_BAD` records unresolved keys.
- **Router**: `hashchange → render(slug)`: swap `<article>`, set `.x-main`
  class (`m`), set `<body>` class (`b`), inject sidebar into `#pn-sidebar`
  (`n` + `c`), title, scroll top; empty hash/`#/` restores the homepage via
  `captureInit()`/`INIT`.
- **Sidebar placement**: sibling AFTER `.x-main` (matches original DOM order);
  no inline width — theme customizer CSS sizes it
  (`.x-sidebar{width:calc(100% - 2.463% - 80%)}` → 213.234px at desktop).

### 3.3 Path compression (three rounds — all naming below is intentional)

Outer names never change (user requirement). Inner dirs compressed for
Windows MAX_PATH safety:

| Round | What | Rule |
|---|---|---|
| 1 | `PATH_RENAMES` (build_site) | 11 topic dirs drop `-study-notes` → `economics/`, `fsa/`,
  `quant-methods/` (quant-methods deliberately avoids the existing
  `quantitative-methods/`); `wp-content/uploads` → `wp-content/up` |
| 2 | `SEG_RENAMES` (computed at import) | every deeper segment: ≤2 words verbatim; ≥3 words → first word + last
  semantic word (`external-influences-on-industry-growth-profitability-and-risk`
  → `external-risk`); colliding groups keep full names; 286 segments |
| 3 | `apply_path_renames()` | prefix map then per-segment map; **must tolerate both leading-slash and
  bare forms** (asymmetry silently left refs dangling — see §5) |

Mapping artifacts: `docs/slug_rename_map.md` (regenerate by importing
build_site and dumping `SEG_RENAMES`).

---

## 4. Constants & invariants (check before editing)

| Where | Value | Why |
|---|---|---|
| `CHUNK_BYTES` | 4,000,000 | browser script-size limits on data chunks |
| `COMPRESS_THRESHOLD` | 50,000 bytes | images below stay lossless in the compressed variant |
| `COMPRESS_QUALITY` | 60 | visual trade for the <100 MB target |
| `PUFFY_GIF` | 1×1 transparent gif | pre-`applyImages` src |
| `skip_roots` | wp-content/wp-includes/wp-json/cdn.jsdelivr.net/fonts.* | never routed/embedded as pages |
| `href_targets` | set of all page slugs | hash-route a link only when the target is a known page |
| verify allowlist | youtube.com, youtube-nocookie.com, vimeo.com, player.vimeo.com, youtu.be, facebook.com, gravatar, googletagmanager, sharethis, cleantalk, fonts.*, cdn.jsdelivr.net | anything else = FAIL "unexpected external" |
| `TRACKER_HOSTS` | fd.cleantalk.org, ws.sharethis.com, googletagmanager, twitter, facebook | tags dropped by the fixer |

---

## 5. Gotcha history (READ BEFORE EDITING — real bugs found by verification)

1. **body-class routing** — homepage shell is a full-width template; routed
   pages MUST switch `<body>` classes (`.page-template-…-php .x-main` would
   pin width:auto). Reference: `.x-main` 942.844px float:left, sidebar
   213.234px float:right — pixel-equal to multi-file.
2. **31.2% banner fix** — a hardcoded aspect made every banner identical; the
   geometry must follow the image's own intrinsic ratio. The fix was deleted.
3. **leading-slash asymmetry** — `apply_path_renames` matched only one of
   `new_path` (has `/`) vs placement parents (no `/`) → dangling refs.
   Strip-and-reapply around the comparison.
4. **`page_slug('index.html')`** — `[:-11]` on a 10-char bare name yields
   `'index.htm'`; home anchors (`href="index.html"`) survived and 404'd.
   Handle the bare name explicitly.
5. **out-of-tree sidebar/menu refs** — sidebar links are relative to the
   *mirror* page depth (one level deeper than the parked pages); resolve
   failures retry SITE-rooted after stripping `../`.
6. **YouTube Error 153** — `/embed/` without Referer (every file:// page) is
   refused on some networks; watch pages play fine, http(s) inline plays
   fine. User decision: file:// click → watch tab; http(s) → inline embed.
7. **single-quoted attributes** — `href='//prepnuggets.com/…integrity-light.css'`
   was skipped by double-quote-only regexes → protocol-relative refs →
   `file://prepnuggets.com/…` → whole theme CSS missing → flat-menu pages.
   ALL attr regexes are now quote-agnostic; `fix_protocol_relative_refs.py`
   localizes everything (388 pages, 0 leftover).
8. **hotlink protection** — the uploads CDN 403s curl/bare request contexts
   without the site Referer; with
   `Referer: https://prepnuggets.com/cfa-level-1-study-notes/` the exact
   original bytes come back 200. fetch_missing carries it.
9. **grep-blind size variants** — `srcset` candidates other than `src`
   (1400x/1536x/768x/300x…) were never downloaded; browsers select by
   viewport → grey blocks on many pages (visible in the multi-file site only,
   because the single file embeds just `src`). Fetched all 578 missing
   variants; the full-render scan (387 content pages) now reports 0 grey /
   0 failed requests.
10. **corrupt image bodies** — 761 files were 281-byte HTTP error bodies
    stored as images (16% of all images); PIL-verify detects them; repair
    prefers same-stem valid variants and drops brand badges — **never
    substitutes unrelated artwork** (incident: an ESG image replaced a Bayes
    figure; the exact online file is always the reference).
11. **bare-name substitution recursion** — rewriting by filename re-matched
    inside previously rewritten relpaths and nested chains
    (`../../../wp-content/up/2022/08/../../../…`); replacement must use the
    exact original url string when present.
12. **urllib DNS hang** — `urlopen(timeout=…)` does NOT bound DNS resolution;
    a stalled DNS produced 4h/zero-output zombies. All network fetching goes
    through curl.exe (`--connect-timeout 6 --max-time 25`).

---

## 6. Verification matrix (run before claiming done)

| Check | Command | Pass condition |
|---|---|---|
| Static links | `python tools/verify_links.py` | `ALL CLEAN`, 389 pages, remote tags 0, placeholders 0 |
| Device matrix | `python tools/.build/verify_single_file_cross_device.py` | 5 contexts OK; every route: imgs loaded==total, `bad=0`, sidebar present, x-main correct |
| Content identity | `… --identity` | routed single-file article innerText == multi-file page (3 pages) |
| Full-render scan | see §7 note | 0 grey/broken images, 0 failed requests on content pages |
| No-JS images | `python tools/verify_no_js.py` | duplicates == 0 |
| Portability | copy site + single file to a +10-level deep probe; open over file:// | 13/13 imgs, 0 errors (proves relative-only refs) |
| Linux safety | case-collision + case-mismatch scan | 0 / 0 |
| Path limit | `max(len(p))` shipped files | absolute depth < 260 incl. deep copy target root |
| Zip round-trip | re-extract split volumes | sha256 equal to original |

Screenshots land in `tools/.build/shots/`. The full-render scan must filter
content pages with `rel = p.relative_to(SITE)` — absolute `parts[0]` (`D:`)
silently disables the filter and pulls in 700+ wp-json snapshot pages.

---

## 7. Common how-tos

- **Change article content** — edit the mirror (branch mirror-archive) →
  `build_site.py` → `fetch_missing.py` → `repair_broken_refs.py` →
  `verify_links.py` → `build_single_file.py` (both variants).
- **Change styling** — CSS lives in the mirror theme; same rebuild chain.
- **Change internal naming** — extend `PATH_RENAMES`/`SEG_RENAMES` rules,
  regenerate `docs/slug_rename_map.md`, rebuild; never hand-edit the single
  file's slugs without also updating the router tests.
- **Add a device context** — CONTEXTS in
  `tools/.build/verify_single_file_cross_device.py` (engine, viewport, UA,
  is_mobile); keep per-context checks identical.
- **Regenerate delivery zip** — zip the >100 MB html (deflate 6); if the zip
  exceeds 100 MB, slice into ≤100 MiB `.zip.001…parts` in the
  `cfa_l1_offline_notes_all_in_one_2026/` folder instead. The html, the zip
  and the potential volume folder are all gitignored by design.
- **Serve locally** — `python tools/serve.py` (`--port`, `--dir`); prints the
  LAN URL for phones; inline videos work there.

### 7.x Delivery notes

- **Recommend the single file first**: best compatibility and easiest to
  copy. The multi-file folder currently renders correctly on desktop only.
- README (bilingual, EN first, language switcher anchored at `#english` /
  `#中文`) documents how to unzip the split volumes (7-Zip/WinRAR open
  `.zip.001` directly; or `copy /b` / `cat` merge; sha256 verified).

---

# 中文版（Engineering Guide）

## 0. 项目是什么

**prepnuggets.com/cfa-level-1-study-notes/**（CFA Level 1 学习笔记，2026 考纲，387 篇正文页 + 主页，
约 4000 张图）的完全离线镜像。交付物：

| 交付物 | 形态 | 入口 / 体积 |
|---|---|---|
| `cfa_l1_offline_notes_site_2026/` | 多文件夹静态站 | `…/index.html`（309 MB）——**目前仅保证电脑端显示正常** |
| `cfa_l1_offline_notes_all_in_one_2026.html` | 单文件（hash 路由） | 该文件（143.8 MB）——**首选，兼容性最好** |
| `cfa_l1_offline_notes_all_in_one_2026_compressed.html` | 单文件，JPEG q60 | 该文件（93.3 MB，<100 MB） |
| `cfa_l1_offline_notes_all_in_one_2026.html.zip` | 整站单 zip（96.8 MB；压缩后 <100MB，无需分卷） | 项目根 |

### Git 分支约定

- `master`——交付态。**不含 `prepnuggets_raw_mirror`**（构建输入，4924 文件/309 MB）；需要镜像时
  `git checkout mirror-archive`。
- `mirror-archive`——完整保留镜像。

### 体积策略

- >100 MB 的原始单文件 **gitignored**，以分卷 zip 交付；压缩版（93.3 MB）保持 git 跟踪。
- 所有成品路径在任何深拷贝目标下低于 Windows 260 字符限制（实测：本检出深度 219；项目根相对 ~178；
  目标根预算 82 字符）。

## 1. 仓库结构

（同英文 §1；重点：`tools/` 下 13 个脚本职责对照表；`.build/` 为 gitignored 暂存；镜像只在 mirror-archive。）

## 2. 全管线细节

### 2.1 完整复现序列

```bash
cd cfa_curated_offline_notes
git checkout mirror-archive            # 取镜像（或只取目录）
python tools/build_site.py             # 1) 镜像→多文件站（确定性，清空重建）
python tools/fetch_new_pages.py        # 2) REST 对照补页+资产
python tools/fetch_missing.py          #    curl+Referer 补资源（有界超时）
python tools/fix_protocol_relative_refs.py  #    //host 引用本地化+追踪器删除
python tools/repair_broken_refs.py     #    审计→最近合法图循环，直到 broken refs: 0
python tools/verify_links.py           # 3) 门禁：必须 ALL CLEAN
python tools/build_single_file.py      # 4) 单文件（无损）/+ --compress（<100 MB）
python tools/.build/verify_single_file_cross_device.py          # 5) 套件
python tools/.build/verify_single_file_cross_device.py --identity # 仅内容对比
python tools/serve.py                  # 6) 可选本地服务
```

耗时参考：build_site ~3 分钟；网络修复 5–20 分钟；repair 3–6 分钟；verify ~1 分钟；
单文件×2 各 ~4 分钟；完整套件 ~20 分钟。

### 2.2 脚本契约表

| 脚本 | 输入 | 输出 | 要点 |
|---|---|---|---|
| build_site.py | 镜像 | site_2026 | 清理顺序：远程标签→视频框→懒加载展开→URL 映射（引号双兼容）→字体/css 本地化；产出 build_report.json；确定性 |
| fetch_new_pages.py | 线上 REST + site | 镜像增量+资产 | `MIRROR` 常量必须指向 `prepnuggets_raw_mirror`；含懒加载属性扫描 |
| fetch_missing.py | build_report.json | 站点文件 | curl.exe（`--connect-timeout 6 --max-time 25`）+ **Referer**（防盗链）；扩展名白名单跳过页面别名项；先抓尺寸档再试基名 |
| fix_protocol_relative_refs.py | 站点 html | 本地化引用 | 双/单引号；prepnuggets/jsdelivr/fonts → 存在则本地相对，否则 https:；追踪器标签整删 |
| repair_broken_refs.py | 站点 | 改写引用 | 审计（缺失+PIL 不可解码）→ 候选：同基名合法档 >> 同目录非品牌；品牌徽标整标签删除；精确整串替换防递归；≤5 轮；目标 0 |
| verify_links.py | 站点 | PASS/FAIL | 引号双兼容；存在性/大小写/外链白名单/协议相对/远程标签/懒加载占位全覆盖 |
| verify_single_file_cross_device.py | 单文件+站点 | 报告 | 5 上下文 + 7 路由；identity 模式逐字符对比文章文本 |
| serve.py | 站点 | 本地服务 | 打印手机局域网地址；http 下视频内嵌 |

### 2.3 build_report.json 结构

```json
{"cleaned_pages": [...], "externalized_urls": [[local, https-original], ...],
 "assets_missing_from_mirror": [[local, https-original], ...]}
```
- `externalized_urls`：页面型 URL（.php/.json/无扩展名）镜像缺失 → 保留外链（feed/glossary/privacy 等）。
- `assets_missing_from_mirror`：6000+ 条目（含大量 URL 别名记账）；**只有资源扩展名可抓**，其余跳过。

## 3. 架构

### 3.1 多文件站（build_site.py）

核心 `map_url_to_local(full, rename_css) -> (site_path, mirror_exists)`；所有
href/src/srcset/poster/CSS url 经其重写为**相对**路径。每页清理顺序见 §2。视频 iframe → `.pn-video-player`
（file:// → watch 页新标签；http(s) → 内嵌；**两处播放器 JS 必须逐字节一致**）。

### 3.2 单文件（build_single_file.py）

主页 body 外壳 + 其余页 chunked JSON（每块 4MB）+ base64 注册表：
- 页面 JSON：`{s, t, h, n, m, b, c}`（slug/title/article/sidebar/x-main 类/body 类/sidebar 类）
- 注册表：`IMG[key]`；img 改 1×1 GIF + `data-pn-img`；`applyImages` 运行时填充；只内嵌 src 档；`__PN_BAD` 记缺失
- 路由：`hashchange→render(slug)`；`#/` 经 `captureInit/INIT` 还原主页
- 侧栏为 `.x-main` 之后兄弟；无内联宽度（主题 CSS 定宽 213.234px）

### 3.3 路径压缩（三轮，均用户要求）

外壳名永不变；内部压缩规则见英文 §3.3 表。映射产物：`docs/slug_rename_map.md`。

## 4. 常量与不变量

同英文 §4（CHUNK_BYTES=4M；COMPRESS_THRESHOLD=50KB；QUALITY=60；PUFFY_GIF；skip_roots；
href_targets；verify 白名单；TRACKER_HOSTS）。

## 5. 踩坑史（改之前必读——全部由验证抓出的真实 bug）

（详见英文 §5 十二条：body 类路由 / 31.2% 补丁 / 前导斜杠不对称 / page_slug 裸名切片 /
侧栏越界 / YouTube Error 153 / **单引号属性跳过 → 主题 CSS 失效平铺菜单** /
**防盗链 Referer 403→200** / **srcset 候选档缺失→多文件版灰块** /
**761 个 281B 错误体假图**（PIL 验证；绝不跨题材替换——曾有 ESG 图顶替 Bayes 图的事故）/
裸名替换套娃 / urllib DNS 挂起僵尸进程。）

## 6. 验证矩阵

（同英文 §6；额外注意：全渲染扫描的过滤必须用 `rel = p.relative_to(SITE)`——用绝对 `parts[0]`
（'D:'）会静默失效，把 700+ wp-json 快照页卷进结果。）

## 7. 常见操作

（同英文 §7；分卷再生成：zip→切 ≤100MiB 片→放 `cfa_l1_offline_notes_all_in_one_2026/`；
>100MB html 与分卷目录均 gitignore。）

### 7.x 交付说明

单文件优先推荐（兼容性最好、复制最方便；多文件版目前电脑端正常）。
README 双语、语言切换锚点 `#english`/`#中文`；分卷解压见 FAQ Q8。

---

*Generated 2026-09-08. Mirror lives on mirror-archive; every incident in §5
  is preserved in git history.*
