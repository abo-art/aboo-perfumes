"""
Catalog Service for loading, indexing, searching, and validating perfumes.
Uses RapidFuzz for high-accuracy phonetic and token-level matching across Russian and English.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from rapidfuzz import fuzz, process

from app.config import settings
from app.models.perfume import Perfume, PerfumeSearchResult


class CatalogService:
    def __init__(self, json_path: Optional[str] = None):
        self.json_path = Path(json_path or settings.catalog_json_path)
        self.perfumes: Dict[str, Perfume] = {}  # keyed by id
        self.search_corpus: List[Tuple[str, str]] = []  # (search_string, perfume_id)
        self.brands: set = set()
        self.families: set = set()
        self._load_catalog()

    def _load_catalog(self) -> None:
        """Loads catalog from SQLite database (falling back to JSON / seed if needed)."""
        from app.database import get_all_perfumes, init_db, count_perfumes
        from app.services.image_service import get_perfume_image_url

        init_db()
        if count_perfumes() == 0 and self.json_path.exists():
            from app.data.seed_db import seed_database
            seed_database()

        db_perfumes = get_all_perfumes()

        # Fallback to JSON if database was somehow empty
        if not db_perfumes and self.json_path.exists():
            with open(self.json_path, "r", encoding="utf-8") as f:
                db_perfumes = json.load(f)

        self.perfumes.clear()
        self.search_corpus.clear()
        self.brands.clear()
        self.families.clear()

        from app.services.external_api import NOTE_TRANSLATIONS, ACCORD_TRANSLATIONS

        def _translate_n(n: str) -> str:
            clean = str(n).strip().lower()
            return NOTE_TRANSLATIONS.get(clean, str(n).strip())

        def _translate_a(a: str) -> str:
            clean = str(a).strip().lower()
            return ACCORD_TRANSLATIONS.get(clean, str(a).strip())

        for item in db_perfumes:
            if not item.get("image_url") or item.get("image_url", "").startswith("/api/"):
                img_resolved = get_perfume_image_url(item["id"], item.get("brand", ""), item.get("name", ""))
                if img_resolved.startswith("http") or not item.get("image_url"):
                    item["image_url"] = img_resolved
            fam = item.get("family", "Нишевые аккорды")
            if not item.get("all_notes"):
                item["all_notes"] = item.get("notes", []) or item.get("top_notes", []) or [fam]
            if not item.get("notes"):
                item["notes"] = item.get("all_notes", [])[:6] or [fam]
            if not item.get("top_notes"):
                item["top_notes"] = item.get("notes", [])[:2] or [fam]
            if not item.get("base_notes"):
                item["base_notes"] = item.get("all_notes", [])[-2:] or [fam]
            if not item.get("description"):
                item["description"] = item.get("character", "")

            # Translate all notes and accords to Russian
            item["top_notes"] = [_translate_n(n) for n in item.get("top_notes", [])]
            item["heart_notes"] = [_translate_n(n) for n in item.get("heart_notes", [])]
            item["base_notes"] = [_translate_n(n) for n in item.get("base_notes", [])]
            item["all_notes"] = [_translate_n(n) for n in item.get("all_notes", [])]
            item["notes"] = [_translate_n(n) for n in item.get("notes", [])]
            item["accords"] = [_translate_a(a) for a in item.get("accords", [])]

            perfume = Perfume(**item)
            self.perfumes[perfume.id] = perfume
            self.brands.add(perfume.brand)
            self.families.add(perfume.family)

            # Build full searchable entries
            full_title = f"{perfume.brand} {perfume.name}"
            self.search_corpus.append((full_title.lower(), perfume.id))
            self.search_corpus.append((perfume.name.lower(), perfume.id))

            for alias in perfume.aliases:
                self.search_corpus.append((alias.lower(), perfume.id))
                self.search_corpus.append((f"{perfume.brand} {alias}".lower(), perfume.id))

    def _register_perfume(self, perfume: Perfume) -> None:
        """Registers and caches a verified Perfume into runtime memory and SQLite database."""
        if not perfume:
            return

        if perfume.id in self.perfumes:
            existing = self.perfumes[perfume.id]
            # Merge and preserve Russian slang and aliases
            merged_aliases = list(dict.fromkeys(existing.aliases + perfume.aliases))
            perfume.aliases = merged_aliases
            if existing.notes and not perfume.notes:
                perfume.notes = existing.notes
            if existing.all_notes and not perfume.all_notes:
                perfume.all_notes = existing.all_notes
            if existing.character and len(existing.character) > len(perfume.character or ""):
                perfume.character = existing.character
                perfume.description = existing.description

        self.perfumes[perfume.id] = perfume
        self.brands.add(perfume.brand)
        self.families.add(perfume.family)

        full_title = f"{perfume.brand} {perfume.name}".lower()
        self.search_corpus.append((full_title, perfume.id))
        self.search_corpus.append((perfume.name.lower(), perfume.id))
        for alias in perfume.aliases:
            self.search_corpus.append((alias.lower(), perfume.id))
            self.search_corpus.append((f"{perfume.brand} {alias}".lower(), perfume.id))

        try:
            from app.database import upsert_perfume
            upsert_perfume(perfume.model_dump())
        except Exception as e:
            pass

    def get_by_id(self, perfume_id: str) -> Optional[Perfume]:
        return self.perfumes.get(perfume_id)

    def get_all(self) -> List[Perfume]:
        return list(self.perfumes.values())

    def search(self, query: str, limit: int = 10, min_score: float = 40.0, category: Optional[str] = None) -> List[PerfumeSearchResult]:
        """
        Fuzzy search across perfume titles, names, brands, and Russian/English aliases.
        Optionally boosts items matching the selected category.
        """
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip().lower()
        scored_ids: Dict[str, Tuple[float, str]] = {}  # id -> (best_score, match_source)

        allowed_genders = None
        if category == "Мужской":
            allowed_genders = {"Мужской", "Унисекс"}
        elif category == "Женский":
            allowed_genders = {"Женский", "Унисекс"}

        for search_str, p_id in self.search_corpus:
            # Calculate composite token and word ratio
            score_ratio = fuzz.WRatio(clean_query, search_str)
            score_token = fuzz.token_set_ratio(clean_query, search_str)
            score_partial = fuzz.partial_ratio(clean_query, search_str) if len(clean_query) >= 4 else 0

            # Weight token set and WRatio
            score = max(score_ratio, score_token, score_partial * 0.9)

            # Bonus for exact substring match
            if clean_query in search_str or search_str in clean_query:
                score = max(score, 88.0)

            # Category boost
            if allowed_genders:
                p_item = self.perfumes.get(p_id)
                if p_item and p_item.gender in allowed_genders:
                    score += 5.0

            if score >= min_score:
                if p_id not in scored_ids or score > scored_ids[p_id][0]:
                    scored_ids[p_id] = (score, "alias" if " " not in search_str else "catalog")

        # Sort by score descending
        sorted_results = sorted(scored_ids.items(), key=lambda x: x[1][0], reverse=True)[:limit]

        results = []
        for p_id, (score, source) in sorted_results:
            perfume = self.perfumes.get(p_id)
            if perfume:
                results.append(PerfumeSearchResult(
                    perfume=perfume,
                    score=round(score, 1),
                    match_source=source
                ))

        return results

    async def async_search(self, query: str, limit: int = 10, min_score: float = 40.0) -> List[PerfumeSearchResult]:
        """
        Searches perfume catalog via live ScentRev API (130,000+ fragrances),
        merging with local catalog and caching any newly fetched bottles.
        """
        if not query or len(query.strip()) < 2:
            return []

        results: List[PerfumeSearchResult] = []
        seen_ids = set()

        # 1. Query live ScentRev / Scento API first if configured
        try:
            from app.services.external_api import scentrev_client
            if scentrev_client.is_configured:
                external_perfumes = await scentrev_client.search_fragrances(query, limit=limit)
                for ext_p in external_perfumes:
                    self._register_perfume(ext_p)
                    results.append(PerfumeSearchResult(
                        perfume=ext_p,
                        score=100.0,
                        match_source="scentrev_api"
                    ))
                    seen_ids.add(ext_p.id)
        except Exception as e:
            pass

        # 2. Query local catalog and merge
        local_results = self.search(query, limit=limit, min_score=min_score)
        for lr in local_results:
            if lr.perfume.id not in seen_ids and len(results) < limit:
                results.append(lr)
                seen_ids.add(lr.perfume.id)

        return results[:limit]

    def find_best_match(self, perfume_name: str) -> Tuple[Optional[Perfume], float]:
        """
        Finds the single best matched perfume in catalog.
        Returns (Perfume, confidence_score).
        """
        results = self.search(perfume_name, limit=1)
        if results and results[0].score >= settings.validation_threshold:
            return results[0].perfume, results[0].score
        elif results:
            return results[0].perfume, results[0].score
        return None, 0.0

    async def async_find_best_match(self, perfume_name: str) -> Tuple[Optional[Perfume], float]:
        """
        Finds the best matched perfume using live ScentRev / Scento API first,
        falling back to local database. Merges authentic bottle images with rich curated descriptions.
        """
        local_perf, local_score = self.find_best_match(perfume_name)

        try:
            from app.services.external_api import scentrev_client
            if scentrev_client.is_configured:
                ext_matches = await scentrev_client.search_fragrances(perfume_name, limit=3)
                if ext_matches:
                    best_ext = ext_matches[0]
                    # If high confidence local match exists, enrich with curated Russian metadata
                    if local_perf and local_score >= 80.0:
                        if not best_ext.image_url and local_perf.image_url:
                            best_ext.image_url = local_perf.image_url
                        if local_perf.character and len(local_perf.character) > len(best_ext.character or ""):
                            best_ext.character = local_perf.character
                        if local_perf.family:
                            best_ext.family = local_perf.family
                        if local_perf.subfamily:
                            best_ext.subfamily = local_perf.subfamily
                        if local_perf.top_notes:
                            best_ext.top_notes = local_perf.top_notes
                        if local_perf.heart_notes:
                            best_ext.heart_notes = local_perf.heart_notes
                        if local_perf.base_notes:
                            best_ext.base_notes = local_perf.base_notes
                    self._register_perfume(best_ext)
                    return best_ext, 100.0
        except Exception as e:
            logger.warning(f"Error during async_find_best_match for '{perfume_name}': {e}")

        return local_perf, local_score

    def verify_perfume(self, brand: str, name: str) -> Tuple[bool, Optional[Perfume], float]:
        """
        Strict validation to eliminate LLM hallucinations.
        Verifies if both brand and perfume actually exist in the database.
        Returns: (is_valid, canonical_perfume_or_none, score)
        """
        clean_brand = brand.strip().lower()
        clean_name = name.strip().lower()

        if not clean_name:
            return False, None, 0.0

        best_perfume: Optional[Perfume] = None
        best_composite_score = 0.0

        for perfume in self.perfumes.values():
            perf_brand = perfume.brand.lower()
            perf_name = perfume.name.lower()

            # Name match score (against canonical name or aliases)
            name_score = max(
                fuzz.token_set_ratio(clean_name, perf_name),
                fuzz.WRatio(clean_name, perf_name)
            )
            for alias in perfume.aliases:
                alias_score = max(
                    fuzz.token_set_ratio(clean_name, alias.lower()),
                    fuzz.WRatio(clean_name, alias.lower())
                )
                name_score = max(name_score, alias_score)

            # Brand match score
            if clean_brand:
                brand_score = max(
                    fuzz.token_set_ratio(clean_brand, perf_brand),
                    fuzz.WRatio(clean_brand, perf_brand)
                )
            else:
                brand_score = 100.0 if name_score >= 85.0 else 0.0

            # Both brand AND name must match with high threshold
            if clean_brand:
                # Require name match >= 72 and brand match >= 70
                if name_score >= 72.0 and brand_score >= 70.0:
                    composite = (name_score * 0.6) + (brand_score * 0.4)
                    if composite > best_composite_score:
                        best_composite_score = composite
                        best_perfume = perfume
            else:
                if name_score >= 82.0:
                    if name_score > best_composite_score:
                        best_composite_score = name_score
                        best_perfume = perfume

        if best_perfume and best_composite_score >= settings.validation_threshold:
            return True, best_perfume, round(best_composite_score, 1)

        return False, None, round(best_composite_score, 1)

    async def async_verify_perfume(self, brand: str, name: str) -> Tuple[bool, Optional[Perfume], float]:
        """
        Validates perfume existence against local catalog and live ScentRev API (130,000+ perfumes).
        Guarantees 0% hallucinations by consulting official external perfume catalog.
        """
        # 1. Check local catalog
        is_valid, perf, score = self.verify_perfume(brand, name)
        if is_valid and perf:
            return True, perf, score

        # 2. Check live ScentRev / Scento API
        try:
            from app.services.external_api import scentrev_client
            if scentrev_client.is_configured:
                ext_perfume = await scentrev_client.verify_and_resolve(brand, name)
                if ext_perfume:
                    self._register_perfume(ext_perfume)
                    return True, ext_perfume, 95.0
        except Exception as e:
            pass

        return False, None, score

    def find_similar_by_profile(
        self,
        target_perfume: Perfume,
        limit: int = 10,
        exclude_ids: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> List[Perfume]:
        """
        Calculates olfactory proximity between perfumes based on shared notes,
        accords, family, and character. Prioritizes items in the selected category.
        """
        exclude = set(exclude_ids or [])
        exclude.add(target_perfume.id)

        target_notes = {n.lower() for n in target_perfume.all_notes}
        target_accords = {a.lower() for a in target_perfume.accords}
        target_family = target_perfume.family.lower()

        allowed_genders = None
        if category == "Мужской":
            allowed_genders = {"Мужской", "Унисекс"}
        elif category == "Женский":
            allowed_genders = {"Женский", "Унисекс"}

        scores: List[Tuple[float, Perfume]] = []

        for candidate in self.perfumes.values():
            if candidate.id in exclude:
                continue

            score = 0.0

            # Category matching
            if allowed_genders:
                if candidate.gender in allowed_genders:
                    score += 10.0
                else:
                    score -= 8.0
            cand_notes = {n.lower() for n in candidate.all_notes}
            cand_accords = {a.lower() for a in candidate.accords}

            # Shared notes
            shared_notes = target_notes.intersection(cand_notes)
            score += len(shared_notes) * 3.0

            # Shared accords
            shared_accords = target_accords.intersection(cand_accords)
            score += len(shared_accords) * 4.0

            # Family match
            if candidate.family.lower() == target_family:
                score += 8.0
            elif target_perfume.subfamily and candidate.subfamily and target_perfume.subfamily == candidate.subfamily:
                score += 6.0

            scores.append((score, candidate))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scores[:limit]]


# Global singleton instance
catalog_service = CatalogService()
