"""
Tests for Top-10 Recommendations, Anti-Hallucination validation, and Output format.
"""

import pytest
from app.models.interview import UserAnswer
from app.services.sommelier_service import sommelier_service
from app.services.validator import validator
from app.services.catalog_service import catalog_service


@pytest.mark.asyncio
async def test_full_sommelier_flow_top10():
    # Step 1 & 2: Start interview
    init_res = await sommelier_service.start_interview("Tom Ford Lost Cherry")
    session_id = init_res.session_id

    # Step 3: Provide answers to 5 questions
    answers = [
        UserAnswer(question_id=1, answer="Для вечерних выходов, свиданий и ресторанов"),
        UserAnswer(question_id=2, answer="Яркий, обволакивающий шлейф, который притягивает взгляды"),
        UserAnswer(question_id=3, answer="Глубокая бархатная сладость с ликерными и вишневыми нотами"),
        UserAnswer(question_id=4, answer="Без удушающей приторности, хочется алкогольных нот или табака"),
        UserAnswer(question_id=5, answer="Утонченный твист — знакомый профиль с интересной изюминкой")
    ]

    top10_res = await sommelier_service.get_recommendations_for_session(session_id, answers)

    # Strictly check status and count
    assert top10_res.status == "success"
    assert len(top10_res.recommendations) == 10
    assert top10_res.chain_of_thought is not None
    assert len(top10_res.chain_of_thought) > 50

    # Strictly verify ranks 1 to 10
    ranks = [r.rank for r in top10_res.recommendations]
    assert ranks == list(range(1, 11))

    # Verify every recommendation is a real existing perfume in catalog
    all_catalog_ids = {p.id for p in catalog_service.get_all()}
    for item in top10_res.recommendations:
        assert item.brand != ""
        assert item.name != ""
        assert item.family != ""
        assert item.notes is not None and len(item.notes) >= 2
        assert item.image_url != "" and (item.image_url.startswith("http") or item.image_url.startswith("/api/perfumes/"))
        assert len(item.reason) >= 30
        assert item.id in all_catalog_ids, f"Hallucinated item detected: {item.brand} {item.name}"

    # Verify strict uniqueness of image_url for each item in TOP-10 recommendations
    rec_image_urls = [item.image_url for item in top10_res.recommendations]
    assert len(rec_image_urls) == 10
    assert len(set(rec_image_urls)) == 10, f"Duplicate image_url in TOP-10 recommendations: {rec_image_urls}"

    # Hotfix: Verify strict uniqueness of reasons and absence of robotic template phrases
    reasons = [item.reason for item in top10_res.recommendations]
    assert len(reasons) == 10
    assert len(set(reasons)) == 10, f"Duplicate reasons detected: {reasons}"
    for r in reasons:
        assert not r.startswith("Точное ольфакторное попадание в эстетику"), f"Banned template phrase found: {r}"
        assert not r.startswith("Изысканное развитие знакомой темы"), f"Banned template phrase found: {r}"
        assert not r.startswith("Смелая нишевая альтернатива: авторское прочтение"), f"Banned template phrase found: {r}"
        assert len(r) > 40



def test_validator_rejects_hallucinations_and_substitutes():
    original = catalog_service.get_by_id("tom-ford-lost-cherry")

    raw_fake_recommendations = [
        {"rank": 1, "brand": "FakeCo", "name": "Fake Berry Extreme", "family": "Gourmand", "notes": ["Berry"], "reason": "Nice"},
        {"rank": 2, "brand": "Tom Ford", "name": "Lost Cherry", "family": "Gourmand", "notes": ["Cherry"], "reason": "Self match"},
        {"rank": 3, "brand": "Imaginary Brand", "name": "Ghost Scent", "family": "Floral", "notes": ["Rose"], "reason": "Fake"}
    ]

    corrected = validator.validate_and_correct_top10(
        raw_recommendations=raw_fake_recommendations,
        original_perfume=original
    )

    # Must guarantee exactly 10 real perfumes
    assert len(corrected) == 10
    ranks = [c.rank for c in corrected]
    assert ranks == list(range(1, 11))

    # Verify no fake brands in final output
    brands = [c.brand for c in corrected]
    assert "FakeCo" not in brands
    assert "Imaginary Brand" not in brands
