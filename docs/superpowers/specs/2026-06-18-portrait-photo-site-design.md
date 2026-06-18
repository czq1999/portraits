# 人像摄影每日图集站 · 设计文档

**日期**：2026-06-18
**状态**：设计已确认，待实现规划

---

## 1. 项目目标

一个每天自动更新的人像摄影图集站，内容来自各图片平台的官方策展集、高质量群组或经过质量阈值过滤的标签流。**不维护摄影师名单**——内容由平台策展和质量阈值决定。

部署在 GitHub Pages 上，由 GitHub Actions 定时抓取并提交，零运维成本。

非目标：不做账号系统、不做评论、不做投稿、不做完整作品归档。

## 2. 数据源

### 配置文件 `sources.yaml`

每个数据源是一条记录，描述"从哪个平台、用何种方式拉取、用什么质量阈值"。

```yaml
sources:
  - platform: unsplash
    type: topic
    id: people

  # 具体 collection / group / topic id 在实现阶段调研后填入。
  # 选取标准：官方策展 > 知名社区群组 > 高赞阈值标签搜索。

  - platform: flickr
    type: group
    id: portraitart

  - platform: flickr
    type: tag
    tag: portrait
    sort: interestingness
    min_faves: 100

  - platform: pexels
    type: search
    query: portrait
```

实际接入的平台与端点：

| 平台 | 接入方式 | 鉴权 | 备注 |
|---|---|---|---|
| Unsplash | 官方 API（`topics`、`collections`、`search/photos`） | API key（GitHub Secret） | 推荐 People topic + 策展集 |
| Flickr | 官方 API（`flickr.groups.pools.getPhotos`、`flickr.photos.search`） | API key（GitHub Secret） | tag 搜索可加 `min_faves` 过滤；按 interestingness 排序 |
| Pexels | 官方 API（`v1/search`） | API key（GitHub Secret） | 关键词 portrait |

### 暂不接入

500px / Behance / 个人站 RSS 在 MVP 中**不接入**——它们没有公开的"主题搜索"端点，与"主题驱动"思路不符。如果未来想加回特定来源，再扩展适配器。

### 适配器设计

每个 platform 一个适配器模块，统一暴露一个函数：

```
fetch(source_config) -> List[NormalizedPhoto]
```

`NormalizedPhoto` 是平台无关的数据结构，定义见 §4。

## 3. 抓取策略

### 触发

- **定时**：GitHub Actions cron `0 2 * * *`（每天 UTC 02:00 ≈ 北京时间 10:00）
- **手动**：`workflow_dispatch`，可在 GitHub 网页上点 Run workflow

### 容错

- 单个数据源抓取失败 → 记录到本次运行的失败列表，跳过该源继续其他源
- 工作流最后输出汇总：哪些源成功/失败、新增多少张
- 全部成功失败不中断 workflow（只在 step summary 标记），避免噪音通知

### 提交策略

- 抓取后与现有 `data/photos.json` diff
- 没有任何变化 → **不 commit**（避免空提交）
- 有变化 → commit 带消息 `chore(photos): daily update YYYY-MM-DD (+N -M)`，自动 push 触发 Pages 重建

### Secret 配置

GitHub repo Secrets 中需要：

- `UNSPLASH_ACCESS_KEY`
- `FLICKR_API_KEY`
- `PEXELS_API_KEY`

## 4. 数据存储

### 主索引 `data/photos.json`

一个 JSON 数组，每条记录：

```json
{
  "id": "flickr:54321678901",
  "source": "flickr",
  "source_kind": "group:portraitart",
  "original_url": "https://www.flickr.com/photos/...",
  "thumb_path": "thumbs/flickr-54321678901.webp",
  "author_name": "Jane Doe",
  "author_url": "https://www.flickr.com/people/janedoe/",
  "title": "Marta, II",
  "taken_at": "2026-06-15T14:30:00Z",
  "posted_at": "2026-06-17T09:12:00Z",
  "exif": {
    "camera": "Leica Q2",
    "lens": "28mm Summilux",
    "focal_length": "28mm",
    "aperture": "f/1.7",
    "shutter": "1/500",
    "iso": 400
  }
}
```

字段说明：

- `id`：全局唯一去重键，格式 `<platform>:<platform_photo_id>`
- `taken_at`：拍摄时间，平台未提供时为 `null`
- `posted_at`：发布到平台的时间——**首页排序依据**
- `exif`：每个字段允许缺失；不全的字段在 UI 上简单跳过
- 任何字符串字段缺失时为 `null` 或省略

数组按 `posted_at` 倒序，全局保留**最新 200 条**。超出按 `posted_at` 淘汰，对应缩略图同时删除。

### 缩略图 `public/thumbs/`

- 命名 `<source>-<photo_id>.webp`
- 最长边 1200px，质量 80
- 不保留原图，原图通过 `original_url` 跳转到原平台

预估总体积：200 张 × ~150KB ≈ 30MB，远低于 GitHub Pages 1GB 限额。

### 抓取流程的内部数据流

```
sources.yaml
   ↓ adapters
List[NormalizedPhoto]  （本次抓取的候选集）
   ↓ merge with existing data/photos.json (dedupe by id)
   ↓ keep top-200 by posted_at
   ↓ download thumbs for new entries; delete thumbs for removed entries
final data/photos.json + public/thumbs/
```

## 5. 前端

### 技术栈

- **Astro**：静态站点生成器，默认零 JS，按需局部加 vanilla JS（用于灯箱）
- 构建产物纯静态，部署到 GitHub Pages
- 内置 `<Image>` 组件用于响应式图片 + 懒加载

