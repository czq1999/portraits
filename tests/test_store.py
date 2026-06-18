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
