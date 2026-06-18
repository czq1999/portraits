# Portrait Photo Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个每日自动从 Unsplash / Flickr / Pexels 抓取人像作品并展示在 GitHub Pages 上的静态图集站。

**Architecture:** 两条独立流水线 —— Python 抓取脚本（CI 中每日运行，写入 `data/photos.json` + `public/thumbs/`）+ Astro 静态站点（在 `data` 变化后由另一个 workflow 构建并发布）。前端读 `data/photos.json` 渲染瀑布流，灯箱用极少量 vanilla JS。后端三个 platform 适配器实现统一的 `fetch(source) -> List[NormalizedPhoto]` 接口，由 `scripts/fetch.py` 调度。

**Tech Stack:** Python 3.11 + httpx + Pillow + PyYAML（抓取）；Astro 4 + TypeScript + vanilla JS（前端）；GitHub Actions（定时 + 部署）。

## Global Constraints

- 仓库公开，部署到 GitHub Pages 项目站点（路径形式 `/<repo>/`）。Astro 必须配置 `base` 反映这一点。
- `data/photos.json` 全局保留**最新 200 条**，按 `posted_at` 倒序；超出按 `posted_at` 淘汰，对应缩略图同时删除。
- 缩略图：WebP，最长边 1200px，质量 80，命名 `<source>-<photo_id>.webp`，路径 `public/thumbs/`。
- 唯一 ID 格式：`<platform>:<platform_photo_id>`（冒号分隔）。
- 单个数据源失败必须跳过、不中断整体抓取；汇总输出到 step summary。
- 没有数据变化时不 commit。
- 视觉规范：背景 `#0a0a0a`、主文字 `#d4d4d4`、标题 `#f0f0f0`、弱化 `#555–#888`；字体 Inter；元数据使用大写小字 + 高字距（letter-spacing 0.2em+）。
- 测试框架：后端 pytest；前端组件用快照/DOM 检查（vitest）。
- 频繁 commit：每个 task 末尾必须 commit。

---

## File Structure

```
photo_project/
├── .github/workflows/
│   ├── update-photos.yml          # 定时抓取 + 推送
│   └── deploy.yml                 # 构建 Astro 并部署 Pages
├── scripts/
│   ├── fetch.py                   # 抓取入口 / 调度器
│   ├── models.py                  # NormalizedPhoto 数据类
│   ├── store.py                   # photos.json 读写、合并、淘汰
│   ├── thumbs.py                  # 缩略图下载 + WebP 转换
│   └── adapters/
│       ├── __init__.py            # 适配器注册表
│       ├── base.py                # 公共 helper（HTTP 客户端、错误类型）
│       ├── unsplash.py
│       ├── flickr.py
│       └── pexels.py
├── tests/
│   ├── conftest.py                # pytest fixture
│   ├── test_models.py
│   ├── test_store.py
│   ├── test_thumbs.py
│   └── adapters/
│       ├── test_unsplash.py
│       ├── test_flickr.py
│       └── test_pexels.py
├── sources.yaml                   # 数据源配置
├── requirements.txt               # Python 依赖
├── pyproject.toml                 # ruff/pytest 配置
├── data/photos.json               # 主索引（构建时被 Astro 读取）
├── public/thumbs/                 # 缩略图
├── src/                           # Astro 源码
│   ├── pages/index.astro
│   ├── components/
│   │   ├── PhotoGrid.astro
│   │   ├── PhotoCard.astro
│   │   └── Lightbox.astro
│   ├── scripts/lightbox.ts        # 灯箱客户端逻辑
│   ├── styles/global.css
│   └── lib/
│       ├── photos.ts              # 读 photos.json 的 helper
│       └── format.ts              # 日期、EXIF 格式化
├── astro.config.mjs
├── package.json
├── tsconfig.json
├── .gitignore
└── docs/superpowers/{specs,plans}/
```

每个文件职责单一：模型只放数据类、store 只管 JSON 文件读写与淘汰、thumbs 只管缩略图下载与转换、每个 adapter 只懂自己平台的 API。前端 `Lightbox` 组件渲染骨架，交互逻辑在独立的 `lightbox.ts` 中。

---

## 任务总览

**Milestone A — 后端抓取管道**
- Task 1: 项目初始化（Python + 工具链）
- Task 2: NormalizedPhoto 数据模型
- Task 3: photos.json store（读、合并、淘汰、写）
- Task 4: 缩略图下载与 WebP 转换
- Task 5: 适配器基础设施
- Task 6: Unsplash 适配器
- Task 7: Flickr 适配器
- Task 8: Pexels 适配器
- Task 9: 抓取调度器 fetch.py（端到端）

**Milestone B — Astro 前端**
- Task 10: Astro 项目初始化 + 全局样式
- Task 11: 数据加载 helper + PhotoCard 组件
- Task 12: PhotoGrid 瀑布流 + 首页
- Task 13: Lightbox 组件 + 客户端交互

**Milestone C — CI/CD**
- Task 14: update-photos workflow（定时 + 手动 + 提交）
- Task 15: deploy workflow（构建 + 部署 Pages）


---

## Task 1: 项目初始化（Python + 工具链）

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `tests/conftest.py`
- Create: `scripts/__init__.py`
- Create: `scripts/adapters/__init__.py`

**Interfaces:**
- Consumes: 无
- Produces: 可运行的 `pytest` 与 `python -m scripts.fetch`（暂未实现 fetch，但 import 路径就位）

- [ ] **Step 1: 创建 `requirements.txt`**

```
httpx==0.27.2
Pillow==10.4.0
PyYAML==6.0.2
pytest==8.3.3
pytest-httpx==0.32.0
```

- [ ] **Step 2: 创建 `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 3: 创建 `.gitignore`**

```
# Python
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
*.egg-info/

# Node / Astro
node_modules/
dist/
.astro/

# OS
.DS_Store

