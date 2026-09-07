# CFA Level 1 Study Notes — PrepNuggets Offline Site (2026)

> [**English**](#english) &nbsp;|&nbsp; [**中文**](#chinese)

This project is a fully-offline mirror of **https://prepnuggets.com/cfa-level-1-study-notes/** — the CFA Level 1 study-notes site (2026 curriculum, 387 article pages + homepage, ~4000 images) — turned into deliverables you can browse with zero network requests: double-click and read, on any device.

本项目是 **https://prepnuggets.com/cfa-level-1-study-notes/**（CFA Level 1 学习笔记，2026 考纲，387 篇正文页 + 主页，约 4000 张图）的完整离线镜像，加工成两种可直接使用的成品：零网络请求、双击即读、跨设备可用。

---

## English

### 0. The two forms (read this first)

The offline site has **two forms** — identical content, identical styling, only the carrier differs:

| | Form ①: **Multi-folder site** | Form ②: **Single file** |
|---|---|---|
| What it is | A folder: `index.html` + topic subfolders + asset folders (images/fonts/CSS) — the whole static site | One `.html` file with the entire site (page content + images) embedded |
| Entry | `cfa_l1_offline_notes_site_2026/index.html` | `cfa_l1_offline_notes_all_in_one_2026.html` (**original, lossless**) or `cfa_l1_offline_notes_all_in_one_2026_compressed.html` (**<100 MB**) |
| Size | 309 MB (one folder) | **128.6 MB** (original) / **99.6 MB** (compressed) |
| Page navigation | Real file navigation (new URL per page) | Hash routing (`#/topic/article/` in the address bar) |
| First load | ~0.1–1 s | ~1.2 s (parses embedded data chunks once) |
| Page switch | < 0.2 s | ~1–1.5 s |
| Recommendation | **Daily reading**: computer, tablet, phone browsers | **One-file portability**: send once via WeChat/cloud drive and carry the whole site |

**Choosing**: use **Form ①** for regular study on phone/tablet/computer (identical to the live site); use **Form ②** only when you need exactly one file (cross-device transfer, cloud backup, apps that only accept single files).

### 1. Quick start

| Scenario | How |
|---|---|
| **Computer** | Double-click `cfa_l1_offline_notes_site_2026/index.html` (Chrome / Edge / Safari) |
| **Android phone / tablet** | Copy the whole `cfa_l1_offline_notes_site_2026/` folder to the device → open its `index.html` with Chrome |
| **iPhone / iPad** | Copy into the Files app → open `index.html` with Safari (or "Share → Add to Home Screen" for full-screen reading) |
| **Single file only** | Open/share `cfa_l1_offline_notes_all_in_one_2026.html` (whole site in one file; links switch pages in place) |

Measured: desktop & mobile first screens 0.1–1.2 s, 100% images loaded, 0 console errors.

### 2. Content

CFA 2026 Level 1, 10 topic sections + 1 extra section (article-level folders keep the original site paths; only the topic layer is compressed — see the mapping below):

| Local folder (topic layer compressed) | Original topic |
|---|---|
| `alternative-investments/` | Alternative Investments |
| `corporate-issuers/` | Corporate Issuers |
| `derivatives/` | Derivatives |
| `economics/` | Economics |
| `equity-investments/` | Equity Investments |
| `ethics/` | Ethics |
| `fsa/` | Financial Statement Analysis (FSA) |
| `fixed-income/` | Fixed Income |
| `portfolio-management/` | Portfolio Management |
| `quant-methods/` | Quantitative Methods |
| `quantitative-methods/` | the site's other quantitative-methods section |

Each topic holds article folders by knowledge point (e.g. `economics/understanding-cycles/`); the hierarchy mirrors `https://prepnuggets.com/cfa-level-1-study-notes/...` with compressed dir names (full old→new map: [docs/slug_rename_map.md](docs/slug_rename_map.md)).

**Scope boundary**: all notes/summaries/figure images are offline; KaTeX formulas, Font Awesome and Google fonts are localized. Features depending on the original server (on-site search, comments, sign-in, video streaming) are unavailable offline — videos show a static box (see Q2 below).

### 3. Comparing the two deliverables

| | **Multi-page site** (big folder) | **Single file** (1 html) |
|---|---|---|
| Location | `cfa_l1_offline_notes_site_2026/` | `cfa_l1_offline_notes_all_in_one_2026.html` |
| Size | 309 MB | 128.6 MB original / 99.6 MB compressed |
| Navigation | Real page jumps (relative paths) | Hash routing (`#/economics/` etc.) |
| First load | ~0.1–1.0 s | ~1.2 s (one-time data-chunk parse) |
| Page switch | < 0.2 s | ~1–1.5 s |
| Images | Full-resolution multi-size (responsive srcset) | Lossless embed (deduped registry, single largest variant) |
| Portability | Copy the whole folder (309 MB) | Copy 1 file (128.6 or 99.6 MB) |
| Best for | Regular use on computer/tablet/phone — recommended | One-file portability; compressed variant for cloud/backup (<100 MB) |

Both render identically (custom CSS, icon fonts, KaTeX verified): site brand 120px, uppercase nav, etc.

### 4. Repository layout & naming

```
cfa_l1_offline_notes/                        ← repo root
├── README.md                                ← this file
├── docs/
│   ├── engineering_guide.md                 ← bilingual engineering guide (reproduce/modify)
│   ├── slug_rename_map.md                   ← old→new compressed segment names
│   └── readme_images/                       ← verification screenshots
├── cfa_l1_offline_notes_site_2026/          ← deliverable ① (multi-file site)
├── cfa_l1_offline_notes_all_in_one_2026.html                ← deliverable ② (single file)
├── cfa_l1_offline_notes_all_in_one_2026_compressed.html
├── serve_local.cmd                          ← Windows double-click local viewer
├── tools/                                   ← all scripts (build/fetch/verify)
└── prepnuggets_raw_mirror/                  ← ONLY on branch mirror-archive
```

**Naming history** (outer names fixed; only inner dirs were compressed):

| Old | New | Meaning |
|---|---|---|
| Round 1 (2026-09): `CFA_Notes` / `offline_prepnuggets` / `study_notes_site` / `full_site_single_file.html` | `cfa_l1_offline_notes` / `prepnuggets_raw_mirror` / `cfa_l1_offline_notes_site_2026` / `cfa_l1_offline_notes_all_in_one_2026.html` | project root / raw mirror (build input, branch `mirror-archive`) / deliverable ① / deliverable ② |
| Round 2: `<topic>-study-notes/` (11 dirs) | `economics/`, `fsa/`, `quant-methods/` etc. | topic layer drops `-study-notes`; `quant-methods` avoids the existing `quantitative-methods/`; article-level slugs untouched |
| Round 2b: `wp-content/uploads/` | `wp-content/up/` | pure asset chain (no meaning to preserve); mirror keeps `uploads/` |
| Round 3 (recursive): deep folder segments | first-word + last-word (`external-influences-on-industry-growth-profitability-and-risk` → `external-risk`) | ≤2 words kept; ≥3 words keep head+tail semantic; colliding groups keep their full names; 286 segments — full map in `docs/slug_rename_map.md` |

Design goal: every shipped path stays under the Windows 260-char MAX_PATH even when copied into deeply nested directories (measured: 219 chars at this checkout; ~178 relative to the repo root → 82-char budget for the copy target).

### 5. Source & rebuild

All artifacts come from the raw mirror (branch **`mirror-archive`** — master does not carry it), a full snapshot of the live site taken 2026-08-02. To refresh:

```bash
cd cfa_l1_offline_notes
git checkout mirror-archive          # mirror lives on this branch only
python tools/fetch_new_pages.py      # REST diff: re-fetch new/changed pages
python tools/build_site.py           # mirror → multi-file site
python tools/verify_links.py         # must print ALL CLEAN
python tools/build_single_file.py    # single file (+ --compress for <100 MB)
```

Full pipeline, architecture, constants, gotcha history and verification matrix (bilingual): [docs/engineering_guide.md](docs/engineering_guide.md).

### 6. Measured data (2026-09-08, Playwright Chromium)

| Item | Multi-file site | Single file |
|---|---|---|
| Host | Windows 10, file:// protocol | same |
| Desktop 1280×900 first screen | 0.1–0.9 s (domContentLoaded 84–386 ms) | ~1.2 s |
| Mobile 375×812 viewport | same pages | 13/13 imgs |
| Images | 13/13 (homepage & spot checks; 26→13 after per-page dedupe) | 13/13 + random routes 100% |
| Console errors | 0 | 0 |
| Broken/remote/placeholder refs | 0 / 0 / 0 (389 pages machine-checked) | 0 |

Screenshots under `docs/readme_images/`.

### 7. FAQ

**Q1 Why was it slow/broken before?** The raw mirror referenced remote trackers (Google Analytics, CleanTalk, ShareThis, gravatar, YouTube/Vimeo, Google Fonts) and lazy-loaded images (grey SVG placeholders with live URLs). `build_site.py` cleans all of it: placeholders resolved to real local paths, fonts localized, `%`-escaped filenames migrated.

**Q2 How do videos work?** Live players come from YouTube/Vimeo streaming (not cached). Click behavior: **file:// (double-click / from phones)** → opens the watch page in a new tab — YouTube refuses `/embed/` without a Referer (Error 153), which file:// pages can never provide (verified 2026-09-07; watch pages play fine); **http(s) (local server** — `python tools/serve.py` or double-click `serve_local.cmd` — **or self-hosted)** → inline playback in the page, 100% verified. Bottom-left of the box: "Open on YouTube / Open on Vimeo" fallback link; zero network requests offline.

**Q3 Why is the single file 128.6 MB?** Lossless original-image embedding (user choice): image dedupe registry ~89 MB (1504 images) + 387 pages + 30.9 MB fonts/CSS. Smaller needs image recompression (the compressed variant exists: JPEG q70 → 99.6 MB, <100 MB).

**Q4 Broken downloads / missing images?** The mirror covers 99%+ of assets; a small set is permanently 403/404 on the original site too (anti-scraping), recorded in `verify_links.py`. If a new broken ref appears, re-run the rebuild sequence.

**Q5 Images used to appear twice.** Fixed (2026-09-06): the snapshots contain a duplicate template render; dedupe keeps the first copy per same `src`, matching the live site (26 → 13 images/page; JS-off duplicate count: 0).

**Q6 Does the Notes Navigation sidebar / video box / back button work in the single file?** Yes — sidebar injected with the current topic teal-highlighted, videos click-to-play (Q2), back button restores the homepage fully (previously it could stick). Home links (logo, "CFA LEVEL I NOTES INDEX") route back to `#/` (fixed 2026-09-08; previously ERR_FILE_NOT_FOUND).

**Q7 Why do some article banners look like wide black banners?** They are the site's own design images (e.g. the black/gold Financial Reporting banner); verified identical to the live-site render.

---

## 中文

### 〇、 本项目的两种形态（先读这里）

离线网页有**两种形态**，内容完全一致、样式一致，区别在于"装载体"：

| | 形态①：**多文件夹网站版** | 形态②：**单文件版** |
|---|---|---|
| 是什么 | 一个文件夹，内含 `index.html` + 各栏目子目录 + 资源目录（图片/字体/CSS），即整个"静态网站" | 一个 `.html` 文件，网站全部内容（页面正文+图片）都内嵌在里面 |
| 入口 | 打开 `cfa_l1_offline_notes_site_2026/index.html` | 打开 `cfa_l1_offline_notes_all_in_one_2026.html`（**原始未压缩版**）或 `cfa_l1_offline_notes_all_in_one_2026_compressed.html`（**压缩版，<100 MB**） |
| 体积 | 309 MB（1 个文件夹） | **128.6 MB**（原始未压缩）/ **99.6 MB**（压缩版 <100MB） |
| 页面间跳转 | 真实文件跳转（新页面新 URL） | hash 路由（同页切换，地址栏出现 `#/栏目/文章/`） |
| 首次加载 | ~0.1–1 秒 | ~1.2 秒 |
| 切页速度 | < 0.2 秒 | ~1–1.5 秒 |
| 推荐场景 | **日常阅读主力**：电脑、平板、手机浏览器均可 | **单文件走天下**：微信/网盘传一次就能全站带走 |

**选择建议**：手机/平板/电脑常规学习直接用**形态①**（跟原站体验一致）；只有需要"只拷一个文件"（如跨设备秒传、备份到网盘、贴到某些只能传文件的应用里）时才用**形态②**。

### 一、 秒上手

| 场景 | 操作 |
|---|---|
| **电脑** | 双击 `cfa_l1_offline_notes_site_2026/index.html`（Chrome / Edge / Safari） |
| **安卓手机 / 平板** | 整个 `cfa_l1_offline_notes_site_2026/` 文件夹拷进设备 → 用 Chrome 打开其 `index.html` |
| **iPhone / iPad** | 拷进「文件」App → Safari 打开 `index.html`（可「分享 → 添加到主屏幕」全屏阅读） |
| **只用单文件** | 打开/分享 `cfa_l1_offline_notes_all_in_one_2026.html`（全站合一，点击站内链接即切换页面） |

上手实测：桌面与手机视口首屏 **0.1–1.2 秒**，图片 100% 加载，0 控制台错误。

### 二、 内容

原站栏目（CFA 2026 Level 1，10 大主题 + 1 个附带栏目；文章级别目录沿用原站路径，栏目层已压缩）：

| 本地目录（栏目层已压缩） | 对应原站栏目 |
|---|---|
| `alternative-investments/` | Alternative Investments |
| `corporate-issuers/` | Corporate Issuers |
| `derivatives/` | Derivatives |
| `economics/` | Economics |
| `equity-investments/` | Equity Investments |
| `ethics/` | Ethics |
| `fsa/` | Financial Statement Analysis（FSA） |
| `fixed-income/` | Fixed Income |
| `portfolio-management/` | Portfolio Management |
| `quant-methods/` | Quantitative Methods |
| `quantitative-methods/` | 原站"量化方法"另一栏目页 |

每个栏目下按知识点分子目录（如 `economics/understanding-cycles/`），层级与原站
`https://prepnuggets.com/cfa-level-1-study-notes/...` 结构一致（目录名已压缩，完整映射见上方对照表 + [docs/slug_rename_map.md](docs/slug_rename_map.md)）。

**范围边界**：学习笔记正文/图表全部离线可用；公式（KaTeX）、图标字体（Font Awesome）、Google 字体均已本地化。依赖原站服务器的功能（站内搜索、评论、会员登录、视频播放）离线不可用——视频嵌入处显示静态占位框（见 Q2）。

### 三、 两种成品对比

| | **多页站点版**（大文件夹） | **单文件版**（1 个 html） |
|---|---|---|
| 位置 | `cfa_l1_offline_notes_site_2026/` | `cfa_l1_offline_notes_all_in_one_2026.html` |
| 体积 | 309 MB | 128.6 MB 原始 / 99.6 MB 压缩 |
| 翻页方式 | 真实多页面跳转（相对路径） | hash 路由（`#/economics/` 等） |
| 首次加载 | ~0.1–1.0 s | ~1.2 s（一次性解析数据块） |
| 页面切换 | < 0.2 s | ~1–1.5 s |
| 图片 | 全分辨率多尺寸（srcset 响应式） | 原图字节无损内嵌（注册表去重，单尺寸取最大档） |
| 迁移性 | 拷整个文件夹（309 MB） | 拷 1 个文件（128.6 或 99.6 MB） |
| 适用 | 电脑/平板/手机常规使用，推荐 | 微信传一次就能全站带走；传网盘/备份选压缩版（<100 MB） |

两版渲染样式一致（自定义 CSS、图标字体、KaTeX 均验证一致：站点品牌 120px、导航大写等）。

### 四、 目录结构与命名

```
cfa_l1_offline_notes/                        ← 项目根（本仓库）
├── README.md                                ← 本说明
├── docs/
│   ├── engineering_guide.md                 ← 中英双语工程指南（复现/改动参考）
│   ├── slug_rename_map.md                   ← 压缩段名新旧对照表
│   └── readme_images/                       ← 验证截图
├── cfa_l1_offline_notes_site_2026/          ← 成品①：多页站点版
├── cfa_l1_offline_notes_all_in_one_2026.html                ← 成品②：单文件版
├── cfa_l1_offline_notes_all_in_one_2026_compressed.html
├── serve_local.cmd                          ← Windows 双击启动本地查看器
├── tools/                                   ← 全部脚本（构建/补抓/校验）
└── prepnuggets_raw_mirror/                  ← 仅存于 mirror-archive 分支
```

**命名沿革**（外壳名固定，只压内部目录）：

| 旧名 | 新名 | 说明 |
|---|---|---|
| 第一轮（2026-09）：`CFA_Notes` / `offline_prepnuggets` / `study_notes_site` / `full_site_single_file.html` | `cfa_l1_offline_notes` / `prepnuggets_raw_mirror` / `cfa_l1_offline_notes_site_2026` / `cfa_l1_offline_notes_all_in_one_2026.html` | 项目根 / 原始镜像（构建输入，分支 `mirror-archive`）/ 成品① / 成品② |
| 第二轮：`<栏目>-study-notes/`（11 个） | `economics/`、`fsa/`、`quant-methods/` 等 | 栏目层去 `-study-notes`；`quant-methods` 避让既有 `quantitative-methods/`；文章级 slug 不动 |
| 第二轮：`wp-content/uploads/` | `wp-content/up/` | 纯资源链压缩；镜像内保持 `uploads/` |
| 第三轮（递归层全压）：深层目录段 | 首词-尾词（`external-influences-on-industry-growth-profitability-and-risk` → `external-risk`） | ≤2 词保持原名；≥3 词取首词+末语义词；冲突组全部保持原名；286 段，全表见 [docs/slug_rename_map.md](docs/slug_rename_map.md) |

设计目标：所有成品路径在任何深度的拷贝目标下都不超 Windows 260 字符限制（实测：本检出深度 219 字符；项目根相对 ~178 → 复制目标根预算 82 字符）。

### 五、 来源与重新构建

所有产物来自原始镜像（分支 **`mirror-archive`**——master 分支不携带镜像），2026-08-02 对原站的全量快照。刷新流程：

```bash
cd cfa_l1_offline_notes
git checkout mirror-archive          # 镜像只在这个分支
python tools/fetch_new_pages.py      # 对照 REST 清单重抓新增/变化页
python tools/build_site.py           # 镜像 → 多页站点版
python tools/verify_links.py         # 必须输出 ALL CLEAN
python tools/build_single_file.py    # 单文件版（+ --compress 出 <100MB 版）
```

完整管线、架构、关键常量、踩坑史与验证矩阵见 [docs/engineering_guide.md](docs/engineering_guide.md)（中英双语）。

### 六、 实测数据（2026-09-08，Playwright Chromium）

| 项目 | 多页站点版 | 单文件版 |
|---|---|---|
| 主机 | Windows 10，file:// 协议 | 同左 |
| 桌面 1280×900 首屏 | 浏览器加载 0.1–0.9 s（domContentLoaded 84–386 ms） | ~1.2 s |
| 手机 375×812 视口 | 同上（同套页面） | 13/13 图 |
| 图片加载 | 13/13（主页）/每页抽查全通过（去重后 26→13） | 13/13 + 随机路由 100% |
| 控制台错误 | 0 | 0 |
| 断链/远程引用/占位灰图 | 0 / 0 / 0（机检 389 页） | 0 |

截图见 `docs/readme_images/`。

### 七、 常见问题

**Q1 为什么原来很卡/有灰图？** 原始镜像残留大量远程引用（Google 统计、CleanTalk 反爬、ShareThis、gravatar 头像、YouTube/Vimeo 嵌入、Google 字体）与懒加载占位（灰 SVG、真实地址指向线上）。`build_site.py` 全部清理：懒加载展开为本地真实路径、字体/资源本地化、`%` 转义文件名迁移。

**Q2 视频怎么用？** 原站视频来自 YouTube/Vimeo 流媒体，不缓存。点击行为：**file:// 打开**（双击文件/拷手机直接打开）→ 新标签打开 YouTube/Vimeo **观看页**——YouTube 的 `/embed/` 嵌入页要求请求带 Referer，file:// 页面永远没有（2026-09-07 实测确定；观看页无此限制，打开即播）；**http(s) 打开**（本地服务器：双击 [tools/serve.py](tools/serve.py) 或 `python tools/serve.py`；或自托管）→ **当前页内嵌播放**（已验证 100% 可用）。播放框左下角常驻 "Open on YouTube / Open on Vimeo" 保底外链；离线时零网络请求。

**Q3 单文件版为什么 128.6 MB？** 原图无损内嵌（用户选定方案）：全部图片去重后约 89 MB 的 base64 注册表（1504 张）+ 387 页正文 + 30.9 MB 字体/CSS。想更小就做图片重压缩（压缩版 JPEG q70：99.6 MB，<100 MB）。

**Q4 下载失败/图片缺失？** 镜像覆盖 99%+ 资源；极少数旧图在原站同样无法显示（反爬常返 403/404），已收录于 `verify_links.py` 已知清单。若出现新的断链，重跑构建流程即可定位。

**Q5 图片曾经每张显示两遍，现在修好了吗？** 修好了（2026-09-06）。根因：快照里每张图带第二份副本（页面模板双份渲染）。构建时按"每页同 src 只保留第一份"去重（与在线原站实际渲染一致），每页图片数 26→13，JS 关闭状态重复计数为 0。

**Q6 单文件版的 Notes Navigation 侧栏、视频占位、返回按钮正常吗？** 正常。侧栏当前所在目录青色高亮（与原站一致）；视频点击后按 Q2 行为；返回按钮完整恢复首页；主页链接（logo、"CFA LEVEL I NOTES INDEX"）路由回 `#/`（2026-09-08 修复，原为 ERR_FILE_NOT_FOUND）。

**Q7 为什么有的文章标题图是黑色大横幅？** 那是原站自带设计图（如 Financial Reporting 黑底金色标题横幅），已验证在线原站同页渲染完全一致，非本项目缺陷。

---

*维护：2026-09-07 全量整理；git 多次提交（基线 → 设计 → 文件夹版 → 单文件版 → 重命名 → 压缩 → 视频 → 分支 → 界面修复 → 双语文档）。*
