"""
Tests for Catalog Service: Fuzzy search, validation, and note extraction.
"""

import pytest
from app.services.catalog_service import catalog_service


def test_catalog_loaded():
    perfumes = catalog_service.get_all()
    assert len(perfumes) >= 80
    assert catalog_service.get_by_id("tom-ford-lost-cherry") is not None


@pytest.mark.parametrize("query,expected_id", [
    ("Tom Ford Lost Cherry", "tom-ford-lost-cherry"),
    ("лост черри", "tom-ford-lost-cherry"),
    ("том форд вишня", "tom-ford-lost-cherry"),
    ("Baccarat Rouge 540", "mfk-baccarat-rouge-540"),
    ("бакара 540", "mfk-baccarat-rouge-540"),
    ("Creed Aventus", "creed-aventus"),
    ("крид авентус", "creed-aventus"),
    ("ганимед", "mab-ganymede"),
    ("буа империал", "essential-parfums-bois-imperial"),
    ("черный фантом", "kilian-black-phantom"),
    ("Angels Share", "kilian-angels-share"),
    ("доля ангелов", "kilian-angels-share"),
])
def test_fuzzy_matching_accuracy(query, expected_id):
    perfume, score = catalog_service.find_best_match(query)
    assert perfume is not None, f"Failed to match query '{query}'"
    assert perfume.id == expected_id, f"Expected {expected_id}, got {perfume.id} (score {score})"
    assert score >= 70.0


def test_verify_perfume_anti_hallucination():
    # Real perfumes must pass verification
    is_valid, perf, score = catalog_service.verify_perfume("Tom Ford", "Lost Cherry")
    assert is_valid is True
    assert perf.name == "Lost Cherry"

    is_valid, perf, score = catalog_service.verify_perfume("Kilian", "Angels' Share")
    assert is_valid is True
    assert perf.brand == "Kilian"

    # Hallucinated / fake perfumes must FAIL verification
    is_valid, perf, score = catalog_service.verify_perfume("FakeBrand123", "Unicorn Mystic Elixir")
    assert is_valid is False

    is_valid, perf, score = catalog_service.verify_perfume("Tom Ford", "NonExistentMoonlightCyber")
    assert is_valid is False
