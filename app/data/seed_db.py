"""
Database Seeding Script for Aboo Perfume Sommelier.
Initializes SQLite database and populates it with verified perfume cards,
including notes, description/mood, and valid high-resolution bottle image URLs.
"""

import json
from pathlib import Path
from app.database import init_db, upsert_perfume, count_perfumes
from app.services.image_service import get_perfume_image_url

DATA_DIR = Path(__file__).resolve().parent
CATALOG_JSON = DATA_DIR / "perfumes_catalog.json"


def seed_database():
    """Initializes and seeds SQLite database with perfume entries."""
    init_db()

    if not CATALOG_JSON.exists():
        raise FileNotFoundError(f"Catalog JSON not found at {CATALOG_JSON}. Please run catalog_generator.py first.")

    with open(CATALOG_JSON, "r", encoding="utf-8") as f:
        perfumes_data = json.load(f)

    updated_perfumes = []
    print(f"✦ Seeding {len(perfumes_data)} perfumes into SQLite database...")

    for item in perfumes_data:
        p_id = item["id"]
        brand = item["brand"]
        name = item["name"]

        # Ensure valid image_url
        image_url = item.get("image_url") or get_perfume_image_url(p_id, brand, name)
        item["image_url"] = image_url

        # Ensure description/mood
        description = item.get("description") or item.get("character") or f"Изысканный аромат от {brand}."
        item["description"] = description
        item["character"] = description

        # Ensure key notes array
        key_notes = item.get("notes") or item.get("all_notes") or (item.get("top_notes", []) + item.get("heart_notes", []))
        item["notes"] = key_notes[:6]

        # Upsert into SQLite
        upsert_perfume(item)
        updated_perfumes.append(item)

    # Sync back to catalog JSON so JSON and SQLite are 100% synchronized
    with open(CATALOG_JSON, "w", encoding="utf-8") as f:
        json.dump(updated_perfumes, f, ensure_ascii=False, indent=2)

    total_in_db = count_perfumes()
    print(f"✓ Successfully seeded {total_in_db} perfumes into SQLite database.")


if __name__ == "__main__":
    seed_database()
