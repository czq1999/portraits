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