# Brainstorm session artifacts
.superpowers/
```

- [ ] **Step 4: 创建 `scripts/__init__.py` 和 `scripts/adapters/__init__.py`（空文件）**

```python
# scripts/__init__.py
```

```python
# scripts/adapters/__init__.py
```

- [ ] **Step 5: 创建 `tests/conftest.py`**

```python
"""Pytest 配置：让 tests 目录能找到 scripts 包。"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
```

- [ ] **Step 6: 安装依赖并验证 pytest 启动**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest --collect-only
```

Expected: pytest 报告 `collected 0 items`（没有错误，只是还没测试）

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pyproject.toml .gitignore scripts/ tests/
git commit -m "chore: scaffold Python project with pytest + httpx + Pillow"
```

---

## Task 2: NormalizedPhoto 数据模型

**Files:**
- Create: `scripts/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `NormalizedPhoto` dataclass with fields: `id: str, source: str, source_kind: str, original_url: str, thumb_url: str, author_name: str, author_url: str, title: str | None, taken_at: str | None, posted_at: str, exif: dict[str, str | int | None]`
  - `NormalizedPhoto.to_dict() -> dict` 输出 photos.json 一条记录的形态（保留 `thumb_path` 字段供下游填充，**不**包含 `thumb_url`，因为后者只是抓取阶段的临时数据）
  - `make_id(platform: str, photo_id: str) -> str` 返回 `f"{platform}:{photo_id}"`

- [ ] **Step 1: 写失败的测试 `tests/test_models.py`**

```python
from scripts.models import NormalizedPhoto, make_id


def test_make_id_joins_with_colon():
    assert make_id("flickr", "12345") == "flickr:12345"


def test_normalized_photo_to_dict_basic():
    p = NormalizedPhoto(
        id="flickr:12345",
        source="flickr",
        source_kind="group:portraitart",
        original_url="https://www.flickr.com/photos/x/12345",
        thumb_url="https://live.staticflickr.com/.../12345_b.jpg",
        author_name="Jane Doe",
        author_url="https://www.flickr.com/people/jane/",
        title="Marta, II",
        taken_at="2026-06-15T14:30:00Z",
        posted_at="2026-06-17T09:12:00Z",
        exif={"camera": "Leica Q2", "aperture": "f/1.7"},
    )
    d = p.to_dict()
    assert d["id"] == "flickr:12345"
    assert d["source"] == "flickr"
    assert d["source_kind"] == "group:portraitart"
    assert d["thumb_path"] == "thumbs/flickr-12345.webp"
    assert "thumb_url" not in d  # 临时字段不应出现在持久化中
    assert d["exif"]["camera"] == "Leica Q2"


def test_to_dict_omits_optional_none_strings():
    p = NormalizedPhoto(
        id="pexels:99",
        source="pexels",
        source_kind="search:portrait",
        original_url="https://www.pexels.com/photo/99/",
        thumb_url="https://images.pexels.com/photos/99/large.jpg",
        author_name="A",
        author_url="https://www.pexels.com/@a",
        title=None,
        taken_at=None,
        posted_at="2026-06-18T00:00:00Z",
        exif={},
    )
    d = p.to_dict()
    assert "title" not in d
    assert "taken_at" not in d
    assert d["exif"] == {}
```

- [ ] **Step 2: 运行测试，验证失败**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL with `ImportError: cannot import name ...`

- [ ] **Step 3: 实现 `scripts/models.py`**

```python
"""统一的图片数据模型，所有适配器输出都要变成它。"""
from dataclasses import dataclass, field


def make_id(platform: str, photo_id: str) -> str:
    """全局唯一 ID 格式：<platform>:<photo_id>。"""
    return f"{platform}:{photo_id}"


def thumb_path_for(photo_id: str) -> str:
    """从 'flickr:12345' 推导出 'thumbs/flickr-12345.webp'。"""
    platform, raw_id = photo_id.split(":", 1)
    return f"thumbs/{platform}-{raw_id}.webp"


@dataclass
class NormalizedPhoto:
    """所有平台 API 响应被适配器转换成这个统一形态。"""

    id: str
    source: str
    source_kind: str
    original_url: str
    thumb_url: str  # 抓取阶段使用，不持久化
    author_name: str
    author_url: str
    title: str | None
    taken_at: str | None
    posted_at: str
    exif: dict[str, str | int | None] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """输出 photos.json 中一条记录的形态。"""
        d: dict = {
            "id": self.id,
            "source": self.source,
            "source_kind": self.source_kind,
            "original_url": self.original_url,
            "thumb_path": thumb_path_for(self.id),
            "author_name": self.author_name,
            "author_url": self.author_url,
            "posted_at": self.posted_at,
            "exif": self.exif,
        }
        if self.title is not None:
            d["title"] = self.title
        if self.taken_at is not None:
            d["taken_at"] = self.taken_at
        return d
```

- [ ] **Step 4: 运行测试，验证通过**

```bash
pytest tests/test_models.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/models.py tests/test_models.py
git commit -m "feat(models): NormalizedPhoto data class with id helpers"
```

---

## Task 3: photos.json store（读、合并、淘汰、写）

**Files:**
- Create: `scripts/store.py`
- Create: `tests/test_store.py`

**Interfaces:**
- Consumes: `NormalizedPhoto`、`thumb_path_for` from Task 2
- Produces:
  - `load_photos(path: Path) -> list[dict]` —— 不存在或为空时返回 `[]`
  - `save_photos(path: Path, photos: list[dict]) -> None` —— UTF-8、缩进 2、按 posted_at 倒序写入；目录不存在时自动创建
  - `merge_and_truncate(existing: list[dict], new_photos: list[NormalizedPhoto], max_keep: int = 200) -> tuple[list[dict], list[NormalizedPhoto], list[str]]`
    - 返回 `(merged, added_photos, removed_thumb_paths)`
    - `added_photos` 是真正进入 merged 的新照片（已去重过），下游会拿来下载缩略图
    - `removed_thumb_paths` 是因淘汰而需要从磁盘删除的 thumb 相对路径

- [ ] **Step 1: 写失败的测试 `tests/test_store.py`**

```python
from pathlib import Path

import pytest

from scripts.models import NormalizedPhoto
from scripts.store import load_photos, merge_and_truncate, save_photos


def make_norm(pid: str, posted: str) -> NormalizedPhoto:
    return NormalizedPhoto(
        id=pid,
        source=pid.split(":")[0],
        source_kind="topic:test",
        original_url=f"https://example.com/{pid}",
        thumb_url=f"https://cdn.example.com/{pid}.jpg",
        author_name="A",
        author_url="https://example.com/a",
        title=None,
        taken_at=None,
        posted_at=posted,
        exif={},
    )


def test_load_photos_returns_empty_when_missing(tmp_path: Path):
    assert load_photos(tmp_path / "nope.json") == []


def test_save_then_load_roundtrip(tmp_path: Path):
    target = tmp_path / "data" / "photos.json"
    photos = [{"id": "x:1", "posted_at": "2026-01-01T00:00:00Z"}]
    save_photos(target, photos)
    assert load_photos(target) == photos


def test_save_creates_parent_directory(tmp_path: Path):
    target = tmp_path / "deep" / "nested" / "photos.json"
    save_photos(target, [])
    assert target.exists()


def test_save_sorted_descending_by_posted_at(tmp_path: Path):
    target = tmp_path / "p.json"
    save_photos(
        target,
        [
            {"id": "a", "posted_at": "2026-01-01T00:00:00Z"},
            {"id": "b", "posted_at": "2026-03-01T00:00:00Z"},
            {"id": "c", "posted_at": "2026-02-01T00:00:00Z"},
        ],
    )
    loaded = load_photos(target)
    assert [p["id"] for p in loaded] == ["b", "c", "a"]


def test_merge_dedupes_existing_ids():
    existing = [{"id": "flickr:1", "posted_at": "2026-01-01T00:00:00Z", "thumb_path": "thumbs/flickr-1.webp"}]
    new = [make_norm("flickr:1", "2026-01-01T00:00:00Z")]
    merged, added, removed = merge_and_truncate(existing, new)
    assert len(merged) == 1
    assert added == []  # 没有真正新增
    assert removed == []


def test_merge_adds_new_photos():
    existing = [{"id": "flickr:1", "posted_at": "2026-01-01T00:00:00Z", "thumb_path": "thumbs/flickr-1.webp"}]
    new = [make_norm("pexels:9", "2026-02-01T00:00:00Z")]
    merged, added, removed = merge_and_truncate(existing, new)
    assert len(merged) == 2
    assert merged[0]["id"] == "pexels:9"  # 新的更晚发布，应排在前面
    assert len(added) == 1 and added[0].id == "pexels:9"
    assert removed == []


def test_merge_truncates_to_max_keep_and_reports_removed_thumbs():
    existing = [
        {"id": f"flickr:{i}", "posted_at": f"2026-01-{i:02d}T00:00:00Z", "thumb_path": f"thumbs/flickr-{i}.webp"}
        for i in range(1, 6)  # 5 张, 日期 01..05
    ]
    new = [make_norm("pexels:99", "2026-02-01T00:00:00Z")]
    merged, added, removed = merge_and_truncate(existing, new, max_keep=3)
    # 期望保留：pexels:99、flickr:5、flickr:4
    assert [p["id"] for p in merged] == ["pexels:99", "flickr:5", "flickr:4"]
    assert len(added) == 1
    # 被淘汰的：flickr:1, flickr:2, flickr:3 → 缩略图路径要被报告
    assert sorted(removed) == [
        "thumbs/flickr-1.webp",
        "thumbs/flickr-2.webp",
        "thumbs/flickr-3.webp",
    ]
```

- [ ] **Step 2: 运行测试，验证失败**

```bash
pytest tests/test_store.py -v
```

Expected: FAIL（ImportError）

- [ ] **Step 3: 实现 `scripts/store.py`**

```python
"""photos.json 的读写、合并、淘汰逻辑。"""
import json
from pathlib import Path

from scripts.models import NormalizedPhoto


def load_photos(path: Path) -> list[dict]:
    """读取 photos.json；不存在或为空则返回空列表。"""
    if not path.exists() or path.stat().st_size == 0:
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_photos(path: Path, photos: list[dict]) -> None:
    """写 photos.json：UTF-8、缩进 2、按 posted_at 倒序。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_photos = sorted(photos, key=lambda p: p.get("posted_at", ""), reverse=True)
    path.write_text(
        json.dumps(sorted_photos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def merge_and_truncate(
    existing: list[dict],
    new_photos: list[NormalizedPhoto],
    max_keep: int = 200,
) -> tuple[list[dict], list[NormalizedPhoto], list[str]]:
    """把新抓的照片合并进现有索引，按 posted_at 倒序保留 max_keep 条。

    返回三元组：
      merged: 合并后的全部记录（dict 形态）
      added:  本次真正进入 merged 的 NormalizedPhoto（用于下游下载缩略图）
      removed_thumb_paths: 因淘汰被踢出的记录的 thumb_path 列表（用于删除磁盘文件）
    """
    by_id: dict[str, dict] = {p["id"]: p for p in existing}
    added: list[NormalizedPhoto] = []
    for np in new_photos:
        if np.id in by_id:
            continue
        by_id[np.id] = np.to_dict()
        added.append(np)

    all_photos = sorted(by_id.values(), key=lambda p: p.get("posted_at", ""), reverse=True)
    keep = all_photos[:max_keep]
    drop = all_photos[max_keep:]

    kept_ids = {p["id"] for p in keep}
    # 仅当一个 id 既被淘汰又不在新增（也就是说本来就在 existing 里）时，才需要删 thumb
    removed_thumb_paths = [
        p["thumb_path"] for p in drop if p.get("thumb_path") and p["id"] not in kept_ids
    ]

    # 如果新加入的照片本身就被立刻淘汰（比 max_keep 边界还旧），从 added 移除以免下游白下载
    added = [np for np in added if np.id in kept_ids]

    return keep, added, removed_thumb_paths
```

- [ ] **Step 4: 运行测试，验证通过**

```bash
pytest tests/test_store.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/store.py tests/test_store.py
git commit -m "feat(store): photos.json load/save/merge/truncate"
```

---

## Task 4: 缩略图下载与 WebP 转换

**Files:**
- Create: `scripts/thumbs.py`
- Create: `tests/test_thumbs.py`

**Interfaces:**
- Consumes: 无外部 task 依赖（自包含的 IO 模块）
- Produces:
  - `download_and_convert(thumb_url: str, dest: Path, *, max_edge: int = 1200, quality: int = 80, client: httpx.Client | None = None) -> bool` —— 成功写盘返回 True；任何失败（HTTP 错误、解码失败）返回 False，调用方负责跳过该照片。
  - `delete_thumbs(thumb_paths: list[str], base_dir: Path) -> None` —— 静默忽略不存在的文件。

- [ ] **Step 1: 写失败的测试 `tests/test_thumbs.py`**

```python
import io
from pathlib import Path

import httpx
import pytest
from PIL import Image
from pytest_httpx import HTTPXMock

from scripts.thumbs import delete_thumbs, download_and_convert


def make_jpeg_bytes(width: int, height: int, color=(120, 80, 80)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_download_writes_webp_and_resizes_long_edge(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://cdn.example.com/big.jpg", content=make_jpeg_bytes(3000, 2000))
    dest = tmp_path / "thumbs" / "x-1.webp"
    with httpx.Client() as c:
        ok = download_and_convert("https://cdn.example.com/big.jpg", dest, client=c)
    assert ok is True
    assert dest.exists()
    with Image.open(dest) as im:
        assert im.format == "WEBP"
        assert max(im.size) == 1200  # long edge resized
        assert im.size[0] == 1200 and im.size[1] == 800  # ratio preserved


def test_download_does_not_upscale_smaller_image(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://cdn.example.com/small.jpg", content=make_jpeg_bytes(800, 600))
    dest = tmp_path / "x-2.webp"
    with httpx.Client() as c:
        download_and_convert("https://cdn.example.com/small.jpg", dest, client=c)
    with Image.open(dest) as im:
        assert im.size == (800, 600)


def test_download_returns_false_on_http_error(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://cdn.example.com/404.jpg", status_code=404)
    dest = tmp_path / "x-3.webp"
    with httpx.Client() as c:
        ok = download_and_convert("https://cdn.example.com/404.jpg", dest, client=c)
    assert ok is False
    assert not dest.exists()


def test_download_returns_false_on_invalid_image_data(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://cdn.example.com/bad.jpg", content=b"not an image")
    dest = tmp_path / "x-4.webp"
    with httpx.Client() as c:
        ok = download_and_convert("https://cdn.example.com/bad.jpg", dest, client=c)
    assert ok is False


def test_delete_thumbs_removes_files_silently(tmp_path: Path):
    base = tmp_path / "public"
    (base / "thumbs").mkdir(parents=True)
    f1 = base / "thumbs" / "flickr-1.webp"
    f2 = base / "thumbs" / "flickr-2.webp"
    f1.write_bytes(b"x")
    f2.write_bytes(b"y")
    delete_thumbs(["thumbs/flickr-1.webp", "thumbs/flickr-2.webp", "thumbs/missing.webp"], base)
    assert not f1.exists() and not f2.exists()  # 不存在的文件不报错
```

- [ ] **Step 2: 运行测试，验证失败**

```bash
pytest tests/test_thumbs.py -v
```

Expected: FAIL（ImportError）

- [ ] **Step 3: 实现 `scripts/thumbs.py`**

```python
"""缩略图下载、转 WebP、批量删除。"""
import io
import logging
from pathlib import Path

import httpx
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


def download_and_convert(
    thumb_url: str,
    dest: Path,
    *,
    max_edge: int = 1200,
    quality: int = 80,
    client: httpx.Client | None = None,
) -> bool:
    """下载图片，按最长边缩放（不放大），转 WebP 写到 dest。

    任何错误（网络、解码）都返回 False，调用方跳过该照片即可。
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        try:
            resp = client.get(thumb_url, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("thumbnail download failed: %s (%s)", thumb_url, e)
            return False

        try:
            img = Image.open(io.BytesIO(resp.content))
            img.load()  # 强制解码以触发错误
        except (UnidentifiedImageError, OSError) as e:
            logger.warning("thumbnail decode failed: %s (%s)", thumb_url, e)
            return False

        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        long_edge = max(img.size)
        if long_edge > max_edge:
            ratio = max_edge / long_edge
            new_size = (round(img.size[0] * ratio), round(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, format="WEBP", quality=quality, method=4)
        return True
    finally:
        if owns_client:
            client.close()


def delete_thumbs(thumb_paths: list[str], base_dir: Path) -> None:
    """从 base_dir/<thumb_path> 删除一组缩略图，不存在的文件静默忽略。"""
    for rel in thumb_paths:
        target = base_dir / rel
        try:
            target.unlink()
        except FileNotFoundError:
            pass
```

- [ ] **Step 4: 运行测试，验证通过**

```bash
pytest tests/test_thumbs.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/thumbs.py tests/test_thumbs.py
git commit -m "feat(thumbs): download + WebP convert + batch delete"
```


---

## Task 5: 适配器基础设施

**Files:**
- Create: `scripts/adapters/base.py`
- Modify: `scripts/adapters/__init__.py`（变为注册表入口）

**Interfaces:**
- Consumes: 无
- Produces:
  - `class AdapterError(Exception)` —— 所有适配器抛出的标准错误类型，调度器据此跳过单源
  - `make_client(api_key_header: dict[str, str] | None = None) -> httpx.Client` —— 共享的带 timeout 和 UA 的 httpx.Client
  - `scripts.adapters.__init__` 导出 `ADAPTERS: dict[str, Callable[[dict, httpx.Client], list[NormalizedPhoto]]]`，键是 `platform` 名（`"unsplash"`、`"flickr"`、`"pexels"`），值是该平台的 `fetch` 函数。注册在每个适配器模块自身完成（见后续 task）。

- [ ] **Step 1: 写失败的测试**

```python
# tests/adapters/__init__.py（空文件）
# tests/adapters/test_base.py
from scripts.adapters.base import AdapterError, make_client


def test_adapter_error_is_exception():
    err = AdapterError("nope")
    assert isinstance(err, Exception)
    assert str(err) == "nope"


def test_make_client_has_timeout_and_user_agent():
    with make_client() as c:
        assert c.timeout.connect is not None
        assert "portrait-photo-site" in c.headers["user-agent"].lower()
```

```bash
mkdir -p tests/adapters
touch tests/adapters/__init__.py
pytest tests/adapters/test_base.py -v
```

Expected: FAIL（ImportError）

- [ ] **Step 2: 实现 `scripts/adapters/base.py`**

```python
"""适配器之间共享的 HTTP 客户端工厂和错误类型。"""
import httpx

USER_AGENT = "portrait-photo-site/1.0 (+https://github.com/)"


class AdapterError(Exception):
    """适配器抓取失败时抛出，调度器捕获后会跳过该源继续其他源。"""


def make_client(extra_headers: dict[str, str] | None = None) -> httpx.Client:
    """统一的 httpx.Client：30s 超时、固定 UA、调用方自行管理生命周期。"""
    headers = {"User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    return httpx.Client(timeout=30.0, headers=headers, follow_redirects=True)
```

- [ ] **Step 3: 改 `scripts/adapters/__init__.py` 为注册表**

```python
"""适配器注册表。每个具体适配器模块在自身被 import 时把自己注册进 ADAPTERS。"""
from collections.abc import Callable

import httpx

from scripts.models import NormalizedPhoto

FetchFn = Callable[[dict, httpx.Client], list[NormalizedPhoto]]
ADAPTERS: dict[str, FetchFn] = {}


def register(platform: str, fn: FetchFn) -> None:
    ADAPTERS[platform] = fn
```

- [ ] **Step 4: 运行测试，验证通过**

```bash
pytest tests/adapters/test_base.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/adapters/base.py scripts/adapters/__init__.py tests/adapters/
git commit -m "feat(adapters): base error type, http client, registry"
```

---

## Task 6: Unsplash 适配器

**Files:**
- Create: `scripts/adapters/unsplash.py`
- Create: `tests/adapters/test_unsplash.py`

**Interfaces:**
- Consumes: `AdapterError`, `make_client`, `NormalizedPhoto`, `make_id`, `register`
- Produces:
  - `fetch(source: dict, client: httpx.Client) -> list[NormalizedPhoto]`
  - 支持的 source 形态：
    - `{platform: unsplash, type: topic, id: people}` → `GET /topics/{id}/photos?per_page=30&order_by=latest`
    - `{platform: unsplash, type: collection, id: <num>}` → `GET /collections/{id}/photos?per_page=30`
    - `{platform: unsplash, type: search, query: portrait}` → `GET /search/photos?query={q}&per_page=30&order_by=latest`
  - 模块在 import 时自动 `register("unsplash", fetch)`
  - API key 来自环境变量 `UNSPLASH_ACCESS_KEY`；缺失抛 `AdapterError`

**关键字段映射（Unsplash → NormalizedPhoto）**

| Unsplash 响应 | NormalizedPhoto |
|---|---|
| `id` | `id = make_id("unsplash", id)` |
| `links.html` | `original_url` |
| `urls.regular` | `thumb_url` |
| `user.name` | `author_name` |
| `user.links.html` | `author_url` |
| `description` 或 `alt_description` | `title` |
| `created_at` | `posted_at`（已是 ISO8601 with timezone） |
| `exif.make + " " + exif.model` | `exif.camera`（缺失则跳过） |
| `exif.exposure_time` | `exif.shutter` |
| `exif.aperture` | `exif.aperture`（前面加 `f/`） |
| `exif.focal_length` | `exif.focal_length`（后面加 `mm`） |
| `exif.iso` | `exif.iso` |
| `taken_at` | `null`（Unsplash 不可靠提供，统一不填） |

`source_kind` = `f"{type}:{id_or_query}"`，例如 `topic:people`、`search:portrait`。

- [ ] **Step 1: 写失败的测试**

```python
# tests/adapters/test_unsplash.py
import httpx
import pytest
from pytest_httpx import HTTPXMock

from scripts.adapters import ADAPTERS
from scripts.adapters.base import AdapterError
from scripts.adapters.unsplash import fetch


SAMPLE = {
    "id": "abc123",
    "created_at": "2026-06-15T10:00:00-04:00",
    "description": "Portrait of Marta",
    "alt_description": None,
    "urls": {"regular": "https://images.unsplash.com/photo-abc?w=1200"},
    "links": {"html": "https://unsplash.com/photos/abc123"},
    "user": {
        "name": "Jane Doe",
        "links": {"html": "https://unsplash.com/@janedoe"},
    },
    "exif": {
        "make": "Leica",
        "model": "Q2",
        "exposure_time": "1/500",
        "aperture": "1.7",
        "focal_length": "28",
        "iso": 400,
    },
}


def test_unsplash_registered_in_adapters():
    assert "unsplash" in ADAPTERS


def test_fetch_topic_normalizes_response(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-key")
    httpx_mock.add_response(
        url="https://api.unsplash.com/topics/people/photos?per_page=30&order_by=latest",
        json=[SAMPLE],
        match_headers={"Authorization": "Client-ID test-key"},
    )
    with httpx.Client() as c:
        photos = fetch({"platform": "unsplash", "type": "topic", "id": "people"}, c)
    assert len(photos) == 1
    p = photos[0]
    assert p.id == "unsplash:abc123"
    assert p.source == "unsplash"
    assert p.source_kind == "topic:people"
    assert p.original_url == "https://unsplash.com/photos/abc123"
    assert p.thumb_url == "https://images.unsplash.com/photo-abc?w=1200"
    assert p.author_name == "Jane Doe"
    assert p.author_url == "https://unsplash.com/@janedoe"
    assert p.title == "Portrait of Marta"
    assert p.posted_at == "2026-06-15T10:00:00-04:00"
    assert p.taken_at is None
    assert p.exif["camera"] == "Leica Q2"
    assert p.exif["aperture"] == "f/1.7"
    assert p.exif["focal_length"] == "28mm"
    assert p.exif["shutter"] == "1/500"
    assert p.exif["iso"] == 400


def test_fetch_search_uses_search_endpoint(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-key")
    httpx_mock.add_response(
        url="https://api.unsplash.com/search/photos?query=portrait&per_page=30&order_by=latest",
        json={"results": [SAMPLE]},
    )
    with httpx.Client() as c:
        photos = fetch({"platform": "unsplash", "type": "search", "query": "portrait"}, c)
    assert len(photos) == 1
    assert photos[0].source_kind == "search:portrait"


def test_fetch_collection(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-key")
    httpx_mock.add_response(
        url="https://api.unsplash.com/collections/12345/photos?per_page=30",
        json=[SAMPLE],
    )
    with httpx.Client() as c:
        photos = fetch({"platform": "unsplash", "type": "collection", "id": "12345"}, c)
    assert photos[0].source_kind == "collection:12345"


def test_fetch_raises_when_key_missing(monkeypatch):
    monkeypatch.delenv("UNSPLASH_ACCESS_KEY", raising=False)
    with httpx.Client() as c, pytest.raises(AdapterError, match="UNSPLASH_ACCESS_KEY"):
        fetch({"platform": "unsplash", "type": "topic", "id": "people"}, c)


def test_fetch_raises_on_http_error(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-key")
    httpx_mock.add_response(
        url="https://api.unsplash.com/topics/people/photos?per_page=30&order_by=latest",
        status_code=429,
    )
    with httpx.Client() as c, pytest.raises(AdapterError):
        fetch({"platform": "unsplash", "type": "topic", "id": "people"}, c)


def test_fetch_raises_on_unknown_type(monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-key")
    with httpx.Client() as c, pytest.raises(AdapterError, match="unknown type"):
        fetch({"platform": "unsplash", "type": "weird"}, c)
```

```bash
pytest tests/adapters/test_unsplash.py -v
```

Expected: FAIL（ImportError）

- [ ] **Step 2: 实现 `scripts/adapters/unsplash.py`**

```python
"""Unsplash 适配器：topic / collection / search 三种来源。"""
import os

import httpx

from scripts.adapters import register
from scripts.adapters.base import AdapterError
from scripts.models import NormalizedPhoto, make_id

API = "https://api.unsplash.com"


def _exif_from(raw: dict | None) -> dict:
    """把 Unsplash 的 exif 字段转换成我们的统一形态；缺失字段直接不放。"""
    if not raw:
        return {}
    out: dict[str, str | int | None] = {}
    make = raw.get("make")
    model = raw.get("model")
    if make and model:
        out["camera"] = f"{make} {model}".strip()
    elif make or model:
        out["camera"] = (make or model or "").strip()
    if raw.get("exposure_time"):
        out["shutter"] = raw["exposure_time"]
    if raw.get("aperture"):
        out["aperture"] = f"f/{raw['aperture']}"
    if raw.get("focal_length"):
        out["focal_length"] = f"{raw['focal_length']}mm"
    if raw.get("iso") is not None:
        out["iso"] = raw["iso"]
    return out


def _normalize(item: dict, source_kind: str) -> NormalizedPhoto:
    return NormalizedPhoto(
        id=make_id("unsplash", item["id"]),
        source="unsplash",
        source_kind=source_kind,
        original_url=item["links"]["html"],
        thumb_url=item["urls"]["regular"],
        author_name=item["user"]["name"],
        author_url=item["user"]["links"]["html"],
        title=item.get("description") or item.get("alt_description") or None,
        taken_at=None,
        posted_at=item["created_at"],
        exif=_exif_from(item.get("exif")),
    )


def fetch(source: dict, client: httpx.Client) -> list[NormalizedPhoto]:
    api_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not api_key:
        raise AdapterError("UNSPLASH_ACCESS_KEY not set")

    headers = {"Authorization": f"Client-ID {api_key}"}
    stype = source.get("type")
    try:
        if stype == "topic":
            tid = source["id"]
            r = client.get(
                f"{API}/topics/{tid}/photos",
                params={"per_page": 30, "order_by": "latest"},
                headers=headers,
            )
            r.raise_for_status()
            items = r.json()
            kind = f"topic:{tid}"
        elif stype == "collection":
            cid = source["id"]
            r = client.get(
                f"{API}/collections/{cid}/photos",
                params={"per_page": 30},
                headers=headers,
            )
            r.raise_for_status()
            items = r.json()
            kind = f"collection:{cid}"
        elif stype == "search":
            q = source["query"]
            r = client.get(
                f"{API}/search/photos",
                params={"query": q, "per_page": 30, "order_by": "latest"},
                headers=headers,
            )
            r.raise_for_status()
            items = r.json().get("results", [])
            kind = f"search:{q}"
        else:
            raise AdapterError(f"unknown type for unsplash: {stype}")
    except httpx.HTTPError as e:
        raise AdapterError(f"unsplash http error: {e}") from e

    return [_normalize(it, kind) for it in items]


register("unsplash", fetch)
```

- [ ] **Step 3: 让模块在测试时被自动 import（这样 ADAPTERS 才会被注册）**

修改 `scripts/adapters/__init__.py` 末尾追加：

```python
# 自动 import 各适配器模块以触发 register() 调用
from scripts.adapters import flickr, pexels, unsplash  # noqa: E402,F401
```

注意：因为 `flickr` 和 `pexels` 还没创建，先把它们注释掉，等到对应 task 时再启用。当前阶段写：

```python
from scripts.adapters import unsplash  # noqa: E402,F401
```

- [ ] **Step 4: 运行测试，验证通过**

```bash
pytest tests/adapters/test_unsplash.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/adapters/unsplash.py scripts/adapters/__init__.py tests/adapters/test_unsplash.py
git commit -m "feat(adapters): unsplash adapter (topic/collection/search)"
```

---

## Task 7: Flickr 适配器

**Files:**
- Create: `scripts/adapters/flickr.py`
- Create: `tests/adapters/test_flickr.py`
- Modify: `scripts/adapters/__init__.py`（启用 flickr import）

**Interfaces:**
- Consumes: 同 Task 6
- Produces:
  - `fetch(source, client)` 处理两种 source：
    - `{platform: flickr, type: group, id: <group_id_or_path_alias>}` → `flickr.groups.pools.getPhotos`
    - `{platform: flickr, type: tag, tag: portrait, sort: interestingness, min_faves: 100}` → `flickr.photos.search`
  - REST endpoint: `https://api.flickr.com/services/rest/`，所有请求加 `format=json&nojsoncallback=1&extras=date_upload,date_taken,owner_name,url_l,path_alias`
  - API key 来自 `FLICKR_API_KEY`；缺失抛 `AdapterError`

**Flickr 响应 → NormalizedPhoto 的关键映射**

每条 photo 对象（来自 `photos.photo` 数组）包含：

| Flickr 字段 | 处理 |
|---|---|
| `id` | `make_id("flickr", id)` |
| `owner` + `pathalias` | `original_url = f"https://www.flickr.com/photos/{pathalias or owner}/{id}"` |
| `url_l` | `thumb_url`（缺失则用 `https://live.staticflickr.com/{server}/{id}_{secret}_b.jpg` 兜底） |
| `ownername` | `author_name` |
| `pathalias or owner` | `author_url = f"https://www.flickr.com/people/{pathalias or owner}/"` |
| `title` | `title`（空字符串归一化为 None） |
| `dateupload`（unix epoch 字符串） | `posted_at = ISO8601 UTC` |
| `datetaken`（如 "2026-06-15 14:30:00"） | `taken_at = f"{date}T{time}Z"`（Flickr 这个字段一般不带时区，统一标 Z 表示"无时区信息但归一为字符串"） |
| `exif` | 不通过 search 提供，保持 `{}`；EXIF 单独通过 `flickr.photos.getExif` 拉取要多一次请求，**MVP 暂不拉**（spec 同意 EXIF 缺失字段直接不显示） |

`source_kind`：
- group: `f"group:{id}"`
- tag: `f"tag:{tag}"`

`min_faves` 仅在 `tag` 模式下应用，作为 `flickr.photos.search` 参数 `min_faves=...`（注意：Flickr 真实 API 没有官方 `min_faves` 参数，但 `interestingness` 排序已经过滤大量低质量结果；如果用户在配置中写了 `min_faves`，我们在客户端筛除，因为 `count_faves` 不在 search 默认 extras 里 —— **MVP 阶段：把 `min_faves` 选项写进 source schema 但实现为 no-op，且在日志里 warn 说"min_faves 暂未实现"**，避免阻塞主流程）。

- [ ] **Step 1: 写失败的测试 `tests/adapters/test_flickr.py`**

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock

from scripts.adapters import ADAPTERS
from scripts.adapters.base import AdapterError
from scripts.adapters.flickr import fetch


SAMPLE_PHOTO = {
    "id": "54321",
    "owner": "12345@N00",
    "secret": "abc",
    "server": "65535",
    "title": "Marta, II",
    "ownername": "Jane Doe",
    "pathalias": "janedoe",
    "dateupload": "1781712000",  # 2026-06-17 ~12:00 UTC
    "datetaken": "2026-06-15 14:30:00",
    "url_l": "https://live.staticflickr.com/65535/54321_abc_b.jpg",
}


def test_flickr_registered():
    assert "flickr" in ADAPTERS


def test_fetch_group(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("FLICKR_API_KEY", "k")
    httpx_mock.add_response(
        url__startswith="https://api.flickr.com/services/rest/",
        match_query_params={
            "method": "flickr.groups.pools.getPhotos",
            "group_id": "portraitart",
            "api_key": "k",
            "format": "json",
            "nojsoncallback": "1",
        },
        json={"photos": {"photo": [SAMPLE_PHOTO]}, "stat": "ok"},
    )
    with httpx.Client() as c:
        photos = fetch({"platform": "flickr", "type": "group", "id": "portraitart"}, c)
    assert len(photos) == 1
    p = photos[0]
    assert p.id == "flickr:54321"
    assert p.source_kind == "group:portraitart"
    assert p.original_url == "https://www.flickr.com/photos/janedoe/54321"
    assert p.thumb_url == "https://live.staticflickr.com/65535/54321_abc_b.jpg"
    assert p.author_name == "Jane Doe"
    assert p.author_url == "https://www.flickr.com/people/janedoe/"
    assert p.title == "Marta, II"
    assert p.posted_at == "2026-06-17T12:00:00Z"
    assert p.taken_at == "2026-06-15T14:30:00Z"
    assert p.exif == {}


def test_fetch_tag_uses_search_method(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("FLICKR_API_KEY", "k")
    httpx_mock.add_response(
        url__startswith="https://api.flickr.com/services/rest/",
        match_query_params={
            "method": "flickr.photos.search",
            "tags": "portrait",
            "sort": "interestingness-desc",
            "api_key": "k",
            "format": "json",
            "nojsoncallback": "1",
        },
        json={"photos": {"photo": [SAMPLE_PHOTO]}, "stat": "ok"},
    )
    with httpx.Client() as c:
        photos = fetch(
            {"platform": "flickr", "type": "tag", "tag": "portrait", "sort": "interestingness"},
            c,
        )
    assert photos[0].source_kind == "tag:portrait"


def test_fetch_uses_url_fallback_when_url_l_missing(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("FLICKR_API_KEY", "k")
    photo = {**SAMPLE_PHOTO}
    del photo["url_l"]
    httpx_mock.add_response(
        url__startswith="https://api.flickr.com/services/rest/",
        json={"photos": {"photo": [photo]}, "stat": "ok"},
    )
    with httpx.Client() as c:
        photos = fetch({"platform": "flickr", "type": "group", "id": "x"}, c)
    assert photos[0].thumb_url == "https://live.staticflickr.com/65535/54321_abc_b.jpg"


def test_fetch_uses_owner_when_pathalias_empty(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("FLICKR_API_KEY", "k")
    photo = {**SAMPLE_PHOTO, "pathalias": None}
    httpx_mock.add_response(
        url__startswith="https://api.flickr.com/services/rest/",
        json={"photos": {"photo": [photo]}, "stat": "ok"},
    )
    with httpx.Client() as c:
        photos = fetch({"platform": "flickr", "type": "group", "id": "x"}, c)
    assert photos[0].original_url == "https://www.flickr.com/photos/12345@N00/54321"


def test_fetch_raises_when_key_missing(monkeypatch):
    monkeypatch.delenv("FLICKR_API_KEY", raising=False)
    with httpx.Client() as c, pytest.raises(AdapterError, match="FLICKR_API_KEY"):
        fetch({"platform": "flickr", "type": "group", "id": "x"}, c)


def test_fetch_raises_when_stat_fail(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("FLICKR_API_KEY", "k")
    httpx_mock.add_response(
        url__startswith="https://api.flickr.com/services/rest/",
        json={"stat": "fail", "code": 1, "message": "Group not found"},
    )
    with httpx.Client() as c, pytest.raises(AdapterError, match="Group not found"):
        fetch({"platform": "flickr", "type": "group", "id": "ghost"}, c)
```

```bash
pytest tests/adapters/test_flickr.py -v
```

Expected: FAIL（ImportError）

- [ ] **Step 2: 实现 `scripts/adapters/flickr.py`**

```python
"""Flickr 适配器：group pool 与 tag search 两种 source。"""
import logging
import os
from datetime import datetime, timezone

import httpx

from scripts.adapters import register
from scripts.adapters.base import AdapterError
from scripts.models import NormalizedPhoto, make_id

REST = "https://api.flickr.com/services/rest/"
EXTRAS = "date_upload,date_taken,owner_name,url_l,path_alias"

logger = logging.getLogger(__name__)


def _build_thumb_fallback(p: dict) -> str:
    return f"https://live.staticflickr.com/{p['server']}/{p['id']}_{p['secret']}_b.jpg"


def _normalize(p: dict, source_kind: str) -> NormalizedPhoto:
    pid = p["id"]
    pathalias = p.get("pathalias") or p["owner"]
    posted_dt = datetime.fromtimestamp(int(p["dateupload"]), tz=timezone.utc)
    posted_at = posted_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    taken_at: str | None = None
    if p.get("datetaken"):
        # Flickr 返回 "YYYY-MM-DD HH:MM:SS"，无时区，转成 ISO8601 末尾加 Z
        date, time = p["datetaken"].split(" ", 1)
        taken_at = f"{date}T{time}Z"

    title = p.get("title") or None

    return NormalizedPhoto(
        id=make_id("flickr", pid),
        source="flickr",
        source_kind=source_kind,
        original_url=f"https://www.flickr.com/photos/{pathalias}/{pid}",
        thumb_url=p.get("url_l") or _build_thumb_fallback(p),
        author_name=p.get("ownername", ""),
        author_url=f"https://www.flickr.com/people/{pathalias}/",
        title=title,
        taken_at=taken_at,
        posted_at=posted_at,
        exif={},
    )


def _call(client: httpx.Client, params: dict) -> list[dict]:
    try:
        r = client.get(REST, params=params)
        r.raise_for_status()
        body = r.json()
    except httpx.HTTPError as e:
        raise AdapterError(f"flickr http error: {e}") from e

    if body.get("stat") != "ok":
        raise AdapterError(f"flickr api error: {body.get('message', 'unknown')}")
    return body.get("photos", {}).get("photo", [])


def fetch(source: dict, client: httpx.Client) -> list[NormalizedPhoto]:
    api_key = os.environ.get("FLICKR_API_KEY")
    if not api_key:
        raise AdapterError("FLICKR_API_KEY not set")

    base = {
        "api_key": api_key,
        "format": "json",
        "nojsoncallback": "1",
        "extras": EXTRAS,
        "per_page": "30",
    }

    stype = source.get("type")
    if stype == "group":
        gid = source["id"]
        params = {**base, "method": "flickr.groups.pools.getPhotos", "group_id": gid}
        kind = f"group:{gid}"
    elif stype == "tag":
        tag = source["tag"]
        sort = source.get("sort", "interestingness")
        params = {
            **base,
            "method": "flickr.photos.search",
            "tags": tag,
            "sort": f"{sort}-desc",
        }
        if source.get("min_faves"):
            logger.warning("flickr: min_faves option is not implemented; ignored")
        kind = f"tag:{tag}"
    else:
        raise AdapterError(f"unknown type for flickr: {stype}")

    raw = _call(client, params)
    return [_normalize(p, kind) for p in raw]


register("flickr", fetch)
```

- [ ] **Step 3: 启用 `scripts/adapters/__init__.py` 中的 flickr import**

```python
from scripts.adapters import flickr, unsplash  # noqa: E402,F401
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/adapters/test_flickr.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/adapters/flickr.py scripts/adapters/__init__.py tests/adapters/test_flickr.py
git commit -m "feat(adapters): flickr adapter (group + tag search)"
```

---

## Task 8: Pexels 适配器

**Files:**
- Create: `scripts/adapters/pexels.py`
- Create: `tests/adapters/test_pexels.py`
- Modify: `scripts/adapters/__init__.py`（启用 pexels import）

**Interfaces:**
- Consumes: 同 Task 6
- Produces:
  - `fetch(source, client)` 处理 `{platform: pexels, type: search, query: portrait}` → `GET https://api.pexels.com/v1/search?query={q}&per_page=30`
  - 鉴权头 `Authorization: <PEXELS_API_KEY>`
  - 缺失 key → `AdapterError`

**字段映射**

| Pexels | NormalizedPhoto |
|---|---|
| `id` | `make_id("pexels", str(id))` |
| `url` | `original_url` |
| `src.large` | `thumb_url` |
| `photographer` | `author_name` |
| `photographer_url` | `author_url` |
| `alt` | `title`（空字符串归一化 None） |
| `created_at` *(若 API 返回)* 否则当天作为 fallback | `posted_at` |
| EXIF | Pexels v1 不提供，`{}` |
| `taken_at` | `null` |

**关于 posted_at：** Pexels 的 `/v1/search` 响应**不**包含 `created_at` 字段。MVP 处理：用脚本运行时的当前时间作为 `posted_at`，并在 `exif` 中放空，理由是 Pexels search 的结果本身就没有发布时间信息可用（这与 Unsplash 不同）。具体实现传入 `now_iso` 参数以便测试可注入。

- [ ] **Step 1: 写失败的测试**

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock

from scripts.adapters import ADAPTERS
from scripts.adapters.base import AdapterError
from scripts.adapters.pexels import fetch


SAMPLE = {
    "id": 99,
    "url": "https://www.pexels.com/photo/99/",
    "photographer": "A",
    "photographer_url": "https://www.pexels.com/@a",
    "alt": "A portrait",
    "src": {"large": "https://images.pexels.com/photos/99/large.jpg"},
}


def test_pexels_registered():
    assert "pexels" in ADAPTERS


def test_fetch_search(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "k")
    httpx_mock.add_response(
        url="https://api.pexels.com/v1/search?query=portrait&per_page=30",
        match_headers={"Authorization": "k"},
        json={"photos": [SAMPLE]},
    )
    with httpx.Client() as c:
        photos = fetch(
            {"platform": "pexels", "type": "search", "query": "portrait"},
            c,
            now_iso="2026-06-18T03:00:00Z",
        )
    assert len(photos) == 1
    p = photos[0]
    assert p.id == "pexels:99"
    assert p.source_kind == "search:portrait"
    assert p.original_url == "https://www.pexels.com/photo/99/"
    assert p.thumb_url == "https://images.pexels.com/photos/99/large.jpg"
    assert p.author_name == "A"
    assert p.title == "A portrait"
    assert p.posted_at == "2026-06-18T03:00:00Z"


def test_fetch_treats_empty_alt_as_no_title(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "k")
    s = {**SAMPLE, "alt": ""}
    httpx_mock.add_response(json={"photos": [s]})
    with httpx.Client() as c:
        photos = fetch(
            {"platform": "pexels", "type": "search", "query": "portrait"},
            c,
            now_iso="2026-06-18T03:00:00Z",
        )
    assert photos[0].title is None


def test_fetch_raises_when_key_missing(monkeypatch):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    with httpx.Client() as c, pytest.raises(AdapterError, match="PEXELS_API_KEY"):
        fetch({"platform": "pexels", "type": "search", "query": "x"}, c)


def test_fetch_raises_on_unknown_type(monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "k")
    with httpx.Client() as c, pytest.raises(AdapterError, match="unknown type"):
        fetch({"platform": "pexels", "type": "weird"}, c)


def test_fetch_raises_on_http_error(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "k")
    httpx_mock.add_response(status_code=429)
    with httpx.Client() as c, pytest.raises(AdapterError):
        fetch({"platform": "pexels", "type": "search", "query": "x"}, c)
```

```bash
pytest tests/adapters/test_pexels.py -v
```

Expected: FAIL

- [ ] **Step 2: 实现 `scripts/adapters/pexels.py`**

```python
"""Pexels 适配器：仅 search 一种 source。"""
import os
from datetime import datetime, timezone

import httpx

from scripts.adapters import register
from scripts.adapters.base import AdapterError
from scripts.models import NormalizedPhoto, make_id

API = "https://api.pexels.com/v1"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize(item: dict, source_kind: str, posted_at: str) -> NormalizedPhoto:
    title = item.get("alt") or None
    return NormalizedPhoto(
        id=make_id("pexels", str(item["id"])),
        source="pexels",
        source_kind=source_kind,
        original_url=item["url"],
        thumb_url=item["src"]["large"],
        author_name=item["photographer"],
        author_url=item["photographer_url"],
        title=title,
        taken_at=None,
        posted_at=posted_at,
        exif={},
    )


def fetch(
    source: dict,
    client: httpx.Client,
    *,
    now_iso: str | None = None,
) -> list[NormalizedPhoto]:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        raise AdapterError("PEXELS_API_KEY not set")

    if source.get("type") != "search":
        raise AdapterError(f"unknown type for pexels: {source.get('type')}")

    q = source["query"]
    posted_at = now_iso or _now_iso()
    headers = {"Authorization": api_key}
    try:
        r = client.get(
            f"{API}/search",
            params={"query": q, "per_page": 30},
            headers=headers,
        )
        r.raise_for_status()
        items = r.json().get("photos", [])
    except httpx.HTTPError as e:
        raise AdapterError(f"pexels http error: {e}") from e

    kind = f"search:{q}"
    return [_normalize(it, kind, posted_at) for it in items]


register("pexels", fetch)
```

- [ ] **Step 3: 启用 import**

`scripts/adapters/__init__.py`：

```python
from scripts.adapters import flickr, pexels, unsplash  # noqa: E402,F401
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/adapters/ -v
```

Expected: 全部 passed（base 2 + unsplash 6 + flickr 6 + pexels 6 = 20）

- [ ] **Step 5: Commit**

```bash
git add scripts/adapters/pexels.py scripts/adapters/__init__.py tests/adapters/test_pexels.py
git commit -m "feat(adapters): pexels adapter (search)"
```


---

## Task 9: 抓取调度器 fetch.py（端到端）

**Files:**
- Create: `scripts/fetch.py`
- Create: `sources.yaml`（含示例配置 + 说明注释）
- Create: `tests/test_fetch.py`

**Interfaces:**
- Consumes: `ADAPTERS` 注册表、`AdapterError`、`make_client`、`load_photos`、`save_photos`、`merge_and_truncate`、`download_and_convert`、`delete_thumbs`
- Produces:
  - `run(sources_path: Path, data_path: Path, public_dir: Path, *, max_keep: int = 200) -> RunSummary`
  - `RunSummary` dataclass: `successes: list[str]`, `failures: list[tuple[str, str]]`（`(source_label, error_msg)`）, `added: int`, `removed: int`, `skipped_thumbs: int`
  - 命令行入口 `python -m scripts.fetch [--sources sources.yaml] [--data data/photos.json] [--public public]`
  - 写 step summary 到 `$GITHUB_STEP_SUMMARY`（如果环境变量存在）

**关键流程**

```
1. 解析 sources.yaml 得到 sources 列表
2. 创建一个共享 httpx.Client
3. 对每个 source：
   - 构造 source_label = f"{platform}:{type}:{id_or_query}"
   - 调用 ADAPTERS[platform](source, client)
   - 捕获 AdapterError → 记录 failure，继续
   - 收集所有成功 source 的 photos 到 candidates
4. load_photos(data_path) 得到 existing
5. merge_and_truncate(existing, candidates, max_keep) 得到 (merged, added, removed_thumb_paths)
6. 对每个 added：download_and_convert(thumb_url, public_dir / thumb_path)
   - 失败的从 merged 中过滤掉（保持 added 与磁盘一致）
7. delete_thumbs(removed_thumb_paths, public_dir)
8. save_photos(data_path, merged)
9. 写 step summary
10. 返回 RunSummary
```

**测试策略：** 不真的发 HTTP，对 ADAPTERS 注册表 monkeypatch 假适配器。重点验证：
- 多个源都成功时所有照片合并
- 一个源失败时其他源继续，failure 列表正确
- 缩略图下载失败的照片被踢出 merged
- 没有变化时不写文件（通过对比 mtime）

- [ ] **Step 1: 写失败的测试**

```python
import json
from pathlib import Path

import pytest

from scripts.fetch import RunSummary, run
from scripts.models import NormalizedPhoto


def make_norm(pid: str, posted: str = "2026-06-17T12:00:00Z") -> NormalizedPhoto:
    return NormalizedPhoto(
        id=pid,
        source=pid.split(":")[0],
        source_kind="topic:test",
        original_url=f"https://example.com/{pid}",
        thumb_url=f"https://cdn.example.com/{pid}.jpg",
        author_name="A",
        author_url="https://example.com/a",
        title=None,
        taken_at=None,
        posted_at=posted,
        exif={},
    )


@pytest.fixture
def project(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "public" / "thumbs").mkdir(parents=True)
    sources = tmp_path / "sources.yaml"
    sources.write_text(
        """\
sources:
  - platform: alpha
    type: topic
    id: a
  - platform: beta
    type: topic
    id: b
""",
        encoding="utf-8",
    )
    return {
        "sources": sources,
        "data": tmp_path / "data" / "photos.json",
        "public": tmp_path / "public",
    }


def test_run_combines_two_successful_sources(project, monkeypatch):
    from scripts.adapters import ADAPTERS

    monkeypatch.setitem(ADAPTERS, "alpha", lambda src, c: [make_norm("alpha:1")])
    monkeypatch.setitem(ADAPTERS, "beta", lambda src, c: [make_norm("beta:1")])

    # 让 download_and_convert 总是成功（不实际下载）
    monkeypatch.setattr(
        "scripts.fetch.download_and_convert",
        lambda url, dest, **kw: (dest.parent.mkdir(parents=True, exist_ok=True), dest.write_bytes(b"x"), True)[2],
    )

    summary = run(project["sources"], project["data"], project["public"])
    assert isinstance(summary, RunSummary)
    assert sorted(summary.successes) == ["alpha:topic:a", "beta:topic:b"]
    assert summary.failures == []
    assert summary.added == 2

    saved = json.loads(project["data"].read_text())
    assert {p["id"] for p in saved} == {"alpha:1", "beta:1"}


def test_run_records_failure_and_keeps_others(project, monkeypatch):
    from scripts.adapters import ADAPTERS
    from scripts.adapters.base import AdapterError

    def failing(src, c):
        raise AdapterError("rate limited")

    monkeypatch.setitem(ADAPTERS, "alpha", failing)
    monkeypatch.setitem(ADAPTERS, "beta", lambda src, c: [make_norm("beta:1")])
    monkeypatch.setattr(
        "scripts.fetch.download_and_convert",
        lambda url, dest, **kw: (dest.parent.mkdir(parents=True, exist_ok=True), dest.write_bytes(b"x"), True)[2],
    )

    summary = run(project["sources"], project["data"], project["public"])
    assert summary.successes == ["beta:topic:b"]
    assert len(summary.failures) == 1
    label, msg = summary.failures[0]
    assert label == "alpha:topic:a"
    assert "rate limited" in msg


def test_run_drops_photos_whose_thumbs_fail(project, monkeypatch):
    from scripts.adapters import ADAPTERS

    monkeypatch.setitem(
        ADAPTERS,
        "alpha",
        lambda src, c: [make_norm("alpha:ok"), make_norm("alpha:bad")],
    )
    monkeypatch.setitem(ADAPTERS, "beta", lambda src, c: [])

    def fake_dl(url, dest, **kw):
        if "bad" in url:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x")
        return True

    monkeypatch.setattr("scripts.fetch.download_and_convert", fake_dl)

    summary = run(project["sources"], project["data"], project["public"])
    assert summary.added == 1
    assert summary.skipped_thumbs == 1
    saved = json.loads(project["data"].read_text())
    assert {p["id"] for p in saved} == {"alpha:ok"}


def test_run_does_not_write_when_unchanged(project, monkeypatch):
    from scripts.adapters import ADAPTERS

    # 先写入一个等价的现有 photos.json
    project["data"].write_text(
        json.dumps(
            [
                {
                    "id": "alpha:1",
                    "source": "alpha",
                    "source_kind": "topic:test",
                    "original_url": "https://example.com/alpha:1",
                    "thumb_path": "thumbs/alpha-1.webp",
                    "author_name": "A",
                    "author_url": "https://example.com/a",
                    "posted_at": "2026-06-17T12:00:00Z",
                    "exif": {},
                }
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mtime_before = project["data"].stat().st_mtime_ns

    monkeypatch.setitem(ADAPTERS, "alpha", lambda src, c: [make_norm("alpha:1")])
    monkeypatch.setitem(ADAPTERS, "beta", lambda src, c: [])
    monkeypatch.setattr(
        "scripts.fetch.download_and_convert",
        lambda url, dest, **kw: True,
    )

    summary = run(project["sources"], project["data"], project["public"])
    assert summary.added == 0
    # 文件不应该被重写
    assert project["data"].stat().st_mtime_ns == mtime_before
```

```bash
pytest tests/test_fetch.py -v
```

Expected: FAIL（ImportError）

- [ ] **Step 2: 实现 `scripts/fetch.py`**

```python
"""抓取调度器：读 sources.yaml，调用各适配器，合并、淘汰、写盘。"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import yaml

# 触发各适配器注册到 ADAPTERS
from scripts.adapters import ADAPTERS  # noqa: F401
from scripts.adapters.base import AdapterError, make_client
from scripts.models import thumb_path_for
from scripts.store import load_photos, merge_and_truncate, save_photos
from scripts.thumbs import delete_thumbs, download_and_convert

logger = logging.getLogger(__name__)


@dataclass
class RunSummary:
    successes: list[str] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)
    added: int = 0
    removed: int = 0
    skipped_thumbs: int = 0

    def to_markdown(self) -> str:
        lines = ["## Photo fetch summary", ""]
        lines.append(f"- Added: **{self.added}**")
        lines.append(f"- Removed (truncated): **{self.removed}**")
        lines.append(f"- Skipped (thumb failed): **{self.skipped_thumbs}**")
        lines.append(f"- Sources OK: {len(self.successes)}")
        lines.append(f"- Sources FAILED: {len(self.failures)}")
        if self.successes:
            lines.append("\n### Successful sources")
            for s in self.successes:
                lines.append(f"- {s}")
        if self.failures:
            lines.append("\n### Failed sources")
            for label, msg in self.failures:
                lines.append(f"- `{label}` — {msg}")
        return "\n".join(lines) + "\n"


def _label(source: dict) -> str:
    sid = source.get("id") or source.get("query") or source.get("tag", "?")
    return f"{source['platform']}:{source.get('type', '?')}:{sid}"


def _gather(sources: list[dict], client: httpx.Client) -> tuple[list, RunSummary]:
    summary = RunSummary()
    candidates = []
    for src in sources:
        label = _label(src)
        platform = src.get("platform")
        adapter = ADAPTERS.get(platform)
        if adapter is None:
            summary.failures.append((label, f"no adapter for platform {platform!r}"))
            continue
        try:
            photos = adapter(src, client)
        except AdapterError as e:
            summary.failures.append((label, str(e)))
            logger.warning("source %s failed: %s", label, e)
            continue
        except Exception as e:  # noqa: BLE001
            summary.failures.append((label, f"unexpected: {e}"))
            logger.exception("source %s crashed", label)
            continue
        summary.successes.append(label)
        candidates.extend(photos)
    return candidates, summary


def run(
    sources_path: Path,
    data_path: Path,
    public_dir: Path,
    *,
    max_keep: int = 200,
) -> RunSummary:
    config = yaml.safe_load(sources_path.read_text(encoding="utf-8")) or {}
    sources = config.get("sources", [])

    with make_client() as client:
        candidates, summary = _gather(sources, client)

        existing = load_photos(data_path)
        merged, added, removed_thumbs = merge_and_truncate(existing, candidates, max_keep=max_keep)
        summary.removed = len(removed_thumbs)

        # 下载新照片的缩略图；失败的从 merged 移除，保持 photos.json 与磁盘一致
        successful_added: list = []
        for np in added:
            rel = thumb_path_for(np.id)
            dest = public_dir / rel
            ok = download_and_convert(np.thumb_url, dest, client=client)
            if ok:
                successful_added.append(np)
            else:
                summary.skipped_thumbs += 1

        # 把下载失败的 added 从 merged 中剔除
        ok_ids = {np.id for np in successful_added}
        bad_ids = {np.id for np in added} - ok_ids
        if bad_ids:
            merged = [p for p in merged if p["id"] not in bad_ids]

        delete_thumbs(removed_thumbs, public_dir)

        summary.added = len(successful_added)

        # 比较是否变化：对 existing 做 id+thumb_path 集合，对 merged 也做集合
        prev_set = {p["id"] for p in existing}
        next_set = {p["id"] for p in merged}
        if prev_set != next_set or summary.added or summary.removed:
            save_photos(data_path, merged)

    _write_step_summary(summary)
    return summary


def _write_step_summary(summary: RunSummary) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(summary.to_markdown())
    except OSError as e:
        logger.warning("failed to write step summary: %s", e)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Fetch portrait photos from configured sources.")
    parser.add_argument("--sources", default="sources.yaml")
    parser.add_argument("--data", default="data/photos.json")
    parser.add_argument("--public", default="public")
    parser.add_argument("--max-keep", type=int, default=200)
    args = parser.parse_args(argv)

    summary = run(
        Path(args.sources),
        Path(args.data),
        Path(args.public),
        max_keep=args.max_keep,
    )
    print(json.dumps({"successes": summary.successes, "failures": summary.failures, "added": summary.added}, indent=2))
    # 即使有源失败也返回 0：已记录到 step summary
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: 创建 `sources.yaml`（示例 + 说明）**

```yaml
# 数据源配置。每条记录描述一个抓取源。
# 实现完成后请按需调整：替换 collection / group id 为你想追的实际清单。
#
# 支持的平台 / 类型：
#   unsplash:  type=topic   id=<topic-slug>           e.g. people
#              type=collection id=<collection-id>     e.g. 1114848
#              type=search  query=<keywords>          e.g. portrait
#   flickr:    type=group   id=<group-id|alias>       e.g. portraitart
#              type=tag     tag=<tag>  sort=interestingness
#   pexels:    type=search  query=<keywords>

sources:
  - platform: unsplash
    type: topic
    id: people

  - platform: flickr
    type: group
    id: portraitart

  - platform: flickr
    type: tag
    tag: portrait
    sort: interestingness

  - platform: pexels
    type: search
    query: portrait
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_fetch.py -v
```

Expected: 4 passed

- [ ] **Step 5: 全后端测试一轮**

```bash
pytest -v
```

Expected: 全部 passed（约 30 个测试）

- [ ] **Step 6: Commit**

```bash
git add scripts/fetch.py sources.yaml tests/test_fetch.py
git commit -m "feat(fetch): orchestrator with run summary and skip-on-error"
```

---

## Task 10: Astro 项目初始化 + 全局样式

**Files:**
- Create: `package.json`
- Create: `astro.config.mjs`
- Create: `tsconfig.json`
- Create: `src/pages/index.astro`（占位）
- Create: `src/styles/global.css`
- Modify: `.gitignore`（已含 node_modules / dist / .astro）

**Interfaces:**
- Consumes: 无
- Produces: 可运行 `npm run dev` 看到深色背景 + 站名；`npm run build` 输出 `dist/` 静态资源

**关于 `base`：** 部署到 `https://<user>.github.io/<repo>/` 时，Astro 必须配置 `base: '/<repo>/'`，否则资源 404。仓库名占位为 `portraits`，**实施时若仓库名不同，必须改这里**。

- [ ] **Step 1: 创建 `package.json`**

```json
{
  "name": "photo-project",
  "type": "module",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "test": "vitest run"
  },
  "dependencies": {
    "astro": "^4.16.7"
  },
  "devDependencies": {
    "@astrojs/check": "^0.9.4",
    "typescript": "^5.6.3",
    "vitest": "^2.1.5",
    "@vitest/ui": "^2.1.5",
    "happy-dom": "^15.10.2"
  }
}
```

- [ ] **Step 2: 创建 `astro.config.mjs`**

```js
import { defineConfig } from "astro/config";

// 仓库名占位。如最终仓库名不是 portraits，请同步修改。
const REPO = "portraits";

export default defineConfig({
  site: `https://example.github.io/${REPO}/`,
  base: `/${REPO}/`,
  build: {
    assets: "_assets",
  },
  vite: {
    test: {
      environment: "happy-dom",
      globals: true,
    },
  },
});
```

- [ ] **Step 3: 创建 `tsconfig.json`**

```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "~/*": ["src/*"]
    }
  },
  "include": [".astro/types.d.ts", "**/*"],
  "exclude": ["dist"]
}
```

- [ ] **Step 4: 创建 `src/styles/global.css`**

```css
:root {
  --bg: #0a0a0a;
  --text: #d4d4d4;
  --heading: #f0f0f0;
  --muted: #888;
  --muted-strong: #555;
  --accent: #d4d4d4;
  --shadow: 0 20px 60px rgba(0, 0, 0, 0.6);

  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;

  --label: 10px;
  --tracking-wide: 0.3em;
}

*, *::before, *::after { box-sizing: border-box; }

html, body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-weight: 300;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

a { color: inherit; text-decoration: none; }
a:hover { color: var(--heading); }

img { display: block; max-width: 100%; height: auto; }

.label {
  font-size: var(--label);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--muted-strong);
}

