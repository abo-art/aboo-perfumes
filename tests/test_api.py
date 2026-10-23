"""
FastAPI HTTP Endpoint Integration Tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["catalog_size"] >= 80


def test_search_perfumes_endpoint():
    response = client.get("/api/perfumes/search?q=lost cherry")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert "Lost Cherry" in data["results"][0]["perfume"]["name"]


def test_sommelier_full_flow_via_api():
    # 1. Start interview
    start_resp = client.post("/api/sommelier/start", json={"perfume_name": "Tom Ford Lost Cherry"})
    assert start_resp.status_code == 200
    start_data = start_resp.json()

    session_id = start_data["session_id"]
    assert len(start_data["questions"]) == 3
    assert start_data["matched_perfume"]["name"] == "Lost Cherry"

    # 2. Get recommendations
    rec_resp = client.post("/api/sommelier/recommend", json={
        "session_id": session_id,
        "answers": [
            {"question_id": 1, "answer": "На вечер и праздники"},
            {"question_id": 2, "answer": "Шлейфовый заметный"},
            {"question_id": 3, "answer": "Без приторности"}
        ]
    })
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()

    assert rec_data["status"] == "success"
    assert len(rec_data["recommendations"]) == 10

    # Strict JSON structure test according to ТЗ (requirement #5 + image_url)
    first_item = rec_data["recommendations"][0]
    assert "rank" in first_item
    assert "brand" in first_item
    assert "name" in first_item
    assert "family" in first_item
    assert "notes" in first_item
    assert "image_url" in first_item
    assert first_item["image_url"].startswith("http")
    assert "reason" in first_item
    assert isinstance(first_item["notes"], list)
    assert first_item["rank"] == 1


def test_direct_recommendation_api():
    response = client.post("/api/sommelier/recommend", json={
        "perfume_name": "Baccarat Rouge 540",
        "answers": [
            {"question_id": 1, "answer": "Каждый день"},
            {"question_id": 2, "answer": "Умеренный"},
            {"question_id": 3, "answer": "Без тяжелых смол"}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["recommendations"]) == 10
