import io
from pathlib import Path

import httpx
import pytest
from PIL import Image
from pytest_httpx import HTTPXMock

from scripts.thumbs import delete_thumbs, download_and_convert


def make_jpeg_bytes(width: int, height: int, color=(120, 80, 80)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_download_writes_webp_and_resizes_long_edge(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://cdn.example.com/big.jpg", content=make_jpeg_bytes(3000, 2000))
    dest = tmp_path / "thumbs" / "x-1.webp"
    with httpx.Client() as c:
        ok = download_and_convert("https://cdn.example.com/big.jpg", dest, client=c)
    assert ok is True
    assert dest.exists()
    with Image.open(dest) as im:
        assert im.format == "WEBP"
        assert max(im.size) == 1200  # long edge resized
        assert im.size[0] == 1200 and im.size[1] == 800  # ratio preserved


def test_download_does_not_upscale_smaller_image(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://cdn.example.com/small.jpg", content=make_jpeg_bytes(800, 600))
    dest = tmp_path / "x-2.webp"
    with httpx.Client() as c:
        download_and_convert("https://cdn.example.com/small.jpg", dest, client=c)
    with Image.open(dest) as im:
        assert im.size == (800, 600)


def test_download_returns_false_on_http_error(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://cdn.example.com/404.jpg", status_code=404)
    dest = tmp_path / "x-3.webp"
    with httpx.Client() as c:
        ok = download_and_convert("https://cdn.example.com/404.jpg", dest, client=c)
    assert ok is False
    assert not dest.exists()


def test_download_returns_false_on_invalid_image_data(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(url="https://cdn.example.com/bad.jpg", content=b"not an image")
    dest = tmp_path / "x-4.webp"
    with httpx.Client() as c:
        ok = download_and_convert("https://cdn.example.com/bad.jpg", dest, client=c)
    assert ok is False


def test_delete_thumbs_removes_files_silently(tmp_path: Path):
    base = tmp_path / "public"
    (base / "thumbs").mkdir(parents=True)
    f1 = base / "thumbs" / "flickr-1.webp"
    f2 = base / "thumbs" / "flickr-2.webp"
    f1.write_bytes(b"x")
    f2.write_bytes(b"y")
    delete_thumbs(["thumbs/flickr-1.webp", "thumbs/flickr-2.webp", "thumbs/missing.webp"], base)
    assert not f1.exists() and not f2.exists()  # 不存在的文件不报错
