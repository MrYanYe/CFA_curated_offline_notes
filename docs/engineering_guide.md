# CFA Level 1 Offline Notes — Engineering Guide

> How to reproduce, run, verify, and modify this project. Written for
> engineers and coding agents. English first; 中文版本在英文部分之后.

---

## 0. What this project is

A fully-offline mirror of **https://prepnuggets.com/cfa-level-1-study-notes/**
(CFA Level 1 study notes, 2026 curriculum, 387 article pages + homepage,
~4000 images), packaged as two interchangeable deliverables:

| Deliverable | What it is | Entry point |
|---|---|---|
| `cfa_l1_offline_notes_site_2026/` | Multi-file static site (real file navigation) | `cfa_l1_offline_notes_site_2026/index.html` |
| `cfa_l1_offline_notes_all_in_one_2026.html` | Single-file site (hash routing, everything embedded) | the file itself |
| `cfa_l1_offline_notes_all_in_one_2026_compressed.html` | Same as above, images re-compressed JPEG q70 (<100 MB) | the file itself |

Sizes (2026-09-08): site 329.5 MB; single file 128.6 MB; compressed 99.6 MB.
Both forms render identically (same CSS bundle, fonts, KaTeX), verified by
character-level content comparison and device-context tests (see §6).

### Git branches

- `master` — the deliverable state. **Does NOT contain
  `prepnuggets_raw_mirror`** (build input, 4924 files, 309 MB). Rebuilds that
  need the mirror: `git checkout mirror-archive`.
- `mirror-archive` — keeps `prepnuggets_raw_mirror` intact (created at
  commit `9aa1c00`).

---

## 1. Layout

```
cfa_l1_offline_notes/                    ← repo root
├── README.md                            ← user-facing docs (Chinese)
├── docs/
│   ├── engineering_guide.md             ← this file
│   ├── slug_rename_map.md               ← old→new segment names (generated)
│   └── readme_images/                   ← verification screenshots
├── cfa_l1_offline_notes_site_2026/      ← deliverable ① (built by build_site.py)
│   ├── index.html                       ← homepage
│   └── <topic>/…                        ← compressed topic dirs (PATH_RENAMES)
├── cfa_l1_offline_notes_all_in_one_2026.html           ← deliverable ②
├── cfa_l1_offline_notes_all_in_one_2026_compressed.html
├── serve_local.cmd                      ← Windows double-click local viewer
├── tools/
│   ├── build_site.py                    ← mirror → multi-file site
│   ├── build_single_file.py             ← multi-file site → single file(s)
│   ├── fetch_missing.py                 ← re-download assets missing from mirror
│   ├── fetch_new_pages.py               ← re-fetch new/changed pages (REST diff)
│   ├── verify_links.py                  ← static check: 0 broken/remote/lazy refs
│   ├── verify_browser.py                ← Playwright smoke test + screenshots
│   ├── verify_no_js.py                  ← image count check with JS disabled
│   ├── dedupe_image_duplicates.py       ← one-copy-per-src dedupe helper
│   ├── fill_image_gaps.py / _loop.py    ← fill missing image refs from mirror
│   ├── serve.py                         ← local http server (inline video view)
│   └── .build/                          ← gitignored scratch: reports, shots,
│       └── verify_single_file_cross_device.py   ← 5-context + identity suite
└── prepnuggets_raw_mirror/              ← ONLY on branch mirror-archive
```

---

## 2. Pipeline (reproduce everything)

```
raw mirror  →  build_site.py  →  multi-file site  →  verify_links.py
                ↓ (site exists)
          build_single_file.py  →  single file  →  verify_… + browser suite
```

```bash
cd cfa_l1_offline_notes

# 1) rebuild the multi-file site (needs the mirror — run on mirror-archive)
git checkout mirror-archive
python tools/build_site.py                 # wipes site dir, rebuilds it

# 2) optional: repair gaps / fetch new pages (network)
python tools/fetch_missing.py              # missing assets listed in the report
python tools/fetch_new_pages.py            # REST diff against the live site

# 3) static gate — MUST print "ALL CLEAN"
python tools/verify_links.py

# 4) single-file builds
python tools/build_single_file.py          # lossless (original bytes)
python tools/build_single_file.py --compress   # JPEG q70, target <100 MB

# 5) browser verification (desktop + mobile + webkit + identity)
python tools/.build/verify_single_file_cross_device.py
python tools/.build/verify_single_file_cross_device.py --identity   # text-only

# 6) optional: inline-video viewing
python tools/serve.py                      # or double-click serve_local.cmd
```