.site-header {
  padding: 32px 48px 0;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid #1f1f1f;
  padding-bottom: 24px;
  margin-bottom: 48px;
}

.site-header .logo {
  font-size: 12px;
  letter-spacing: 0.4em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 300;
}

.site-header .meta {
  font-size: var(--label);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted-strong);
}

main { padding: 0 24px 96px; }

@media (min-width: 768px) { main { padding: 0 48px 96px; } }
```

- [ ] **Step 5: 创建 `src/pages/index.astro`（占位）**

```astro
---
import "~/styles/global.css";
const total = 0;
---
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
    <title>Portraits · 2026</title>
  </head>
  <body>
    <header class="site-header">
      <div class="logo">PORTRAITS · 2026</div>
      <div class="meta">{total} PHOTOS</div>
    </header>
    <main>
      <p class="label">Photo grid coming in Task 12.</p>
    </main>
  </body>
</html>
```

- [ ] **Step 6: 安装依赖并验证 build 通过**

```bash
npm install
npm run build
```

Expected: build 成功，输出 `dist/` 目录（含 `index.html` 和 `_assets/`）

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json astro.config.mjs tsconfig.json src/
git commit -m "chore(web): scaffold astro + dark room global styles"
```

---

## Task 11: 数据加载 helper + PhotoCard 组件

