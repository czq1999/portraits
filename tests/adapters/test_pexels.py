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
