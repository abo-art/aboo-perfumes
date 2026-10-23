"""
Tests for Interview Generation and 3 Clarifying Questions.
"""

import pytest
from app.services.sommelier_service import sommelier_service


@pytest.mark.asyncio
async def test_start_interview_returns_exactly_3_questions():
    res = await sommelier_service.start_interview("Tom Ford Lost Cherry")

    assert res.session_id is not None
    assert res.matched_perfume.brand == "Tom Ford"
    assert res.matched_perfume.name == "Lost Cherry"
    assert len(res.questions) == 3

    # Check question numbers and aspects
    q_ids = [q.id for q in res.questions]
    assert q_ids == [1, 2, 3]

    aspects = [q.aspect for q in res.questions]
    assert "occasion" in aspects
    assert "sillage" in aspects
    assert "notes_antipathies" in aspects

    for q in res.questions:
        assert len(q.question) > 10
        assert len(q.options) >= 2


@pytest.mark.asyncio
async def test_start_interview_with_slang():
    res = await sommelier_service.start_interview("лост черри")
    assert res.matched_perfume.id == "tom-ford-lost-cherry"
    assert len(res.questions) == 3