**Files:**
- Create: `src/lib/photos.ts`
- Create: `src/lib/format.ts`
- Create: `src/components/PhotoCard.astro`
- Create: `tests/web/photos.test.ts`
- Create: `tests/web/format.test.ts`

**Interfaces:**
- Consumes: `data/photos.json`（项目根的相对路径）
- Produces:
  - `Photo` TypeScript 接口（与 §4 spec 字段一致）
  - `loadPhotos(): Promise<Photo[]>` —— 在 Astro 构建时（Node 环境）读取 JSON，按 `posted_at` 倒序返回；文件缺失返回 `[]`
  - `formatDate(iso: string): string` —— 输出 `JUN 17, 2026` 风格
  - `formatPlatform(p: Photo): string` —— 输出 `FLICKR · GROUP: PORTRAITART` 风格
  - `formatExif(exif: Photo["exif"]): string[]` —— 返回非空字段的展示字符串数组（如 `["Leica Q2", "f/1.7", "1/500", "ISO 400"]`），缺失字段直接不进数组
  - `<PhotoCard photo={photo} index={i} />` —— 渲染瀑布流中一张图卡，含懒加载 `<img>`、hover 时浮现的小字 `<作者名> · <平台> · <日期>`

- [ ] **Step 1: 写失败的测试**