`build_site.py` is deterministic (same report numbers on re-runs). Total
run time on a dev machine: ~3 min for build_site, ~1 min for verify_links,
~4 min for single-file builds (×2), ~10 min for the full device suite.

### Which tool writes what

| Tool | Input | Output |
|---|---|---|
| build_site.py | mirror (branch mirror-archive) | site_2026 (389 pages incl. homepage) |
| build_single_file.py | site_2026 | both single-file htmls |
| verify_links.py | site_2026 | PASS/FAIL report |
| verify_single_file_cross_device.py | single file + site_2026 | device matrix report |

---

## 3. Architecture

### 3.1 Multi-file site (build_site.py)

`Map URL → local file` is the core: `map_url_to_local()` canonicalizes an
original absolute URL into `(site_path, mirror_file_exists)`; every href/src/
srcset/poster/CSS-url goes through it and is re-emitted as a **relative**
path (never absolute). Per page, in order:

1. Strip remote `<script>/<link>` tags + CleanTalk anti-bot scripts.
2. Replace YouTube/Vimeo `<iframe>` with `.pn-video-player` boxes
   (`replace_video_iframes`, see §4.3).
3. Expand WP-Rocket lazyload (svg placeholder → real local src).
4. Rewrite every URL attr via `map_url_to_local`.
5. Localize Google Fonts css; `%`-escaped filenames get safe names.

Sanity rule: an asset whose raw-mirror counterpart is missing is either
kept as external (page-like URLs) or reported in
`tools/.build/build_report.json` under `assets_missing_from_mirror` — the
output still points at its (existing or backfilled) local path.

### 3.2 Single file (build_single_file.py)

The single file = homepage `<body>` (shell) + all other pages as chunked
JSON + a registry of every asset as base64 data-URI.

- **Shell**: cleaned homepage body (header/nav chrome). Same CSS bundle as
  the multi-file site (deduped per-file `<style>` blocks, minified).
- **Per-page JSON** (`chunks`, 4 MB each): `{s: slug, t: title, h: article,
  n: sidebar html, m: x-main classes, b: body classes, c: sidebar classes}`.
- **Registry**: `IMG[key]` — every image keyed by site-relative path, value
  is a base64 data URI. `<img>` tags are rewritten to a 1×1 GIF +
  `data-pn-img="key"`, then `applyImages()` fills in the real bytes at
  runtime. De-duplicated: one key per path, `<img>` srcset stripped, single
  (largest) variant embedded.
- **Router**: `hashchange` → `render(slug)`:
  swap `<article>` for `page.h`, set `.x-main` class from `page.m`,
  set `<body>` class from `page.b`, inject sidebar into `#pn-sidebar`
  (`page.n` + `page.c`), set `document.title`, `window.scrollTo(0,0)`;
  `#/` (or empty hash) restores the captured homepage
  (`captureInit()` / `INIT`) exactly.
- **Sidebar placement**: `#pn-sidebar` is inserted as a **sibling AFTER**
  `.x-main` — same DOM order as the original pages. No inline width: the
  theme CSS sizes it (customizer `.x-sidebar{width:calc(100% - 2.463% - 80%)}`).

### 3.3 Path compression (three rounds, all user decisions)

Outer names (root / site dir / single-file name) are **fixed**; only the
site's inner dirs are compressed (Windows MAX_PATH 260 chars):

1. `PATH_RENAMES` in build_site.py: 11 topic dirs drop `-study-notes`
   (`economics/`, `fsa/`, `quant-methods/` — quant-methods avoids the
   existing `quantitative-methods/`), `wp-content/uploads` → `wp-content/up`.
2. `SEG_RENAMES` (segment map, computed at import): every **deeper**
   segment: ≤2 words kept verbatim; ≥3 words keep first + last semantic
   word (`external-influences-on-industry-growth-profitability-and-risk` →
   `external-risk`; stopwords excluded from the tail position). Collisions:
   the whole conflicting group keeps its original names (never ambiguous,
   never sequence-suffixed). 286 segments renamed; full map in
   `docs/slug_rename_map.md` (regenerate: import build_site, dump
   `SEG_RENAMES`).
3. `apply_path_renames()` applies prefix map then per-segment map; tolerate
   both leading-slash and bare forms (see the gotcha history in §5).

