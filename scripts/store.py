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
    existing_ids = {p["id"] for p in existing}
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
        p["thumb_path"] for p in drop if p.get("thumb_path") and p["id"] in existing_ids
    ]

    # 如果新加入的照片本身就被立刻淘汰（比 max_keep 边界还旧），从 added 移除以免下游白下载
    added = [np for np in added if np.id in kept_ids]

    return keep, added, removed_thumb_paths