`tests/web/photos.test.ts`：

```ts
import { describe, expect, it } from "vitest";
import { loadPhotos } from "../../src/lib/photos";
import { promises as fs } from "node:fs";
import path from "node:path";

describe("loadPhotos", () => {
  it("returns empty when data file missing", async () => {
    const tmp = await fs.mkdtemp("/tmp/ph-");
    const photos = await loadPhotos(path.join(tmp, "missing.json"));
    expect(photos).toEqual([]);
  });

  it("sorts by posted_at desc", async () => {
    const tmp = await fs.mkdtemp("/tmp/ph-");
    const file = path.join(tmp, "p.json");
    await fs.writeFile(
      file,
      JSON.stringify([
        { id: "a:1", posted_at: "2026-01-01T00:00:00Z" },
        { id: "a:2", posted_at: "2026-03-01T00:00:00Z" },
        { id: "a:3", posted_at: "2026-02-01T00:00:00Z" },
      ])
    );
    const photos = await loadPhotos(file);
    expect(photos.map((p) => p.id)).toEqual(["a:2", "a:3", "a:1"]);
  });
});
```

`tests/web/format.test.ts`：

```ts
import { describe, expect, it } from "vitest";
import { formatDate, formatExif, formatPlatform } from "../../src/lib/format";

describe("formatDate", () => {
  it("formats ISO into uppercase short month + day + year", () => {
    expect(formatDate("2026-06-17T09:12:00Z")).toBe("JUN 17, 2026");
  });
});

describe("formatPlatform", () => {
  it("formats source + source_kind", () => {
    expect(
      formatPlatform({ source: "flickr", source_kind: "group:portraitart" } as any)
    ).toBe("FLICKR · GROUP: PORTRAITART");
  });
});

describe("formatExif", () => {
  it("returns only present fields", () => {
    expect(
      formatExif({ camera: "Leica Q2", aperture: "f/1.7", iso: 400 } as any)
    ).toEqual(["Leica Q2", "f/1.7", "ISO 400"]);
  });

  it("returns empty for empty exif", () => {
    expect(formatExif({})).toEqual([]);
  });
});
```

