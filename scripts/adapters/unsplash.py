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
