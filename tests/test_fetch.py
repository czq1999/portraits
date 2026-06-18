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
