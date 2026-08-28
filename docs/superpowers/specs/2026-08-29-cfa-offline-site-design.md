# CFA 离线学习站点整理设计文档（2026-08-29）

## 目标

把原始镜像 `offline_prepnuggets/`（309MB，WP 站点镜像）加工成：

1. **文件夹版** `study_notes_site/`：主页放在最外层，子目录层级与原站一致，可整个拷进手机
2. **单文件版** `CFA_Notes/full_site_single_file.html`：全站合一、原图无损、hash 路由
3. 两者均：无远程依赖（离线流畅）、无灰色图片、跨设备兼容（Android/iOS/Mac 浏览器）
4. git 版本管理全程留痕

## 诊断结论（依据原始镜像）

| 症状 | 根因 |
|---|---|
| 页面卡顿 | 每页残留远程 `<script>`/`<iframe>`：googletagmanager(612)、youtube(680)、vimeo(613)、cleantalk/fd.cleantalk.org(306)、sharethis(306)、gravatar/facebook(612)、fonts.gstatic(306)。离线时浏览器逐个等网络超时；另有 CleanTalk `ctPublic` 巨型内联脚本 |
| 灰色图片 | WP Rocket 懒加载：`src`=灰色 SVG 占位，真图在 `data-lazy-src="//prepnuggets.com/…"`（协议相对、未经改写），懒加载脚本离线拉取失败 → 灰块 |
| 结构混乱 | 主页埋在 `offline_prepnuggets/prepnuggets.com/cfa-level-1-study-notes/index.html` 三层深处 |

图片本体（3776 张，239MB）已全部下载，灰图问题不是缺图而是引用错。

## 采用方案

### 文件夹版 study_notes_site/

```
study_notes_site/
  index.html                          ← 原 cfa-level-1-study-notes 主页（最外层）
  README.md
  wp-content/ wp-includes/ wp-json/   ← 公用资源树（原样搬移，保持内部相对结构）
  cdn.jsdelivr.net/ fonts.googleapis.com/ fonts.gstatic.com/
  quantitative-methods/
  <10 个栏目>study-notes/…            ← 各栏目 index.html + 知识点子目录
```

- 资源树**原样字节拷贝**（CSS/JS 内部相对引用不断）；页面层级整体上移两级
- 全部页面的 href/src/srcset/data-src/data-lazy-src 重算为从新位置出发的相对路径
- CSS 内 `url(//fonts.gstatic.com…)` 重写为本地相对路径（按 css 所在深度计算）

### 清洗规则（每页通用）

1. 删除指向外域的 `<script src>`（gtag/sharethis/cleantalk/gravatar/facebook/fd.cleantalk.org）
2. 删除 CleanTalk 内联巨型 `<script>`（`ctPublic*`、bot-detector-wrapper 引用等）
3. YouTube/Vimeo `<iframe>` → 同尺寸静态占位块（标题 + "Video (offline)"），不修视频
4. 懒加载展开：占位 `src` 回填为 `data-lazy-src` 真图地址后删除懒加载属性；协议相对 `//prepnuggets.com/…` → 本地相对
5. 根绝对路径（`/udemy` 等）：本地有 → 相对；本地无 → 保留原站 https 外链
6. 评论/搜索/登录等 REST 脚本段：离线无功能，删除（浏览与导航功能不受影响）

### 兜底重抓（新允许项）

构建后做"引用 → 落盘"全量对照审计；凡 HTML/CSS 引用但本地缺失的资源，用
`tools/fetch_missing.py` 按原 URL 从 prepnuggets.com 补抓。默认以现有镜像为准。

### 验证（问题 4）

- 链接机检：全站页面所有内部 href/src 目标文件必须存在（0 缺失）
- Playwright Chromium（已装 v1234）：
  - 打开 `file://…/study_notes_site/index.html`，收集 console 错误、统计图片
    `naturalWidth>0` 比例（目标 100%）、无头计时二屏时间（目标 <3s）
  - 手机 viewport 375×812 截图 + 菜单展开 + 抽样 3 页翻页
- 单文件版同套验证，重点记录解析耗时与内存

### 单文件版（无损 + 流畅硬性要求）

- 结构：公共 CSS/JS 去重合并内联；690 页正文以分块 `<script>` 存储（每块 ~3-5MB，
  规避巨型字符串/解析停顿）；图片 base64 直接内嵌在各页正文内，路由切页时才挂 DOM
  → 解码按需发生；`#/` hash 路由实现页面间跳转 + document.title 更新
- 图片**原图字节** base64（用户选定无损）；若实测首开 >15s，采取渐进措施：
  分块进一步细化 → PNG 用 lossless WebP 重编码（像素零损失）→ README 标注实测数据
- 产物放 `CFA_Notes/full_site_single_file.html`

### Git 管理

- 仓库根 = `CFA_Notes/`；.gitignore：`__pycache__/`、`tools/.build/`
- 提交序列：①原始镜像基线（已完成）②本设计文档 ③清洗构建 ④单文件构建 ⑤验证修订 ⑥README

## 边界（明确不做）

- 不重排版式、不清减正文（"一模一样"）
- 视频不修复（用户要求），仅移除网络挂起
- 不引入构建产物以外的依赖与抽象
