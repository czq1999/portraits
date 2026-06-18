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