### 视觉风格 · Dark Room

- 背景 `#0a0a0a`，主文字 `#d4d4d4`，标题 `#f0f0f0`，弱化文字 `#555–#888`
- 字体：`Inter`（系统/Google Fonts），300/400 字重为主
- 标签类元数据使用极小号字体 + 高字距 + 大写字母（视觉上像画廊展签）
- 图片浮在深色背景上，配 `box-shadow: 0 20px 60px rgba(0,0,0,0.6)`，营造投影感
- 顶部一行极简标题栏（站名 + 简单 nav），其下空旷留白

### 页面结构

**只有一页**：`/`

- 顶部：极小号站标 `PORTRAITS · 2026`（或类似），不放任何导航
- 主区：瀑布流网格（CSS `column-count` 实现），按 `posted_at` 倒序
  - 桌面 3 列、平板 2 列、手机 1 列
  - 每张图加载时使用 `<Image>` 懒加载、`aspect-ratio` 占位避免抖动
  - 默认不显示作者名（保持 Dark Room 极简感），hover 时图片底部浮出小字 `<作者名> · <平台> · <日期>`

不做：摄影师索引、摄影师档案页、按平台筛选 tab、搜索、tag 浏览。

### 灯箱（点击图片打开）

布局：全屏黑底，桌面端左 70% 大图、右 30% 信息面板；移动端竖向堆叠。

信息面板内容：

- 标题（如有）
- 作者名 → 链接到该作者在原平台的页面
- 日期（`posted_at`）
- 平台名 + 来源类型（如 `Flickr · Group: portraitart`）
- EXIF（相机 / 镜头 / 焦距 / 光圈 / 快门 / ISO）—— 缺失字段直接不显示
- "在原平台查看 →" 跳转 `original_url`

交互：

- ← → 键切换上下张
- ESC 或点击空白处关闭
- 移动端左右滑动切换、下滑关闭
- 灯箱状态写入 URL hash（如 `#photo=flickr:54321678901`），刷新可恢复、可分享

### 浏览器兼容

不做 IE 支持。最低支持 2 年内的 Chrome/Safari/Firefox 主流版本。

## 6. 仓库结构

```
photo_project/
├── .github/
│   └── workflows/
│       └── update-photos.yml      # 定时抓取 workflow
├── scripts/
│   ├── fetch.py (or .ts)          # 抓取入口
│   └── adapters/
│       ├── unsplash.py
│       ├── flickr.py
│       └── pexels.py
├── sources.yaml                    # 数据源配置
├── data/
│   └── photos.json                 # 主索引（构建时被 Astro 读取）
├── public/
│   └── thumbs/                     # 缩略图
├── src/                            # Astro 源码
│   ├── pages/
│   │   └── index.astro
│   ├── components/
│   │   ├── PhotoGrid.astro
│   │   └── Lightbox.astro          # 含少量 vanilla JS
│   └── styles/
│       └── global.css
├── astro.config.mjs
├── package.json
└── docs/
    └── superpowers/
        └── specs/                  # 本设计文档所在
```

抓取脚本语言：**Python**（生态成熟、httpx + Pillow + PyYAML 即可，CI 启动快）。如未来需要可换 Node.js 跟前端统一，目前不强求。

## 7. 部署

- GitHub 仓库**公开**，仓库名在实现阶段确认（建议 `portraits` 或 `daily-portraits`）
- GitHub Pages 项目站点 URL：`https://<username>.github.io/<repo>/`
- 不使用自定义域名
- 部署方式：仓库根目录的 GitHub Actions workflow `pages.yml` 在 `data/` 或 `src/` 变化时构建 Astro 并发布到 `gh-pages` 分支（或使用官方 `actions/deploy-pages`）

两个独立 workflow，避免耦合：

- `update-photos.yml`：定时 + 手动触发，跑抓取，commit 数据变化
- `deploy.yml`：监听 `main` 分支 push，构建 Astro 并发布

数据 commit 触发 deploy，deploy 触发 Pages 更新。

## 8. 失败模式与人工介入

| 场景 | 行为 |
|---|---|
| 单个数据源 API 暂时挂了 | 跳过，下次 cron 再试 |
| API key 失效 / 配额耗尽 | 该源全部失败，workflow summary 高亮提示，用户手动更新 secret |
| 平台改变响应格式 | 适配器抛错，单源失败处理，用户看到日志后修代码 |
| 没有任何新照片 | 不 commit，workflow 正常退出 |
| 缩略图下载失败 | 跳过该照片（不写入 photos.json），下次重试 |

## 9. 范围与里程碑

**MVP（本设计文档对应实现）**

1. Astro 项目骨架 + Dark Room 静态首页（用 mock data 跑通）
2. Lightbox 组件（含键盘/移动端交互）
3. Python 抓取脚本 + 三个适配器（Unsplash / Flickr / Pexels）
4. `update-photos.yml` 定时抓取 workflow
5. `deploy.yml` 部署 workflow
6. 实际配置 `sources.yaml` 并跑通端到端

**MVP 之外（明确不做）**

- 任何形式的后台/账号
- 摄影师档案页
- 评论 / 收藏 / 投票
- 多语言
- 全文搜索
- 完整作品归档（>200 张）

未来可能扩展（不在本设计内）：

- 加入 RSS 适配器（让用户能订阅特定 RSS 源）
- 加入 500px / Behance 抓取（如果他们重新开放搜索 API）
- 主题/标签筛选 UI
