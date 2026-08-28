# CFA Level 1 Study Notes —— 离线阅读站点

本文件夹是从 prepnuggets.com 镜像整理的**离线可读版**，双击 `index.html` 即可浏览，
无需任何网络连接。已通过浏览器实测：桌面 Chrome / 移动端（375×812 手机视口）加载
约 0.1-1 秒、图片全部显示、无控制台错误。

## 使用说明

- **电脑**：双击 `index.html`，用 Chrome / Edge / Safari 打开
- **安卓 / 平板**：把本文件夹整个拷到手机，用 Chrome / 文件管理器打开 `index.html`
- **iPhone / iPad**：拷到「文件」App，用 Safari 打开 `index.html`；
  也可以用「快捷指令 → 网页应用」把 index.html 发送到主屏幕后全屏阅读
- **单文件版**：`CFA_Notes/full_site_single_file.html`（与本文件夹同级的仓库根目录）——
  全部 305 页正文 + 全部原图内嵌到一个 HTML（约 95MB），打开后点任意站内链接即切换页面
  （hash 路由），可单独拷这一个文件到任何设备

## 布局

```
index.html            主页（最外层）—— 与原站 cfa-level-1-study-notes 首页一致
<10 个栏目>/          alternative-investments / corporate-issuers / derivatives /
                      economics / equity / ethics / financial-statement-analysis-fsa /
                      fixed-income / portfolio-management / quantitative-methods ·
                      quantitative-methods/  ← 主页链接的另一栏目
wp-content/ 等        字体、图片、CSS/JS 等静态资源
```

## 实测性能数据（Playwright Chromium，桌面 1280×900 / 移动 375×812）

| 项目 | 文件夹版 | 单文件版 |
|---|---|---|
| 首屏/加载 | 0.1 - 1.0 s | ~1.2 s |
| 页面切换 | < 0.2 s | ~1 - 1.5 s |
| 图片加载率 | 26/26 | 26/26（含随机 8 页抽查全通过） |
| 控制台错误 | 0 | 0 |
| 磁盘占用 | 309 MB | 94.8 MB（单文件） |

## 为什么以前很卡 / 有灰图（已修复）

原镜像直接离线打开时，每页残留大量远程引用（Google 统计、CleanTalk 反爬、
ShareThis、gravatar 头像、YouTube/Vimeo 嵌入、Google 字体），浏览器离线时逐个
等网络超时；图片是懒加载的灰色占位符 + 真实地址仍指向 `//prepnuggets.com`，
换页时懒加载脚本拉取失败 → 灰块。构建流程删除了全部远程引用、把懒加载展开为
真实本地路径、将字体/贴图资源本地化，并补抓了原镜像中缺失的 6 个字体文件、
把 2 个原站已删除的图片引用改写为已有的同图变体。

## 重新构建（可选）

在仓库根目录（CFA_Notes/）执行：

```
python tools/build_site.py          # 镜像 -> 本目录（清理+重排）
python tools/fetch_missing.py       # 补抓镜像缺失的网络资源（可选）
python tools/verify_links.py        # 链接机检（必须 0 问题）
python tools/verify_browser.py      # 浏览器实测（截图/计时/错误审计）
python tools/build_single_file.py   # 本目录 -> 仓库根 full_site_single_file.html
```

依次顺序执行。原始镜像在 `../offline_prepnuggets/`（不参与复制分发）。
