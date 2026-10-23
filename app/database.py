"""
Relational SQLite Database layer for Aboo Perfume Sommelier.
Implements the required perfume card schema with indexes and JSON serializations.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

DB_PATH = Path(settings.database_path)


def get_db_connection() -> sqlite3.Connection:
    """Creates a thread-safe connection to SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    """Initializes the database tables and indexes according to specification."""
    with get_db_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS perfumes (
            id TEXT PRIMARY KEY,
            brand TEXT NOT NULL,
            name TEXT NOT NULL,
            family TEXT NOT NULL,
            subfamily TEXT,
            gender TEXT DEFAULT 'Унисекс',
            notes TEXT NOT NULL,
            top_notes TEXT,
            heart_notes TEXT,
            base_notes TEXT,
            all_notes TEXT,
            image_url TEXT NOT NULL,
            description TEXT NOT NULL,
            character TEXT,
            accords TEXT,
            season TEXT,
            sillage TEXT,
            longevity TEXT,
            year INTEGER,
            price_category TEXT,
            aliases TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_perfumes_brand ON perfumes(brand);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perfumes_name ON perfumes(name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perfumes_family ON perfumes(family);")
        conn.commit()
    logger.info(f"SQLite database initialized at {DB_PATH}")


def serialize_json(val: Any) -> str:
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    return str(val) if val is not None else "[]"


def deserialize_json(val: Any) -> List[Any]:
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except Exception:
        return []


def upsert_perfume(p: Dict[str, Any]) -> None:
    """Inserts or updates a perfume in the SQLite database."""
    # Ensure notes is a combined list of key notes
    notes = p.get("notes") or p.get("all_notes") or (p.get("top_notes", []) + p.get("heart_notes", []))
    description = p.get("description") or p.get("character") or ""
    image_url = p.get("image_url") or ""

    with get_db_connection() as conn:
        conn.execute("""
        INSERT INTO perfumes (
            id, brand, name, family, subfamily, gender,
            notes, top_notes, heart_notes, base_notes, all_notes,
            image_url, description, character, accords, season,
            sillage, longevity, year, price_category, aliases
        ) VALUES (
            :id, :brand, :name, :family, :subfamily, :gender,
            :notes, :top_notes, :heart_notes, :base_notes, :all_notes,
            :image_url, :description, :character, :accords, :season,
            :sillage, :longevity, :year, :price_category, :aliases
        )
        ON CONFLICT(id) DO UPDATE SET
            brand=excluded.brand,
            name=excluded.name,
            family=excluded.family,
            subfamily=excluded.subfamily,
            gender=excluded.gender,
            notes=excluded.notes,
            top_notes=excluded.top_notes,
            heart_notes=excluded.heart_notes,
            base_notes=excluded.base_notes,
            all_notes=excluded.all_notes,
            image_url=excluded.image_url,
            description=excluded.description,
            character=excluded.character,
            accords=excluded.accords,
            season=excluded.season,
            sillage=excluded.sillage,
            longevity=excluded.longevity,
            year=excluded.year,
            price_category=excluded.price_category,
            aliases=excluded.aliases;
        """, {
            "id": p["id"],
            "brand": p["brand"],
            "name": p["name"],
            "family": p["family"],
            "subfamily": p.get("subfamily"),
            "gender": p.get("gender", "Унисекс"),
            "notes": serialize_json(notes),
            "top_notes": serialize_json(p.get("top_notes", [])),
            "heart_notes": serialize_json(p.get("heart_notes", [])),
            "base_notes": serialize_json(p.get("base_notes", [])),
            "all_notes": serialize_json(p.get("all_notes", [])),
            "image_url": image_url,
            "description": description,
            "character": p.get("character", description),
            "accords": serialize_json(p.get("accords", [])),
            "season": serialize_json(p.get("season", [])),
            "sillage": p.get("sillage", ""),
            "longevity": p.get("longevity", ""),
            "year": p.get("year"),
            "price_category": p.get("price_category", "Ниша / Люкс"),
            "aliases": serialize_json(p.get("aliases", []))
        })
        conn.commit()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a SQLite row into a hydrated dictionary with parsed JSON fields."""
    d = dict(row)
    d["notes"] = deserialize_json(d.get("notes"))
    d["top_notes"] = deserialize_json(d.get("top_notes"))
    d["heart_notes"] = deserialize_json(d.get("heart_notes"))
    d["base_notes"] = deserialize_json(d.get("base_notes"))
    d["all_notes"] = deserialize_json(d.get("all_notes"))
    d["accords"] = deserialize_json(d.get("accords"))
    d["season"] = deserialize_json(d.get("season"))
    d["aliases"] = deserialize_json(d.get("aliases"))
    return d


def get_perfume_by_id(perfume_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM perfumes WHERE id = ?", (perfume_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_all_perfumes() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM perfumes ORDER BY brand ASC, name ASC")
        return [row_to_dict(r) for r in cursor.fetchall()]


def count_perfumes() -> int:
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM perfumes")
        return cursor.fetchone()[0]
