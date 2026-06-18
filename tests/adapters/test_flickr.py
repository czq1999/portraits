import re

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
    "dateupload": "1781712000",  # 2026-06-17 16:00 UTC
    "datetaken": "2026-06-15 14:30:00",
    "url_l": "https://live.staticflickr.com/65535/54321_abc_b.jpg",
}


def test_flickr_registered():
    assert "flickr" in ADAPTERS


def test_fetch_group(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("FLICKR_API_KEY", "k")
    httpx_mock.add_response(
        url=re.compile(r".*\bmethod=flickr\.groups\.pools\.getPhotos\b.*"),
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
    assert p.posted_at == "2026-06-17T16:00:00Z"
    assert p.taken_at == "2026-06-15T14:30:00Z"
    assert p.exif == {}


def test_fetch_tag_uses_search_method(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("FLICKR_API_KEY", "k")
    httpx_mock.add_response(
        url=re.compile(r".*\bmethod=flickr\.photos\.search\b.*\bsort=interestingness-desc\b.*"),
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
        url=re.compile(r".*method=flickr\.groups\.pools\.getPhotos.*"),
        json={"photos": {"photo": [photo]}, "stat": "ok"},
    )
    with httpx.Client() as c:
        photos = fetch({"platform": "flickr", "type": "group", "id": "x"}, c)
    assert photos[0].thumb_url == "https://live.staticflickr.com/65535/54321_abc_b.jpg"


def test_fetch_uses_owner_when_pathalias_empty(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("FLICKR_API_KEY", "k")
    photo = {**SAMPLE_PHOTO, "pathalias": None}
    httpx_mock.add_response(
        url=re.compile(r".*method=flickr\.groups\.pools\.getPhotos.*"),
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
        url=re.compile(r".*method=flickr\.groups\.pools\.getPhotos.*"),
        json={"stat": "fail", "code": 1, "message": "Group not found"},
    )
    with httpx.Client() as c, pytest.raises(AdapterError, match="Group not found"):
        fetch({"platform": "flickr", "type": "group", "id": "ghost"}, c)