```bash
npx vitest run
```

Expected: FAIL（找不到模块）

- [ ] **Step 2: 实现 `src/lib/photos.ts`**

```ts
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export interface Photo {
  id: string;
  source: string;
  source_kind: string;
  original_url: string;
  thumb_path: string;
  author_name: string;
  author_url: string;
  title?: string;
  taken_at?: string;
  posted_at: string;
  exif: Record<string, string | number | null>;
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_DATA_PATH = path.resolve(__dirname, "..", "..", "data", "photos.json");

export async function loadPhotos(file: string = DEFAULT_DATA_PATH): Promise<Photo[]> {
  let raw: string;
  try {
    raw = await fs.readFile(file, "utf-8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw e;
  }
  if (!raw.trim()) return [];
  const photos = JSON.parse(raw) as Photo[];
  return photos.sort((a, b) => (a.posted_at < b.posted_at ? 1 : -1));
}
```

- [ ] **Step 3: 实现 `src/lib/format.ts`**

```ts
import type { Photo } from "./photos";

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const m = MONTHS[d.getUTCMonth()];
  const day = d.getUTCDate();
  const y = d.getUTCFullYear();
  return `${m} ${day}, ${y}`;
}

export function formatPlatform(photo: Pick<Photo, "source" | "source_kind">): string {
  const kind = photo.source_kind.replace(":", ": ");
  return `${photo.source.toUpperCase()} · ${kind.toUpperCase()}`;
}

const EXIF_ORDER: { key: string; render: (v: string | number) => string }[] = [
  { key: "camera", render: (v) => String(v) },
  { key: "lens", render: (v) => String(v) },
  { key: "focal_length", render: (v) => String(v) },
  { key: "aperture", render: (v) => String(v) },
  { key: "shutter", render: (v) => String(v) },
  { key: "iso", render: (v) => `ISO ${v}` },
];

export function formatExif(exif: Photo["exif"]): string[] {
  const out: string[] = [];
  for (const { key, render } of EXIF_ORDER) {
    const v = exif?.[key];
    if (v !== undefined && v !== null && v !== "") {
      out.push(render(v as string | number));
    }
  }
  return out;
}
```

