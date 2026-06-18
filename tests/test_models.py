from scripts.models import NormalizedPhoto, make_id


def test_make_id_joins_with_colon():
    assert make_id("flickr", "12345") == "flickr:12345"


def test_normalized_photo_to_dict_basic():
    p = NormalizedPhoto(
        id="flickr:12345",
        source="flickr",
        source_kind="group:portraitart",
        original_url="https://www.flickr.com/photos/x/12345",
        thumb_url="https://live.staticflickr.com/.../12345_b.jpg",
        author_name="Jane Doe",
        author_url="https://www.flickr.com/people/jane/",
        title="Marta, II",
        taken_at="2026-06-15T14:30:00Z",
        posted_at="2026-06-17T09:12:00Z",
        exif={"camera": "Leica Q2", "aperture": "f/1.7"},
    )
    d = p.to_dict()
    assert d["id"] == "flickr:12345"
    assert d["source"] == "flickr"
    assert d["source_kind"] == "group:portraitart"
    assert d["thumb_path"] == "thumbs/flickr-12345.webp"
    assert "thumb_url" not in d  # 临时字段不应出现在持久化中
    assert d["exif"]["camera"] == "Leica Q2"


def test_to_dict_omits_optional_none_strings():
    p = NormalizedPhoto(
        id="pexels:99",
        source="pexels",
        source_kind="search:portrait",
        original_url="https://www.pexels.com/photo/99/",
        thumb_url="https://images.pexels.com/photos/99/large.jpg",
        author_name="A",
        author_url="https://www.pexels.com/@a",
        title=None,
        taken_at=None,
        posted_at="2026-06-18T00:00:00Z",
        exif={},
    )
    d = p.to_dict()
    assert "title" not in d
    assert "taken_at" not in d
    assert d["exif"] == {}
