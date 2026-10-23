"""
Strict Validation Engine for Anti-Hallucination enforcement.
Validates every single perfume recommendation against the real catalog database.
Guarantees 100% verified real market perfumes in the final TOP-10 output.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional, Set
from app.models.perfume import Perfume
from app.models.recommendation import RecommendationItem
from app.models.interview import UserAnswer
from app.services.catalog_service import catalog_service

logger = logging.getLogger(__name__)


class RecommendationValidator:
    def __init__(self):
        self.catalog = catalog_service

    def validate_item(self, item_dict: Dict[str, Any]) -> Tuple[bool, Optional[Perfume], float]:
        """
        Validates if brand and perfume actually exist in the database.
        Returns: (is_valid, canonical_perfume, score)
        """
        brand = item_dict.get("brand", "").strip()
        name = item_dict.get("name", "").strip()

        if not name:
            return False, None, 0.0

        is_valid, perfume, score = self.catalog.verify_perfume(brand, name)
        return is_valid, perfume, score

    def validate_and_correct_top10(
        self,
        raw_recommendations: List[Dict[str, Any]],
        original_perfume: Perfume,
        answers: Optional[List[UserAnswer]] = None
    ) -> List[RecommendationItem]:
        """
        Validates the raw LLM output against the verified catalog.
        - Verifies brand and perfume name.
        - Canonicalizes and enriches notes and family with real catalog data.
        - If the LLM hallucinated any item or returned fewer than 10,
          substitutes with verified real perfumes matching the olfactory profile.
        - Guarantees exactly 10 real perfumes, ranked 1 to 10.
        """
        verified_items: List[RecommendationItem] = []
        used_perfume_ids: Set[str] = {original_perfume.id}

        # Step 1: Process and validate raw recommendations from LLM
        for raw in raw_recommendations:
            is_valid, perfume, score = self.validate_item(raw)

            if is_valid and perfume and perfume.id not in used_perfume_ids:
                used_perfume_ids.add(perfume.id)

                # Canonicalize brand and name from verified database
                reason = raw.get("reason", "").strip()
                if not reason or len(reason) < 10:
                    reason = f"Превосходно перекликается с нотами {perfume.name}: {', '.join(perfume.all_notes[:3])}."

                # Ensure notes are real notes from the verified database
                real_notes = perfume.all_notes[:4]

                verified_items.append(RecommendationItem(
                    rank=len(verified_items) + 1,
                    brand=perfume.brand,
                    name=perfume.name,
                    family=perfume.family,
                    notes=real_notes,
                    reason=reason,
                    id=perfume.id,
                    character=perfume.character,
                    accords=perfume.accords[:4],
                    sillage=perfume.sillage,
                    longevity=perfume.longevity,
                    gender=perfume.gender,
                    verified=True
                ))

                if len(verified_items) == 10:
                    break
            else:
                logger.info(f"Validator rejected or de-duplicated: '{raw.get('brand')} - {raw.get('name')}' (score={score})")

        # Step 2: If LLM hallucinated or returned fewer than 10 valid items, fill up with verified matches
        if len(verified_items) < 10:
            deficit = 10 - len(verified_items)
            logger.info(f"Filling {deficit} missing slots with verified catalog olfactory neighbors.")

            fallback_candidates = self.catalog.find_similar_by_profile(
                original_perfume,
                limit=deficit + 5,
                exclude_ids=list(used_perfume_ids)
            )

            for cand in fallback_candidates:
                if len(verified_items) >= 10:
                    break
                if cand.id in used_perfume_ids:
                    continue

                used_perfume_ids.add(cand.id)
                rank = len(verified_items) + 1

                if rank <= 3:
                    reason = f"Точное попадание в профиль {original_perfume.name}: благородная база из {', '.join(cand.base_notes[:2])} и родственное семейство {cand.family.lower()}."
                elif rank <= 7:
                    reason = f"Изысканная интерпретация любимых аккордов: ноты {', '.join(cand.all_notes[:3])} с изящным шлейфом."
                else:
                    reason = f"Смелая нишевая альтернатива от {cand.brand}: необычное раскрытие ноты {cand.all_notes[0]} для расширения вкуса."

                verified_items.append(RecommendationItem(
                    rank=rank,
                    brand=cand.brand,
                    name=cand.name,
                    family=cand.family,
                    notes=cand.all_notes[:4],
                    reason=reason,
                    id=cand.id,
                    character=cand.character,
                    accords=cand.accords[:4],
                    sillage=cand.sillage,
                    longevity=cand.longevity,
                    gender=cand.gender,
                    verified=True
                ))

        # Re-number ranks 1 to 10
        for idx, item in enumerate(verified_items[:10], start=1):
            item.rank = idx

        return verified_items[:10]


# Global validator singleton
validator = RecommendationValidator()
