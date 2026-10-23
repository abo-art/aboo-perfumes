"""
Tests for Interview Generation and Strictly 5 Clarifying Questions.
"""

import pytest
from app.services.sommelier_service import sommelier_service


@pytest.mark.asyncio
async def test_start_interview_returns_strictly_5_questions():
    res = await sommelier_service.start_interview("Tom Ford Lost Cherry", category="Унисекс")

    assert res.session_id is not None
    assert res.matched_perfume.brand == "Tom Ford"
    assert res.matched_perfume.name == "Lost Cherry"
    assert len(res.questions) == 5

    # Check question numbers 1 through 5
    q_ids = [q.id for q in res.questions]
    assert q_ids == [1, 2, 3, 4, 5]

    # Verify all 5 criteria from ТЗ are covered
    aspects = [q.aspect for q in res.questions]
    assert "lifestyle" in aspects
    assert "sillage" in aspects
    assert "temperature_notes" in aspects
    assert "antipathies" in aspects
    assert "boldness" in aspects

    for q in res.questions:
        assert len(q.question) > 10
        assert len(q.options) >= 2


@pytest.mark.asyncio
async def test_start_interview_with_slang():
    res = await sommelier_service.start_interview("лост черри", category="Женский")
    assert res.matched_perfume.id == "tom-ford-lost-cherry"
    assert res.category == "Женский"
    assert len(res.questions) == 5

