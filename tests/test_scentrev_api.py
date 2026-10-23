"""
Tests for ScentRev / Scento API integration.
Validates live connection to api.scentrev.com, search, note pyramids,
authentic bottle photos, and anti-hallucination verification.
"""

import pytest
from app.services.external_api import scentrev_client
from app.services.catalog_service import catalog_service
from app.services.sommelier_service import sommelier_service
from app.services.validator import validator
from app.models.interview import UserAnswer


def test_scentrev_api_is_configured():
    assert scentrev_client.is_configured is True
    assert scentrev_client.api_key.startswith("frag_live_")


@pytest.mark.asyncio
async def test_scentrev_live_search():
    results = await scentrev_client.search_fragrances("Lost Cherry", limit=3)
    assert len(results) > 0

    top = results[0]
    assert top.brand == "Tom Ford"
    assert "Lost Cherry" in top.name
    # Authentic image from Fragrantica CDN
    assert top.image_url.startswith("https://fimgs.net/mdimg/perfume-thumbs/")
    assert len(top.top_notes) > 0
    assert len(top.heart_notes) > 0
    assert len(top.base_notes) > 0
    assert len(top.accords) > 0


@pytest.mark.asyncio
async def test_scentrev_verify_and_resolve_real_vs_fake():
    # Real perfume
    real_match = await scentrev_client.verify_and_resolve("Creed", "Aventus")
    assert real_match is not None
    assert real_match.brand == "Creed"
    assert "Aventus" in real_match.name
    assert real_match.image_url.startswith("http")

    # Hallucinated / fake perfume should be rejected
    fake_match = await scentrev_client.verify_and_resolve("NonExistentCo", "GhostPhantomMirage99")
    assert fake_match is None


@pytest.mark.asyncio
async def test_catalog_async_search_with_scentrev():
    search_results = await catalog_service.async_search("Ganymede", limit=5)
    assert len(search_results) > 0

    first = search_results[0]
    assert "Ganymede" in first.perfume.name
    assert first.match_source == "scentrev_api"
    assert first.perfume.image_url.startswith("http")


@pytest.mark.asyncio
async def test_sommelier_full_flow_with_scentrev_integration():
    # Start interview with ScentRev-backed perfume lookup
    start_res = await sommelier_service.start_interview("Ganymede", category="Унисекс")
    assert start_res.matched_perfume.brand == "Marc-Antoine Barrois"
    assert "Ganymede" in start_res.matched_perfume.name
    assert start_res.matched_perfume.image_url.startswith("http")
    assert len(start_res.questions) == 5

    # Submit answers to all 5 questions and generate TOP-10
    answers = [
        UserAnswer(question_id=1, answer="Для деловых встреч и офиса"),
        UserAnswer(question_id=2, answer="Умеренный шлейф"),
        UserAnswer(question_id=3, answer="Холодная минеральная свежесть"),
        UserAnswer(question_id=4, answer="Без приторности и удушливости"),
        UserAnswer(question_id=5, answer="Смелый концептуальный авангард")
    ]
    rec_res = await sommelier_service.get_recommendations_for_session(start_res.session_id, answers)
    assert rec_res.status == "success"
    assert len(rec_res.recommendations) == 10
    assert rec_res.chain_of_thought is not None

    # Ensure all 10 recommendations are strictly verified and have valid bottle photos
    for item in rec_res.recommendations:
        assert item.verified is True
        assert item.brand != ""
        assert item.name != ""
        assert item.image_url.startswith("http") or item.image_url.startswith("/api/perfumes/")
        assert len(item.notes) >= 2