Measured: longest shipped path 219 chars at this checkout depth (project
root relative ~178 → 82-char budget for the copy target root).

### 3.4 Renders equal — how it's guaranteed

Same CSS bundle, same article HTML, same sidebar, same body classes per
route (the homepage shell is a *full-width template*: its `page-template-
template-layout-full-width-php` body class pins `.x-main` to `width:auto` —
each routed page MUST carry its own body classes or the layout collapses).

---

## 4. Constants & invariants that matter

| Where | Value | Why it matters |
|---|---|---|
| build_single_file.py `CHUNK_BYTES` | 4,000,000 | JSON chunk size (script size limits in browsers) |
| `COMPRESS_THRESHOLD` | 100,000 bytes | images below stay lossless |
| `COMPRESS_QUALITY` | 70 | compressed variant size target (<100 MB) |
| `PUFFY_GIF` | 1×1 transparent GIF placeholder | pre-`applyImages` img src |
| `skip_roots` | wp-content/wp-includes/wp-json/cdn.jsdelivr.net/fonts.googleapis.com/fonts.gstatic.com | never routed/embedded as pages |
| `href_targets` | set of all page slugs | a link is hash-routed only if its target is a known page; otherwise kept (`#/…` vs raw) |
| verify_links.py allowlist | youtube.com, youtube-nocookie.com, vimeo.com, player.vimeo.com, youtu.be, facebook.com, gravatar, googletagmanager, sharethis, cleantalk, fonts.*, cdn.jsdelivr.net | anything else = "unexpected external" FAIL |

---

## 5. Gotcha history (read before editing)

These are real bugs found by verification. Any new change must not resurface them:

1. **Body-class routing**: routed pages must switch `<body>` classes
   (full-width-template home shell). Fix, then verified `.x-main` 942.844px
   float:left, sidebar 213.234px float:right — pixel-equal to multi-file.
2. **Featured-banner fix**: a hardcoded `31.2%` aspect-ratio fix made every
   banner the same geometry — deleted; banners now follow the image's own
   intrinsic ratio (like the multi-file pages).
3. **Leading-slash asymmetry**: `apply_path_renames` initially matched only
   one of `new_path` (has `/`) vs page-placement parents (no `/`) —
   page refs silently became dangling. Put the strip-and-reapply around the
   comparison.
4. **`page_slug('index.html')`**: `[:-11]` on a 10-char bare name yields
   `'index.htm'` — home shell anchors (`href="index.html"`) survived and
   404'd. Handle the bare name explicitly.
5. **Out-of-tree sidebar/menu refs**: sidebar links are relative to the
   *mirror* page depth, one level deeper than the parked site page; resolve
   failures must retry SITE-rooted after stripping `../`.
