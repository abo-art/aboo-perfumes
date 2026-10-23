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
    # 1. Start interview with category
    start_resp = client.post("/api/sommelier/start", json={
        "perfume_name": "Tom Ford Lost Cherry",
        "category": "Женский"
    })
    assert start_resp.status_code == 200
    start_data = start_resp.json()

    session_id = start_data["session_id"]
    assert start_data["category"] == "Женский"
    assert len(start_data["questions"]) == 5
    assert start_data["matched_perfume"]["name"] == "Lost Cherry"

    # 2. Get recommendations with strictly 5 answers
    rec_resp = client.post("/api/sommelier/recommend", json={
        "session_id": session_id,
        "answers": [
            {"question_id": 1, "answer": "На вечер, свидания и светские события"},
            {"question_id": 2, "answer": "Шлейфовый заметный, заполняющий пространство"},
            {"question_id": 3, "answer": "Глубокая бархатная сладость с ликерными нотами"},
            {"question_id": 4, "answer": "Без резкого мускуса и мыла"},
            {"question_id": 5, "answer": "Утонченный твист — знакомый профиль с интересной изюминкой"}
        ]
    })
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()

    assert rec_data["status"] == "success"
    assert len(rec_data["recommendations"]) == 10

    # Chain of thought requirement
    assert "chain_of_thought" in rec_data
    assert rec_data["chain_of_thought"] is not None
    assert len(rec_data["chain_of_thought"]) > 50

    # Strict JSON structure test according to ТЗ (requirement #5 + image_url)
    first_item = rec_data["recommendations"][0]
    assert "rank" in first_item
    assert "brand" in first_item
    assert "name" in first_item
    assert "family" in first_item
    assert "notes" in first_item
    assert "image_url" in first_item
    assert first_item["image_url"].startswith("http") or first_item["image_url"].startswith("/api/perfumes/")
    assert "reason" in first_item
    assert isinstance(first_item["notes"], list)
    assert first_item["rank"] == 1

    # Verify strict image_url uniqueness for each item rank 1 to 10
    image_urls = [r["image_url"] for r in rec_data["recommendations"]]
    assert len(image_urls) == 10
    assert len(set(image_urls)) == 10, f"Found duplicate image URLs: {image_urls}"


def test_direct_recommendation_api():
    response = client.post("/api/sommelier/recommend", json={
        "perfume_name": "Baccarat Rouge 540",
        "category": "Унисекс",
        "answers": [
            {"question_id": 1, "answer": "Каждый день и статусная работа"},
            {"question_id": 2, "answer": "Интимная аура близко к коже"},
            {"question_id": 3, "answer": "Минеральная прохлада и чистота"},
            {"question_id": 4, "answer": "Без приторности"},
            {"question_id": 5, "answer": "Смелый концептуальный авангард"}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["recommendations"]) == 10
    assert "chain_of_thought" in data
    assert data["chain_of_thought"] is not None

    # Verify strict image_url uniqueness in direct recommendations
    rec_urls = [r["image_url"] for r in data["recommendations"]]
    assert len(rec_urls) == 10
    assert len(set(rec_urls)) == 10


def test_perfume_badge_svg_endpoint():
    """Verify dynamic SVG flacon badge endpoint returns valid SVG with perfume branding."""
    response = client.get("/api/perfumes/tom-ford-lost-cherry/badge.svg")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert "TOM FORD" in response.text
    assert "Lost Cherry" in response.text


def test_pwa_manifest_and_sw():
    """Verify PWA manifest and service worker endpoints adhere to PWA standards."""
    manifest_resp = client.get("/manifest.json")
    assert manifest_resp.status_code == 200
    manifest = manifest_resp.json()
    assert manifest["name"] == "ABOO Perfumes"
    assert manifest["short_name"] == "ABOO"
    assert manifest["display"] == "standalone"
    assert manifest["theme_color"] == "#000000"
    assert manifest["background_color"] == "#000000"

    sw_resp = client.get("/sw.js")
    assert sw_resp.status_code == 200
    assert "application/javascript" in sw_resp.headers["content-type"]
    assert "ABOO PERFUMES" in sw_resp.text