- [ ] **Step 4: 实现 `src/components/PhotoCard.astro`**

```astro
---
import type { Photo } from "~/lib/photos";
import { formatDate } from "~/lib/format";

interface Props { photo: Photo; index: number; }
const { photo, index } = Astro.props;
const eager = index < 6;
---
<figure class="card" data-id={photo.id}>
  <button class="card-trigger" type="button" aria-label={`Open ${photo.title ?? "photo"}`}>
    <img
      src={`${import.meta.env.BASE_URL}${photo.thumb_path}`}
      alt={photo.title ?? `${photo.author_name} portrait`}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
    />
    <figcaption class="overlay">
      <span class="who">{photo.author_name}</span>
      <span class="src">{photo.source.toUpperCase()} · {formatDate(photo.posted_at)}</span>
    </figcaption>
  </button>
</figure>
<style>
  .card {
    margin: 0 0 8px;
    break-inside: avoid;
    position: relative;
    overflow: hidden;
    background: #1a1a1a;
    box-shadow: var(--shadow);
  }
  .card-trigger {
    all: unset;
    display: block;
    cursor: pointer;
    width: 100%;
  }
  .card img { width: 100%; display: block; }
  .overlay {
    position: absolute;
    inset: auto 0 0 0;
    padding: 12px 14px;
    background: linear-gradient(to top, rgba(0,0,0,0.75), transparent);
    color: var(--heading);
    font-size: 11px;
    line-height: 1.5;
    opacity: 0;
    transition: opacity 0.18s ease;
    display: flex;
    flex-direction: column;
  }
  .card:hover .overlay,
  .card-trigger:focus-visible .overlay { opacity: 1; }
  .who { font-weight: 400; }
  .src {
    color: var(--muted);
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 2px;
  }
</style>
```

- [ ] **Step 5: 运行测试**

```bash
npx vitest run
```

Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/lib/ src/components/PhotoCard.astro tests/web/
git commit -m "feat(web): photo data loader + formatters + PhotoCard"
```

---

## Task 12: PhotoGrid 瀑布流 + 首页

**Files:**
- Create: `src/components/PhotoGrid.astro`
- Modify: `src/pages/index.astro`（用真实数据 + 瀑布流）
- Create: `data/photos.json`（手工写入 3-5 条样本数据，供本地 dev 看到效果）

**Interfaces:**
- Consumes: `loadPhotos()`, `<PhotoCard>`
- Produces:
  - `<PhotoGrid photos={...} />` —— 用 CSS columns 实现瀑布流
  - 桌面 3 列、平板 2 列、手机 1 列
  - 首页正常渲染数据并显示 `${total} PHOTOS`

- [ ] **Step 1: 实现 `src/components/PhotoGrid.astro`**

```astro
---
import PhotoCard from "./PhotoCard.astro";
import type { Photo } from "~/lib/photos";
interface Props { photos: Photo[]; }
const { photos } = Astro.props;
---
<section class="grid">
  {photos.map((p, i) => <PhotoCard photo={p} index={i} />)}
</section>
<style>
  .grid {
    column-count: 1;
    column-gap: 8px;
  }
  @media (min-width: 640px) { .grid { column-count: 2; } }
  @media (min-width: 1024px) { .grid { column-count: 3; } }
</style>
```

- [ ] **Step 2: 改写 `src/pages/index.astro`**

```astro
---
import "~/styles/global.css";
import PhotoGrid from "~/components/PhotoGrid.astro";
import { loadPhotos } from "~/lib/photos";

const photos = await loadPhotos();
const total = photos.length;
---
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap" rel="stylesheet" />
    <title>Portraits · 2026</title>
    <meta name="description" content="A daily-updated portrait photography gallery." />
  </head>
  <body>
    <header class="site-header">
      <div class="logo">PORTRAITS · 2026</div>
      <div class="meta">{total} PHOTOS</div>
    </header>
    <main>
      {total === 0 ? (
        <p class="label" style="text-align:center;margin-top:96px">
          No photos yet. The first fetch will run via GitHub Actions.
        </p>
      ) : (
        <PhotoGrid photos={photos} />
      )}
    </main>
  </body>
</html>
```

- [ ] **Step 3: 创建本地样本 `data/photos.json`（仅用于本地开发，生产由 fetch 脚本写入）**

```json
[
  {
    "id": "unsplash:demo-1",
    "source": "unsplash",
    "source_kind": "topic:people",
    "original_url": "https://unsplash.com/photos/demo-1",
    "thumb_path": "thumbs/unsplash-demo-1.webp",
    "author_name": "Sample Photographer",
    "author_url": "https://unsplash.com/@sample",
    "posted_at": "2026-06-17T09:00:00Z",
    "exif": {}
  }
]
```

并在 `public/thumbs/` 放一张测试图（任何 webp，命名 `unsplash-demo-1.webp`）：

```bash
mkdir -p public/thumbs
# 创建一张占位 webp（用 Pillow 写一张纯色，存到 public/thumbs/unsplash-demo-1.webp）
python3 -c "from PIL import Image; Image.new('RGB',(800,1000),(80,60,60)).save('public/thumbs/unsplash-demo-1.webp','WEBP',quality=80)"
```

- [ ] **Step 4: 验证 build**

```bash
npm run build
```

Expected: 构建成功，`dist/index.html` 存在并包含图片标签

- [ ] **Step 5: Commit**

```bash
git add src/components/PhotoGrid.astro src/pages/index.astro data/photos.json public/thumbs/
git commit -m "feat(web): photo grid + index page with sample data"
```

---

## Task 13: Lightbox 组件 + 客户端交互

**Files:**
- Create: `src/components/Lightbox.astro`
- Create: `src/scripts/lightbox.ts`
- Modify: `src/pages/index.astro`（嵌入 `<Lightbox>` 与初始化脚本）
- Create: `tests/web/lightbox.test.ts`

**Interfaces:**
- Consumes: `Photo`, `formatDate`, `formatPlatform`, `formatExif`
- Produces:
  - `<Lightbox photos={photos} />` 渲染一个隐藏的 `<dialog>` 骨架
  - `lightbox.ts` 暴露默认导出 `init(photos: Photo[])`，绑定：
    - 点击 `.card-trigger` 打开 lightbox 显示对应图
    - 键盘 `←` / `→` 切换、`ESC` 关闭
    - 点击 backdrop 关闭
    - 触屏左右滑切换、下滑关闭（基础 touch 处理：`touchstart` + `touchend`，距离阈值 60px）
    - URL hash 同步：打开时 `location.hash = #photo=<id>`，关闭时清空；初始加载若 hash 存在则自动打开
  - 信息面板内容：标题、作者（链接到 `author_url`）、`formatDate`、`formatPlatform`、EXIF 按行、`原平台查看 →`

- [ ] **Step 1: 写测试 `tests/web/lightbox.test.ts`**

```ts
import { describe, expect, it, beforeEach } from "vitest";
import init from "../../src/scripts/lightbox";
import type { Photo } from "../../src/lib/photos";

const PHOTOS: Photo[] = [
  {
    id: "a:1",
    source: "unsplash",
    source_kind: "topic:people",
    original_url: "https://example.com/a1",
    thumb_path: "thumbs/a-1.webp",
    author_name: "Jane",
    author_url: "https://example.com/jane",
    posted_at: "2026-06-17T09:00:00Z",
    exif: { camera: "Leica Q2" },
    title: "First",
  },
  {
    id: "a:2",
    source: "flickr",
    source_kind: "group:portraitart",
    original_url: "https://example.com/a2",
    thumb_path: "thumbs/a-2.webp",
    author_name: "John",
    author_url: "https://example.com/john",
    posted_at: "2026-06-16T09:00:00Z",
    exif: {},
  },
];

function setupDom() {
  document.body.innerHTML = `
    <button class="card-trigger" data-id="a:1"><img src="/thumbs/a-1.webp" /></button>
    <button class="card-trigger" data-id="a:2"><img src="/thumbs/a-2.webp" /></button>
    <dialog id="lightbox">
      <div class="lb-image"><img id="lb-img" /></div>
      <aside class="lb-info">
        <div id="lb-title"></div>
        <a id="lb-author" href="#"></a>
        <div id="lb-date"></div>
        <div id="lb-platform"></div>
        <ul id="lb-exif"></ul>
        <a id="lb-original" href="#">original →</a>
      </aside>
      <button id="lb-close">×</button>
    </dialog>
  `;
  // happy-dom 需要 polyfill HTMLDialogElement.prototype.showModal/close
  const dialog = document.getElementById("lightbox") as any;
  if (typeof dialog.showModal !== "function") {
    dialog.showModal = function () { this.setAttribute("open", ""); };
    dialog.close = function () { this.removeAttribute("open"); };
  }
}

describe("lightbox", () => {
  beforeEach(() => {
    location.hash = "";
    setupDom();
  });

  it("opens with the clicked photo's data", () => {
    init(PHOTOS);
    const card = document.querySelector('[data-id="a:1"]') as HTMLElement;
    card.click();
    const dialog = document.getElementById("lightbox") as HTMLDialogElement;
    expect(dialog.hasAttribute("open")).toBe(true);
    expect((document.getElementById("lb-title") as HTMLElement).textContent).toBe("First");
    expect((document.getElementById("lb-author") as HTMLAnchorElement).href).toContain("example.com/jane");
    expect((document.getElementById("lb-original") as HTMLAnchorElement).href).toContain("example.com/a1");
    expect(location.hash).toBe("#photo=a:1");
  });

  it("arrow right advances to next photo", () => {
    init(PHOTOS);
    (document.querySelector('[data-id="a:1"]') as HTMLElement).click();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
    expect((document.getElementById("lb-title") as HTMLElement).textContent).toBe("");
    expect(location.hash).toBe("#photo=a:2");
  });

  it("escape closes and clears hash", () => {
    init(PHOTOS);
    (document.querySelector('[data-id="a:1"]') as HTMLElement).click();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    const dialog = document.getElementById("lightbox") as HTMLDialogElement;
    expect(dialog.hasAttribute("open")).toBe(false);
    expect(location.hash).toBe("");
  });

  it("opens from initial hash on init", () => {
    location.hash = "#photo=a:2";
    init(PHOTOS);
    const dialog = document.getElementById("lightbox") as HTMLDialogElement;
    expect(dialog.hasAttribute("open")).toBe(true);
    expect((document.getElementById("lb-platform") as HTMLElement).textContent).toBe(
      "FLICKR · GROUP: PORTRAITART"
    );
  });
});
```