6. **YouTube Error 153**: `/embed/` without a Referer (every file:// page)
   is refused by YouTube on some networks — watch pages play fine, http(s)
   embeds play fine. Behavior chosen by the user: file:// click opens the
   watch tab; http(s) embeds inline. `build_site.video_player_script()` and
   `build_single_file.VIDEO_PLAYER_JS` must stay **identical**.

---

## 6. Verification matrix (use before claiming "done")

| Check | Command | Pass condition |
|---|---|---|
| Static links | `python tools/verify_links.py` | `ALL CLEAN`, 389 pages, remote tags 0, placeholders 0 |
| Device matrix | `python tools/.build/verify_single_file_cross_device.py` | 5 contexts OK (desktop/Android phone/tablet/WebKit/iOS) + 0 console errors, 13/13 imgs, `bad=0` |
| Content identity | … `--identity` | routed single-file article innerText == multi-file page (3 pages) |
| No-JS image count | `python tools/verify_no_js.py` | duplicates == 0 |
| Portability | copy `site_2026/` + single file to a deep probe dir (e.g. +10 levels), open over file:// | 13/13 imgs, 0 errors — also proves relative-only refs |
| Linux safety | scan for case-insensitive name collisions and case-mismatched hrefs | 0 collisions, 0 mismatches |
| Path limit | `max(len(p))` over shipped files | absolute depth < 260 incl. deep copy target root |

Screenshots land in `tools/.build/shots/`.

---

## 7. Common how-tos

- **Change article content**: edit the mirror (mirror-archive) → build_site →
  verify_links → build_single_file (both variants) → device suite.
- **Change styling**: CSS lives in the mirrored theme; rebuild the site (or
  patch `bundle_css`) the same way.
- **Change site-internal naming**: extend `PATH_RENAMES`/`SEG_RENAMES` rules,
  regenerate `docs/slug_rename_map.md`, rebuild; **never** rename article-level
  slugs in the single-file JSON without also touching the router tests.
- **Add a device context**: edit `tools/.build/verify_single_file_cross_device.py`
  CONTEXTS (engine, viewport, UA, is_mobile) — keep checks per context.
- **Serve locally**: `python tools/serve.py` (optionally `--port`, `--dir`);
  prints phone URL; serves deliverable ①.


### 7.x Distribution & delivery notes

- **Deliverable to prefer for users: the single file.** Its compatibility is
  the best of all forms and it is the easiest to copy (one file, phone/tablet/
  desktop). The multi-file folder version currently renders correctly on
  desktop only (verified), so README recommends Form ② first.
- The >100MB original single file is gitignored (tracked removal) and shipped
  as split-volume zip (`cfa_l1_offline_notes_all_in_one_2026/` folder,
  `.zip.001` + optional .002...). Un-/re-created by
  `tools/.build/make_split_zip.py` style logic; volumes are plain zip byte
  slices: 7-Zip/WinRAR open .001 directly, or `copy /b`/`cat` merge then
  unzip. sha256 round-trip verified.
- Single-file sizes: original 143.78 MB; split zip single volume 96.8 MB.
---

**分发与交付说明**：单文件版优先推荐（兼容性最好、复制最方便；多文件版目前仅电脑端正常显示）。
原始单文件（>100MB）已从 git 剔除，以分卷 zip 交付（`cfa_l1_offline_notes_all_in_one_2026/` 下
`.zip.001`；解压：7-Zip/WinRAR 直开，或 `copy /b`/`cat` 合并后解压，sha256 已验证）。

# 中文版（Engineering Guide）

## 0. 项目是什么

**prepnuggets.com/cfa-level-1-study-notes/**（CFA Level 1 学习笔记，2026 考纲，
387 篇正文页 + 主页，约 4000 张图）的完全离线镜像，产出两种可互换形态：

| 形态 | 说明 | 入口 |
|---|---|---|
| `cfa_l1_offline_notes_site_2026/` | 多文件静态站（真实文件跳转） | `…/cfa_l1_offline_notes_site_2026/index.html` |
| `cfa_l1_offline_notes_all_in_one_2026.html` | 单文件站（hash 路由、全部内嵌） | 该文件本身 |
| `cfa_l1_offline_notes_all_in_one_2026_compressed.html` | 同上，图片重压缩 JPEG q70（<100 MB） | 该文件本身 |

体积（2026-09-08）：站点 329.5 MB；单文件 128.6 MB；压缩版 99.6 MB。
两形态渲染一致（同一 CSS/字体/KaTeX），经字符级内容对比与设备矩阵验证（见 §6）。

### Git 分支约定

- `master`——交付态。**不含 `prepnuggets_raw_mirror`**（构建输入，4924 文件/309 MB）；
  需要镜像重建时先 `git checkout mirror-archive`。
- `mirror-archive`——完整保留镜像（自 commit `9aa1c00` 创建）。

## 1. 目录结构

（同上英文 §1；要点：`tools/` 下十个 + 脚本、`.build/`（gitignored 暂存：构建报告、
截图、跨设备套件脚本）、`docs/slug_rename_map.md` 为压缩映射全表）。

## 2. 复现全流程

```bash
cd cfa_l1_offline_notes
git checkout mirror-archive          # 需要镜像
python tools/build_site.py           # 1) 镜像 → 多文件站（清空重建，确定性）
python tools/fetch_missing.py        # 2) 可选：补抓缺失资源（网络）
python tools/fetch_new_pages.py      #    可选：对照在线 REST 补新增/变化页
python tools/verify_links.py         # 3) 机检：必须输出 ALL CLEAN
python tools/build_single_file.py    # 4) 单文件（无损）
python tools/build_single_file.py --compress   #   压缩版（JPEG q70，<100MB）
python tools/.build/verify_single_file_cross_device.py          # 5) 设备矩阵
python tools/.build/verify_single_file_cross_device.py --identity  # 仅内容对比
```

耗时参考：build_site ~3 分钟；verify_links ~1 分钟；单文件两种各 ~4 分钟；设备套件 ~10 分钟。

### 脚本职责表

| 脚本 | 输入 | 输出 |
|---|---|---|
| build_site.py | 镜像（mirror-archive 分支） | site_2026（389 页含主页） |
| build_single_file.py | site_2026 | 两个单文件 html |
| verify_links.py | site_2026 | PASS/FAIL 报告 |
| verify_single_file_cross_device.py | 单文件 + site_2026 | 设备矩阵报告 |

## 3. 架构

### 3.1 多文件站（build_site.py）

核心 = `map_url_to_local()`：把原站绝对 URL 规范成 `(站点路径, 镜像文件是否存在)`；
所有 href/src/srcset/poster/CSS url 都经过它并**以相对路径重写**（绝不绝对化）。每页加工顺序：
去除远程 script/link 与 CleanTalk 反爬脚本 → 视频 iframe 换 `.pn-video-player`（§4.3）→
WP-Rocket 懒加载展开（灰 SVG 占位换真实本地路径）→ 全部 URL 属性经 map 重写 →
Google 字体 css 本地化、`%` 转义文件名安全化。

判定规则：镜像缺失的资源——页面型 URL 保留为外部链接；其余记入
`tools/.build/build_report.json` 的 `assets_missing_from_mirror`（输出仍指向已存在/待补的本地路径）。

### 3.2 单文件（build_single_file.py）

单文件 = 主页 `<body>`（外壳）+ 其余页面做 chunked JSON + 全资源 base64 注册表：
- **外壳**：清洗后的主页 body（页头/导航 chrome），与多文件站同一 CSS 包（按文件去重的 `<style>`、minify）。
- **页面 JSON**（每块 4MB）：`{s: slug, t: title, h: article, n: sidebar html, m: x-main 类, b: body 类, c: sidebar 类}`。
- **注册表**：`IMG[key]`（key=站点相对路径 → base64）。`<img>` 先改 1×1 GIF + `data-pn-img="key"`，
  `applyImages()` 运行时填真实字节；同一路径只存一份，剥 srcset、取最大档。
- **路由器**：`hashchange → render(slug)`——换 `<article>`、设 `.x-main` 类（`m`）、设 `<body>` 类（`b`）、
  向 `#pn-sidebar` 注入侧栏（`n`+`c`）、设标题、回顶；`#/` 时用 `captureInit()`/`INIT` 完整还原主页。
- **侧栏位置**：`#pn-sidebar` 是 `.x-main` 的**兄弟节点且在其后**（与原版 DOM 顺序一致）；不带内联宽度，
  由主题 CSS 计算（customizer `.x-sidebar{width:calc(100% - 2.463% - 80%)}`）。

### 3.3 路径压缩（三轮，均用户拍板）

外层名（根/站点目录/单文件名）**固定不动**，只压站点内部（Windows MAX_PATH 260 风险）：
1. `PATH_RENAMES`：11 个栏目目录去 `-study-notes`（`economics/`、`fsa/`、`quant-methods/`——后者避让已有
   `quantitative-methods/`），`wp-content/uploads` → `wp-content/up`。
2. `SEG_RENAMES`（模块导入时动态计算）：**更深的任何段**——词数 ≤2 保持原名；≥3 词取首词+末语义词
   （`external-influences-on-industry-growth-profitability-and-risk` → `external-risk`，尾部为停用词时取倒数第二词）；
   **压缩结果冲突的组整体保持原名**（绝不歧义、绝不带序号后缀）。共 286 段；全表 `docs/slug_rename_map.md`
   （重新生成：import build_site 后导出 `SEG_RENAMES`）。
3. `apply_path_renames()`：先前缀映射再逐段映射；必须同时容忍带前导斜杠与不带两种形态（见 §5 踩坑 3）。

实测：本检出深度最长路径 219 字符（项目根相对 ~178 → 复制目标根 82 字符预算）。

### 3.4 两形态渲染一致的保证

同一 CSS 包、同一文章 HTML、同一侧栏、路由时各自 body 类（主页外壳是 full-width 模板——它的
`page-template-template-layout-full-width-php` body 类会把 `.x-main` 钉死为 `width:auto`；
**每个路由页必须带自己的 body 类，否则布局塌成全宽**）。

## 4. 关键常量与不变量

| 位置 | 值 | 意义 |
|---|---|---|
| build_single_file.py `CHUNK_BYTES` | 4,000,000 | JSON 分块（浏览器脚本体积限制） |
| `COMPRESS_THRESHOLD` | 100,000 字节 | 小于此值的图片保持无损 |
| `COMPRESS_QUALITY` | 70 | 压缩版体积目标（<100 MB） |
| `PUFFY_GIF` | 1×1 透明 GIF | `applyImages` 前的 img 占位 |
| `skip_roots` | wp-content/wp-includes/wp-json/cdn.jsdelivr.net/fonts.googleapis.com/fonts.gstatic.com | 不做页面收录/路由 |
| `href_targets` | 全部页面 slug 集合 | 链接只有目标页已知才转 hash 路由 |
| verify_links 白名单 | youtube.com、youtube-nocookie.com、vimeo.com、player.vimeo.com、youtu.be、facebook.com、gravatar、googletagmanager、sharethis、cleantalk、fonts.*、cdn.jsdelivr.net | 其它 = "unexpected external" 失败 |

## 5. 踩坑史（改之前必读）

下述都是验证抓出的真实 bug，任何新改动不得复活：

1. **body 类路由**：路由页必须切换 `<body>` 类（外壳是 full-width 模板）。修复后基准：`.x-main`
   942.844px/float:left、侧栏 213.234px/float:right——与多文件版逐像素一致。
2. **横幅修复补丁**：曾硬编码 31.2% 纵横比导致全站横幅同一几何——已删；横幅按图片自身比例。
3. **前导斜杠不对称**：`apply_path_renames` 初版只匹配 `new_path`（带 `/`）与页面放置 parent（不带）中的一种——
   页内引用静默悬空。修复：比较前统一 lstrip，返回时按原样加回。
4. **`page_slug('index.html')`**：`[:-11]` 切 10 字符裸名得到 `'index.htm'`——外壳主页锚点
   （`href="index.html"`）原样保留导致 404。显式处理裸名。
5. **越界的侧栏/菜单引用**：侧栏链接相对深度按**镜像页**计算（比落盘页深一级）；解析失败必须
   "剥 `../` 后以 SITE 为根重试"（CSS 重写早有的兜底，正文此前没有）。
6. **YouTube Error 153**：`/embed/` 无 Referer（file:// 必无）在部分网络被拒——watch 页可播、http(s) 可内嵌。
   用户已拍板：file:// 点击→开 watch 标签页；http(s)→页内内嵌。**build_site.video_player_script() 与
   build_single_file.VIDEO_PLAYER_JS 必须保持逐字符一致**。

## 6. 验证矩阵（声称"完成"前必须）

| 检查 | 命令 | 通过标准 |
|---|---|---|
| 静态链接 | `python tools/verify_links.py` | `ALL CLEAN`、389 页、远程标签 0、占位 0 |
| 设备矩阵 | `python tools/.build/verify_single_file_cross_device.py` | 5 上下文 OK（桌面/安卓手机/平板/WebKit/iOS）+ 0 控制台错误、13/13 图、`bad=0` |
| 内容一致 | 同上 `--identity` | 路由页正文 innerText 与多文件版逐字符相等（3 页） |
| 无 JS 图数 | `python tools/verify_no_js.py` | 重复计数 == 0 |
| 可移植性 | 拷 `site_2026/`+单文件到深层探针目录（如 +10 层）file:// 打开 | 13/13 图、0 错误——同时证明全相对引用 |
| Linux 安全 | 扫大小写碰撞与大小写错配 href | 0 / 0 |
| 路径极限 | `max(len(p))`（全量文件） | 绝对深度 < 260（含深拷贝目标根） |

截图输出在 `tools/.build/shots/`。

## 7. 常见操作

- **改内容**：改镜像（mirror-archive）→ build_site → verify_links → build_single_file（两种）→ 设备套件。
- **改样式**：CSS 在镜像主题里；同样整链重建（或改 `bundle_css`）。
- **改内部命名**：扩 `PATH_RENAMES`/`SEG_RENAMES` 规则 → 重新生成 `docs/slug_rename_map.md` → 重建；
  **禁止**直接改单文件 JSON 里的文章 slug 而不同步路由测试。
- **加设备上下文**：编辑 `tools/.build/verify_single_file_cross_device.py` 的 CONTEXTS（引擎/视口/UA/is_mobile），
  每个上下文的检查项保持一致。
- **本地服务**：`python tools/serve.py`（可 `--port`/`--dir`），会打印手机局域网地址；serve 的是形态①。

---

*Generated 2026-09-08. Deliberate sizes/changes are committed in master; mirror lives on mirror-archive.*
