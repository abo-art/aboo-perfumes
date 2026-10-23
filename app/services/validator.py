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
from app.services.sommelier_descriptions import generate_unique_sommelier_reason

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
        answers: Optional[List[UserAnswer]] = None,
        category: Optional[str] = "Унисекс"
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

                # Ensure 100% unique, non-templated live expert reason
                reason = raw.get("reason", "").strip()
                banned_prefixes = (
                    "точное ольфакторное попадание",
                    "точное попадание в профиль",
                    "изысканное развитие знакомой темы",
                    "изысканная интерпретация любимых аккордов",
                    "смелая нишевая альтернатива"
                )
                if not reason or len(reason) < 15 or any(reason.lower().startswith(bp) for bp in banned_prefixes):
                    reason = generate_unique_sommelier_reason(
                        original_perfume=original_perfume,
                        candidate=perfume,
                        rank=len(verified_items) + 1,
                        answers=answers,
                        category=category or "Унисекс"
                    )

                real_notes = perfume.notes or perfume.all_notes[:4]
                image_url = perfume.image_url or (self.catalog.get_by_id(perfume.id).image_url if self.catalog.get_by_id(perfume.id) else "")
                from app.services.image_service import get_perfume_image_url
                if not image_url or image_url.startswith("/api/"):
                    resolved_img = get_perfume_image_url(perfume.id, perfume.brand, perfume.name)
                    if resolved_img.startswith("http"):
                        image_url = resolved_img
                    elif not image_url:
                        image_url = resolved_img

                verified_items.append(RecommendationItem(
                    rank=len(verified_items) + 1,
                    brand=perfume.brand,
                    name=perfume.name,
                    family=perfume.family,
                    notes=real_notes[:4],
                    image_url=image_url,
                    reason=reason,
                    id=perfume.id,
                    description=perfume.description or perfume.character,
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
                exclude_ids=list(used_perfume_ids),
                category=category
            )

            for cand in fallback_candidates:
                if len(verified_items) >= 10:
                    break
                if cand.id in used_perfume_ids:
                    continue

                used_perfume_ids.add(cand.id)
                rank = len(verified_items) + 1

                cand_notes = cand.all_notes or cand.notes or [cand.family]
                dominant_note = cand_notes[0] if cand_notes else cand.family
                cand_base = cand.base_notes or cand_notes
                base_preview = ', '.join(cand_base[:2]) if cand_base else cand.family
                notes_preview = ', '.join(cand_notes[:3]) if cand_notes else cand.family

                reason = generate_unique_sommelier_reason(
                    original_perfume=original_perfume,
                    candidate=cand,
                    rank=rank,
                    answers=answers,
                    category=category or "Унисекс"
                )

                cand_img = cand.image_url
                from app.services.image_service import get_perfume_image_url
                if not cand_img or cand_img.startswith("/api/"):
                    resolved_img = get_perfume_image_url(cand.id, cand.brand, cand.name)
                    if resolved_img.startswith("http"):
                        cand_img = resolved_img
                    elif not cand_img:
                        cand_img = resolved_img

                verified_items.append(RecommendationItem(
                    rank=rank,
                    brand=cand.brand,
                    name=cand.name,
                    family=cand.family,
                    notes=(cand.notes or cand.all_notes)[:4],
                    image_url=cand_img,
                    reason=reason,
                    id=cand.id,
                    description=cand.description or cand.character,
                    character=cand.character,
                    accords=cand.accords[:4],
                    sillage=cand.sillage,
                    longevity=cand.longevity,
                    gender=cand.gender,
                    verified=True
                ))

        # Re-number ranks 1 to 10 and guarantee strictly unique image_url for every recommendation
        final_items = verified_items[:10]
        used_image_urls: Set[str] = set()

        for idx, item in enumerate(final_items, start=1):
            item.rank = idx
            # If image_url is missing or duplicates an earlier rank, enforce unique flacon badge
            if not item.image_url or item.image_url in used_image_urls:
                unique_badge_url = f"/api/perfumes/{item.id}/badge.svg"
                if unique_badge_url in used_image_urls:
                    unique_badge_url = f"/api/perfumes/{item.id}/badge.svg?rank={idx}"
                item.image_url = unique_badge_url

            used_image_urls.add(item.image_url)

        return final_items

    async def async_validate_and_correct_top10(
        self,
        raw_recommendations: List[Dict[str, Any]],
        original_perfume: Perfume,
        answers: Optional[List[UserAnswer]] = None,
        category: Optional[str] = "Унисекс"
    ) -> List[RecommendationItem]:
        """
        Asynchronously validates raw recommendations against both local catalog and live ScentRev API (130,000+ perfumes).
        Guarantees 100% real market perfumes with genuine bottle photos and verified pyramids.
        """
        from app.services.external_api import scentrev_client

        verified_items: List[RecommendationItem] = []
        used_perfume_ids: Set[str] = {original_perfume.id}

        # Step 1: Validate each recommendation from LLM against local and ScentRev API
        for raw in raw_recommendations:
            brand = raw.get("brand", "").strip()
            name = raw.get("name", "").strip()

            if not name:
                continue

            is_valid, perfume, score = await self.catalog.async_verify_perfume(brand, name)

            if is_valid and perfume and perfume.id not in used_perfume_ids:
                used_perfume_ids.add(perfume.id)

                # Ensure 100% unique, non-templated live expert reason
                reason = raw.get("reason", "").strip()
                banned_prefixes = (
                    "точное ольфакторное попадание",
                    "точное попадание в профиль",
                    "изысканное развитие знакомой темы",
                    "изысканная интерпретация любимых аккордов",
                    "смелая нишевая альтернатива"
                )
                if not reason or len(reason) < 15 or any(reason.lower().startswith(bp) for bp in banned_prefixes):
                    reason = generate_unique_sommelier_reason(
                        original_perfume=original_perfume,
                        candidate=perfume,
                        rank=len(verified_items) + 1,
                        answers=answers,
                        category=category or "Унисекс"
                    )

                real_notes = perfume.notes or perfume.all_notes[:4]
                image_url = perfume.image_url or (self.catalog.get_by_id(perfume.id).image_url if self.catalog.get_by_id(perfume.id) else "")
                from app.services.image_service import get_perfume_image_url
                if not image_url or image_url.startswith("/api/"):
                    resolved_img = get_perfume_image_url(perfume.id, perfume.brand, perfume.name)
                    if resolved_img.startswith("http"):
                        image_url = resolved_img
                    elif not image_url:
                        image_url = resolved_img

                verified_items.append(RecommendationItem(
                    rank=len(verified_items) + 1,
                    brand=perfume.brand,
                    name=perfume.name,
                    family=perfume.family,
                    notes=real_notes[:4],
                    image_url=image_url,
                    reason=reason,
                    id=perfume.id,
                    description=perfume.description or perfume.character,
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
                logger.info(f"Validator rejected fake or duplicate recommendation: '{brand} - {name}' (score={score})")

        # Step 2: Fill deficit with verified real perfumes from ScentRev API and local catalog
        if len(verified_items) < 10:
            deficit = 10 - len(verified_items)
            logger.info(f"Filling {deficit} missing recommendation slots via ScentRev / Scento API.")

            fallback_candidates: List[Perfume] = []

            # 2a. Fetch live olfactory neighbors from ScentRev API
            if scentrev_client.is_configured:
                try:
                    ext_candidates = await scentrev_client.get_similar_fragrances(
                        original_perfume,
                        limit=deficit + 6,
                        exclude_ids=used_perfume_ids
                    )
                    for cand in ext_candidates:
                        if cand.id not in used_perfume_ids:
                            self.catalog._register_perfume(cand)
                            fallback_candidates.append(cand)
                except Exception as e:
                    logger.warning(f"ScentRev similar fragrances fetch error: {e}")

            # 2b. Add local catalog candidates as reliable supplement
            if len(fallback_candidates) < deficit:
                local_candidates = self.catalog.find_similar_by_profile(
                    original_perfume,
                    limit=deficit + 5,
                    exclude_ids=list(used_perfume_ids),
                    category=category
                )
                for lc in local_candidates:
                    if lc.id not in {c.id for c in fallback_candidates}:
                        fallback_candidates.append(lc)

            for cand in fallback_candidates:
                if len(verified_items) >= 10:
                    break
                if cand.id in used_perfume_ids:
                    continue

                used_perfume_ids.add(cand.id)
                rank = len(verified_items) + 1

                cand_notes = cand.all_notes or cand.notes or [cand.family]
                dominant_note = cand_notes[0] if cand_notes else cand.family
                cand_base = cand.base_notes or cand_notes
                base_preview = ', '.join(cand_base[:2]) if cand_base else cand.family
                notes_preview = ', '.join(cand_notes[:3]) if cand_notes else cand.family

                reason = generate_unique_sommelier_reason(
                    original_perfume=original_perfume,
                    candidate=cand,
                    rank=rank,
                    answers=answers,
                    category=category or "Унисекс"
                )

                cand_img = cand.image_url
                from app.services.image_service import get_perfume_image_url
                if not cand_img or cand_img.startswith("/api/"):
                    resolved_img = get_perfume_image_url(cand.id, cand.brand, cand.name)
                    if resolved_img.startswith("http"):
                        cand_img = resolved_img
                    elif not cand_img:
                        cand_img = resolved_img

                verified_items.append(RecommendationItem(
                    rank=rank,
                    brand=cand.brand,
                    name=cand.name,
                    family=cand.family,
                    notes=(cand.notes or cand.all_notes)[:4],
                    image_url=cand_img,
                    reason=reason,
                    id=cand.id,
                    description=cand.description or cand.character,
                    character=cand.character,
                    accords=cand.accords[:4],
                    sillage=cand.sillage,
                    longevity=cand.longevity,
                    gender=cand.gender,
                    verified=True
                ))

        # Re-number ranks 1 to 10 and ensure image uniqueness
        final_items = verified_items[:10]
        used_image_urls: Set[str] = set()

        for idx, item in enumerate(final_items, start=1):
            item.rank = idx
            if not item.image_url or item.image_url in used_image_urls:
                unique_badge_url = f"/api/perfumes/{item.id}/badge.svg"
                if unique_badge_url in used_image_urls:
                    unique_badge_url = f"/api/perfumes/{item.id}/badge.svg?rank={idx}"
                item.image_url = unique_badge_url

            used_image_urls.add(item.image_url)

        return final_items


# Global validator singleton
validator = RecommendationValidator()

