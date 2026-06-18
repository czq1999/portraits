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
