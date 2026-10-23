"""
Tests for SQLite Database layer and schema compliance.
"""

from app.database import init_db, count_perfumes, get_all_perfumes, get_perfume_by_id


def test_sqlite_database_seeded():
    init_db()
    total = count_perfumes()
    assert total >= 80, f"Expected at least 80 perfumes in database, got {total}"


def test_sqlite_perfume_schema():
    p = get_perfume_by_id("tom-ford-lost-cherry")
    assert p is not None
    assert p["id"] == "tom-ford-lost-cherry"
    assert p["brand"] == "Tom Ford"
    assert p["name"] == "Lost Cherry"
    assert p["family"] == "Восточные гурманские"
    assert isinstance(p["notes"], list) and len(p["notes"]) >= 2
    assert isinstance(p["image_url"], str) and p["image_url"].startswith("http")
    assert isinstance(p["description"], str) and len(p["description"]) > 10


def test_all_perfumes_have_image_url_and_notes():
    perfumes = get_all_perfumes()
    for p in perfumes:
        assert p["id"] != ""
        assert p["brand"] != ""
        assert p["name"] != ""
        assert p["family"] != ""
        assert isinstance(p["notes"], list) and len(p["notes"]) > 0
        assert p["image_url"] != "" and (p["image_url"].startswith("http") or p["image_url"].startswith("/api/perfumes/")), f"Invalid image_url for {p['id']}"
        assert p["description"] != "" or p["character"] != "", f"Missing description for {p['id']}"


def test_all_perfume_images_are_strictly_unique():
    """Hotfix requirement: Every perfume card in DB must have a unique, non-duplicated image_url."""
    perfumes = get_all_perfumes()
    image_urls = [p["image_url"] for p in perfumes]
    assert len(perfumes) == len(set(image_urls)), f"Duplicate image URLs detected in DB: {len(perfumes)} items vs {len(set(image_urls))} unique URLs"
