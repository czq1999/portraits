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
    return f"{source.get('platform', '?')}:{source.get('type', '?')}:{sid}"


def _gather(sources: list[dict], client: httpx.Client) -> tuple[list, RunSummary]:
    summary = RunSummary()
    candidates = []
    for src in sources:
        platform = src.get("platform")
        adapter = ADAPTERS.get(platform)
        if adapter is None:
            label = _label(src)
            summary.failures.append((label, f"no adapter for platform {platform!r}"))
            continue
        label = _label(src)
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