```bash
npx vitest run tests/web/lightbox.test.ts
```

Expected: FAIL（找不到模块）

- [ ] **Step 2: 实现 `src/scripts/lightbox.ts`**

```ts
import type { Photo } from "~/lib/photos";
import { formatDate, formatExif, formatPlatform } from "~/lib/format";

const SWIPE_THRESHOLD = 60;

export default function init(photos: Photo[]): void {
  const dialog = document.getElementById("lightbox") as HTMLDialogElement | null;
  if (!dialog) return;

  const img = document.getElementById("lb-img") as HTMLImageElement;
  const title = document.getElementById("lb-title")!;
  const author = document.getElementById("lb-author") as HTMLAnchorElement;
  const date = document.getElementById("lb-date")!;
  const platform = document.getElementById("lb-platform")!;
  const exifEl = document.getElementById("lb-exif")!;
  const original = document.getElementById("lb-original") as HTMLAnchorElement;
  const closeBtn = document.getElementById("lb-close")!;

  const byId = new Map<string, number>();
  photos.forEach((p, i) => byId.set(p.id, i));

  let current = -1;

  const base = (typeof document !== "undefined" && (document as any).baseURI) || "/";

  function render(index: number): void {
    const p = photos[index];
    if (!p) return;
    current = index;
    img.src = `${new URL(p.thumb_path, base).pathname}`;
    img.alt = p.title ?? p.author_name;
    title.textContent = p.title ?? "";
    author.textContent = p.author_name;
    author.href = p.author_url;
    date.textContent = formatDate(p.posted_at);
    platform.textContent = formatPlatform(p);
    exifEl.innerHTML = "";
    for (const line of formatExif(p.exif)) {
      const li = document.createElement("li");
      li.textContent = line;
      exifEl.appendChild(li);
    }
    original.href = p.original_url;
    location.hash = `#photo=${p.id}`;
  }

  function open(id: string): void {
    const i = byId.get(id);
    if (i === undefined) return;
    render(i);
    if (!dialog.hasAttribute("open")) dialog.showModal();
  }

  function close(): void {
    if (dialog.hasAttribute("open")) dialog.close();
    if (location.hash.startsWith("#photo=")) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    current = -1;
  }

  function step(delta: number): void {
    if (current < 0) return;
    const next = (current + delta + photos.length) % photos.length;
    render(next);
  }

  // 卡片点击
  document.querySelectorAll<HTMLElement>(".card-trigger[data-id]").forEach((el) => {
    el.addEventListener("click", () => {
      const id = el.getAttribute("data-id");
      if (id) open(id);
    });
  });

  // 键盘
  document.addEventListener("keydown", (e) => {
    if (!dialog.hasAttribute("open")) return;
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight") step(1);
    else if (e.key === "ArrowLeft") step(-1);
  });

  // 关闭按钮 + backdrop
  closeBtn.addEventListener("click", close);
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) close();
  });
  dialog.addEventListener("close", () => {
    if (location.hash.startsWith("#photo=")) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    current = -1;
  });

  // 触屏滑动
  let touchStart: { x: number; y: number } | null = null;
  dialog.addEventListener("touchstart", (e) => {
    const t = e.changedTouches[0];
    touchStart = { x: t.clientX, y: t.clientY };
  });
  dialog.addEventListener("touchend", (e) => {
    if (!touchStart) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - touchStart.x;
    const dy = t.clientY - touchStart.y;
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > SWIPE_THRESHOLD) {
      step(dx < 0 ? 1 : -1);
    } else if (dy > SWIPE_THRESHOLD) {
      close();
    }
    touchStart = null;
  });

  // 初始 hash
  const m = /^#photo=(.+)$/.exec(location.hash);
  if (m) open(decodeURIComponent(m[1]));
}
```

- [ ] **Step 3: 实现 `src/components/Lightbox.astro`**

```astro
---
import type { Photo } from "~/lib/photos";
interface Props { photos: Photo[]; }
const { photos } = Astro.props;
---
<dialog id="lightbox" class="lightbox" aria-label="Photo viewer">
  <div class="lb-image">
    <img id="lb-img" alt="" />
  </div>
  <aside class="lb-info">
    <div id="lb-title" class="lb-title"></div>
    <a id="lb-author" class="lb-author" href="#" rel="noopener noreferrer" target="_blank"></a>
    <div class="lb-meta">
      <span id="lb-date" class="label"></span>
      <span id="lb-platform" class="label"></span>
    </div>
    <ul id="lb-exif" class="lb-exif"></ul>
    <a id="lb-original" class="lb-original" href="#" rel="noopener noreferrer" target="_blank">VIEW ON ORIGINAL →</a>
  </aside>
  <button id="lb-close" class="lb-close" aria-label="Close">×</button>
</dialog>

<script type="application/json" id="lb-data" set:html={JSON.stringify(photos)}></script>

<script>
  import init from "~/scripts/lightbox";
  const data = JSON.parse(document.getElementById("lb-data")!.textContent || "[]");
  init(data);
</script>

<style>
  .lightbox {
    border: 0;
    padding: 0;
    margin: 0;
    width: 100vw;
    height: 100vh;
    max-width: 100vw;
    max-height: 100vh;
    background: rgba(0,0,0,0.97);
    color: var(--text);
    display: none;
  }
  .lightbox[open] { display: grid; }
  @media (min-width: 900px) {
    .lightbox[open] { grid-template-columns: 70% 30%; }
  }
  @media (max-width: 899px) {
    .lightbox[open] { grid-template-rows: 60% 40%; }
  }
  .lb-image {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
    background: #000;
  }
  .lb-image img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    box-shadow: var(--shadow);
  }
  .lb-info {
    padding: 48px 40px;
    border-left: 1px solid #1f1f1f;
    overflow-y: auto;
  }
  .lb-title {
    color: var(--heading);
    font-size: 22px;
    font-weight: 300;
    line-height: 1.3;
    margin-bottom: 8px;
    min-height: 22px;
  }
  .lb-author {
    display: block;
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 24px;
  }
  .lb-author:hover { color: var(--heading); }
  .lb-meta {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    border-top: 1px solid #1f1f1f;
    padding-top: 16px;
    margin-bottom: 16px;
  }
  .lb-exif {
    list-style: none;
    padding: 0;
    margin: 0 0 32px;
    color: var(--muted);
    font-size: 11px;
    line-height: 2;
    letter-spacing: 0.05em;
  }
  .lb-exif li { font-variant-numeric: tabular-nums; }
  .lb-original {
    font-size: var(--label);
    letter-spacing: var(--tracking-wide);
    text-transform: uppercase;
    color: var(--muted);
    border-top: 1px solid #1f1f1f;
    padding-top: 16px;
    display: inline-block;
  }
  .lb-original:hover { color: var(--heading); }
  .lb-close {
    position: absolute;
    top: 16px;
    right: 24px;
    background: transparent;
    border: 0;
    color: var(--muted);
    font-size: 32px;
    line-height: 1;
    cursor: pointer;
  }
  .lb-close:hover { color: var(--heading); }
</style>
```

- [ ] **Step 4: 修改 `src/pages/index.astro` 嵌入 Lightbox**

把 `</main>` 之前补上：

```astro
<Lightbox photos={photos} />
```

并在 frontmatter 加 `import Lightbox from "~/components/Lightbox.astro";`。

- [ ] **Step 5: 运行测试**

```bash
npx vitest run tests/web/
```

Expected: 9 passed（含 Task 11 的 5 个 + Task 13 的 4 个）

- [ ] **Step 6: 验证 build 仍能通过**

```bash
npm run build
```

Expected: 构建成功

- [ ] **Step 7: Commit**

```bash
git add src/components/Lightbox.astro src/scripts/lightbox.ts src/pages/index.astro tests/web/lightbox.test.ts
git commit -m "feat(web): lightbox with keyboard, touch, and hash sync"
```

---

## Task 14: update-photos workflow（定时 + 手动 + 提交）

**Files:**
- Create: `.github/workflows/update-photos.yml`

**Interfaces:**
- Consumes: `scripts/fetch.py`, `requirements.txt`, `sources.yaml`
- Produces: 每天 UTC 02:00 自动运行，把 `data/photos.json` 与 `public/thumbs/` 的变化提交到 main 分支

- [ ] **Step 1: 创建 workflow 文件**

```yaml
# .github/workflows/update-photos.yml
name: Update photos

on:
  schedule:
    - cron: "0 2 * * *"   # daily at 02:00 UTC
  workflow_dispatch:

permissions:
  contents: write

jobs:
  fetch:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - run: pip install -r requirements.txt

      - name: Run fetch
        env:
          UNSPLASH_ACCESS_KEY: ${{ secrets.UNSPLASH_ACCESS_KEY }}
          FLICKR_API_KEY: ${{ secrets.FLICKR_API_KEY }}
          PEXELS_API_KEY: ${{ secrets.PEXELS_API_KEY }}
        run: python -m scripts.fetch

      - name: Commit changes if any
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/photos.json public/thumbs/
          if git diff --staged --quiet; then
            echo "No changes."
            exit 0
          fi
          # 计算 +N -M 概要
          ADDED=$(git diff --staged --numstat -- data/photos.json | awk '{print $1}')
          REMOVED=$(git diff --staged --numstat -- data/photos.json | awk '{print $2}')
          DATE=$(date -u +%Y-%m-%d)
          git commit -m "chore(photos): daily update ${DATE} (json +${ADDED:-0} -${REMOVED:-0} lines)"
          git push
```

- [ ] **Step 2: 本地语法检查（可选，actionlint 若未装可跳过）**

```bash
# 若有 actionlint：
actionlint .github/workflows/update-photos.yml
# 没有则人工检查 YAML 缩进
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update-photos.yml
git commit -m "ci: add daily update-photos workflow"
```

**注意：** 部署后需要在仓库 Settings → Secrets and variables → Actions 中添加：

- `UNSPLASH_ACCESS_KEY`
- `FLICKR_API_KEY`
- `PEXELS_API_KEY`

并确认仓库 Settings → Actions → General → Workflow permissions 设为 **Read and write**。

---

## Task 15: deploy workflow（构建 + 部署 Pages）

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: `package.json`, `astro.config.mjs`, `data/photos.json`, `public/thumbs/`
- Produces: 每次 main 分支变化（包括 update-photos 的 commit）触发，构建 Astro 并部署到 GitHub Pages

- [ ] **Step 1: 创建 workflow 文件**

```yaml
# .github/workflows/deploy.yml
name: Deploy site

on:
  push:
    branches: [main]
    paths:
      - "src/**"
      - "data/**"
      - "public/**"
      - "astro.config.mjs"
      - "package.json"
      - "package-lock.json"
      - "tsconfig.json"
      - ".github/workflows/deploy.yml"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add Pages deploy workflow"
```

**部署后人工操作：**

1. GitHub 仓库 → Settings → Pages → **Source** 选 **GitHub Actions**
2. 推送代码到 `main`，第一次手动触发 `Update photos` workflow 拉数据，再触发 `Deploy site` workflow（或等数据 commit 后自动连锁触发）
3. 访问 `https://<username>.github.io/portraits/` 看到首页

如果仓库名不是 `portraits`，记得：

- 改 `astro.config.mjs` 的 `REPO` 常量
- 重新 build & deploy

---

## 端到端验证清单（实施完成后人工跑一遍）

- [ ] `pytest -v` 全部通过
- [ ] `npm run build` 成功
- [ ] `npx vitest run` 全部通过
- [ ] 本地 `npm run dev` 看到深色背景 + 至少一张样本图，hover 能看到作者名
- [ ] 点击图片打开 lightbox，看到信息面板
- [ ] 键盘 `←` `→` 能切换、`ESC` 能关闭
- [ ] 浏览器地址栏 hash 同步变化
- [ ] GitHub Secrets 已配置三个 API key
- [ ] 手动触发 `Update photos` workflow，查看 Actions 日志和 step summary
- [ ] 推送 main 后 `Deploy site` workflow 成功
- [ ] 访问 Pages URL 看到真实数据

