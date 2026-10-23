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
        """Loads catalog JSON and builds search indices."""
        if not self.json_path.exists():
            raise FileNotFoundError(f"Perfume catalog not found at {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.perfumes.clear()
        self.search_corpus.clear()
        self.brands.clear()
        self.families.clear()

        for item in data:
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

    def get_by_id(self, perfume_id: str) -> Optional[Perfume]:
        return self.perfumes.get(perfume_id)

    def get_all(self) -> List[Perfume]:
        return list(self.perfumes.values())

    def search(self, query: str, limit: int = 10, min_score: float = 40.0) -> List[PerfumeSearchResult]:
        """
        Fuzzy search across perfume titles, names, brands, and Russian/English aliases.
        """
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip().lower()
        scored_ids: Dict[str, Tuple[float, str]] = {}  # id -> (best_score, match_source)

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

    def find_best_match(self, perfume_name: str) -> Tuple[Optional[Perfume], float]:
        """
        Finds the single best matched perfume in catalog.
        Returns (Perfume, confidence_score).
        """
        results = self.search(perfume_name, limit=1)
        if results and results[0].score >= settings.validation_threshold:
            return results[0].perfume, results[0].score
        elif results:
            # Return even if below threshold but with lower confidence for validation inspection
            return results[0].perfume, results[0].score
        return None, 0.0

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

    def find_similar_by_profile(
        self,
        target_perfume: Perfume,
        limit: int = 10,
        exclude_ids: Optional[List[str]] = None
    ) -> List[Perfume]:
        """
        Calculates olfactory proximity between perfumes based on shared notes,
        accords, family, and character.
        Used for intelligent recommendation ranking and anti-hallucination substitution.
        """
        exclude = set(exclude_ids or [])
        exclude.add(target_perfume.id)

        target_notes = {n.lower() for n in target_perfume.all_notes}
        target_accords = {a.lower() for a in target_perfume.accords}
        target_family = target_perfume.family.lower()

        scores: List[Tuple[float, Perfume]] = []

        for candidate in self.perfumes.values():
            if candidate.id in exclude:
                continue

            score = 0.0
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
