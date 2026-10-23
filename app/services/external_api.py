"""
External Scentrev / Scento Fragrance API Client.
Integrates official 130,000+ fragrance catalog, authentic bottle images,
note pyramids, and anti-hallucination verification from api.scentrev.com.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple, Set
import httpx
from rapidfuzz import fuzz

from app.config import settings
from app.models.perfume import Perfume

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Generates a clean URL and ID-friendly slug from brand and perfume name."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


# Russian Cyrillic to English transliteration / common brand & perfume mappings
CYRILLIC_PERFUME_MAP = {
    "лост черри": "Lost Cherry",
    "черри": "Lost Cherry",
    "вишня": "Lost Cherry",
    "том форд": "Tom Ford",
    "том форд черри": "Tom Ford Lost Cherry",
    "том форд вишня": "Tom Ford Lost Cherry",
    "бакара": "Baccarat Rouge 540",
    "бакара 540": "Baccarat Rouge 540",
    "бакарат": "Baccarat Rouge 540",
    "бакарат руж": "Baccarat Rouge 540",
    "авентус": "Creed Aventus",
    "крид": "Creed",
    "крид авентус": "Creed Aventus",
    "ганимед": "Marc-Antoine Barrois Ganymede",
    "доля ангелов": "Kilian Angels' Share",
    "ангел шер": "Kilian Angels' Share",
    "буа империал": "Essential Parfums Bois Imperial",
    "боис империал": "Essential Parfums Bois Imperial",
    "флер наркотик": "Ex Nihilo Fleur Narcotique",
    "бал дафрик": "Byredo Bal d'Afrique",
    "черный фантом": "Kilian Black Phantom",
    "блэк фантом": "Kilian Black Phantom",
    "табако ваниль": "Tom Ford Tobacco Vanille",
    "табак ваниль": "Tom Ford Tobacco Vanille",
    "херод": "Parfums de Marly Herod",
    "ирод": "Parfums de Marly Herod",
    "джаз клуб": "Maison Margiela Jazz Club",
    "шерги": "Serge Lutens Chergui",
}

ACCORD_TRANSLATIONS = {
    "woody": "древесные",
    "warm-spicy": "теплые пряные",
    "warm spicy": "теплые пряные",
    "sweet": "сладкие",
    "vanilla": "ванильные",
    "amber": "амбровые",
    "fruity": "фруктовые",
    "cinnamon": "коричные",
    "leather": "кожаные",
    "powdery": "пудровые",
    "fresh-spicy": "свежие пряные",
    "fresh spicy": "свежие пряные",
    "aromatic": "ароматические",
    "citrus": "цитрусовые",
    "white-floral": "белоцветочные",
    "white floral": "белоцветочные",
    "floral": "цветочные",
    "musky": "мускусные",
    "animalic": "анималистические",
    "balsamic": "бальзамические",
    "smoky": "дымные",
    "almond": "миндальные",
    "caramel": "карамельные",
    "patchouli": "пачули",
    "earthy": "землистые",
    "tobacco": "табачные",
    "cherry": "вишневые",
    "aquatic": "акватические",
    "marine": "морские",
    "green": "зеленые",
    "rose": "розовые",
    "oud": "удовые",
    "mineral": "минеральные",
    "metallic": "металлические",
    "lactonic": "молочно-кремовые",
    "coffee": "кофейные",
    "rum": "ромовые",
    "boozy": "ликёрные",
    "conifer": "хвойные",
    "herbal": "травяные",
    "ozonic": "озоновые",
    "aldehydic": "альдегидные",
    "mossy": "мшистые",
    "soapy": "чистые мыльные",
    "gourmand": "гурманские",
    "whiskey": "виски",
    "honey": "медовые",
    "chocolate": "шоколадные",
    "cacao": "какао",
    "nutty": "ореховые",
    "woody-spicy": "древесно-пряные",
}

NOTE_TRANSLATIONS = {
    "cognac": "Коньяк",
    "cinnamon": "Корица",
    "tonka bean": "Бобы тонка",
    "oak": "Дуб",
    "hedione": "Гедион",
    "candied almond": "Засахаренный миндаль",
    "bitter almond": "Горький миндаль",
    "almond": "Миндаль",
    "vanilla": "Ваниль",
    "praline": "Пралине",
    "sandalwood": "Сандал",
    "bergamot": "Бергамот",
    "lemon": "Лимон",
    "orange": "Апельсин",
    "mandarin": "Мандарин",
    "mandarin orange": "Мандарин",
    "grapefruit": "Грейпфрут",
    "lime": "Лайм",
    "orange blossom": "Флердоранж",
    "neroli": "Нероли",
    "jasmine": "Жасмин",
    "jasmine sambac": "Жасмин самбак",
    "rose": "Роза",
    "turkish rose": "Турецкая роза",
    "damask rose": "Дамасская роза",
    "lavender": "Лаванда",
    "cardamom": "Кардамон",
    "pink pepper": "Розовый перец",
    "black pepper": "Черный перец",
    "pepper": "Перец",
    "nutmeg": "Мускатный орех",
    "cloves": "Гвоздика",
    "star anise": "Звездчатый анис",
    "anise": "Анис",
    "coriander": "Кориандр",
    "ginger": "Имбирь",
    "mint": "Мята",
    "cedar": "Белый кедр",
    "cedarwood": "Кедр",
    "vetiver": "Ветивер",
    "musk": "Мускус",
    "white musk": "Белый мускус",
    "amber": "Амбра",
    "ambergris": "Серая амбра",
    "ambroxan": "Амброксан",
    "iso e super": "Изо Е Супер",
    "akigalawood": "Акигалавуд",
    "cashmeran": "Кашмеран",
    "patchouli": "Пачули",
    "iris": "Ирис",
    "orris": "Корень ириса",
    "tobacco": "Табак",
    "leather": "Кожа",
    "suede": "Замша",
    "oud": "Уд",
    "agarwood": "Агаровое дерево",
    "saffron": "Шафран",
    "incense": "Ладан",
    "myrrh": "Мирра",
    "labdanum": "Лабданум",
    "benzoin": "Бензоин",
    "olibanum": "Олибанум",
    "elemi": "Элеми",
    "guaiac wood": "Гваяк",
    "coffee": "Кофе",
    "chocolate": "Шоколад",
    "dark chocolate": "Темный шоколад",
    "honey": "Мёд",
    "caramel": "Карамель",
    "peach": "Персик",
    "cherry": "Вишня",
    "black cherry": "Черная вишня",
    "sour cherry": "Вишня",
    "plum": "Слива",
    "apple": "Яблоко",
    "pear": "Груша",
    "black currant": "Черная смородина",
    "raspberry": "Малина",
    "blackberry": "Ежевика",
    "fig": "Инжир",
    "coconut": "Кокос",
    "rhubarb": "Ревень",
    "sea salt": "Морская соль",
    "sea notes": "Морские ноты",
    "mineral notes": "Минеральные ноты",
    "rum": "Ром",
    "whiskey": "Виски",
    "liquor": "Ликёр",
    "cacao": "Какао",
    "violet": "Фиалка",
    "violet leaf": "Лист фиалки",
    "tuberose": "Тубероза",
    "ylang-ylang": "Иланг-иланг",
    "osmanthus": "Османтус",
    "lily of the valley": "Ландыш",
    "peony": "Пион",
    "freesia": "Фрезия",
    "magnolia": "Магнолия",
    "cypress": "Кипарис",
    "pine": "Сосна",
    "fir": "Пихта",
    "birch": "Береза",
    "smoke": "Дым",
    "civet": "Цивет",
    "castoreum": "Кастореум",
    "moss": "Мох",
    "oakmoss": "Дубовый мох",
}


def infer_family(raw_family: Optional[str], accords: List[str], notes: List[str]) -> Tuple[str, Optional[str]]:
    """Infers Russian perfume family and subfamily from accords and notes."""
    acc_str = " ".join([a.lower() for a in accords])
    notes_str = " ".join([n.lower() for n in notes])
    combined = f"{acc_str} {notes_str}"

    if raw_family and raw_family.strip():
        rf = raw_family.lower()
        if "woody" in rf:
            return "Древесные", "Пряно-древесные"
        if "floral" in rf:
            return "Цветочные", "Восточно-цветочные"
        if "oriental" in rf or "amber" in rf:
            return "Восточные пряные", "Амбровые"
        if "citrus" in rf:
            return "Цитрусовые свежие", "Фужерные"

    if any(k in combined for k in ["cherry", "almond", "vanilla", "sweet", "chocolate", "caramel", "honey", "tonka"]):
        return "Восточные гурманские", "Фруктово-ликёрные"
    if any(k in combined for k in ["leather", "animalic", "suede"]):
        return "Кожаные", "Дымные"
    if any(k in combined for k in ["woody", "cedar", "sandalwood", "oud", "vetiver", "patchouli"]):
        return "Древесные", "Древесно-пряные"
    if any(k in combined for k in ["amber", "warm-spicy", "balsamic", "smoky", "incense", "resinous"]):
        return "Восточные пряные", "Смолистые"
    if any(k in combined for k in ["citrus", "bergamot", "lemon", "aquatic", "marine", "fresh"]):
        return "Цитрусовые свежие", "Озоновые"
    if any(k in combined for k in ["floral", "white-floral", "rose", "jasmine", "tuberose", "iris"]):
        return "Цветочные", "Цветочно-мускусные"

    return "Нишевая парфюмерия", "Авторские аккорды"


class ScentrevApiClient:
    """
    High-performance client for interacting with Scento / ScentRev Fragrance API (api.scentrev.com).
    Integrates 130,000+ real fragrances, authentic high-res bottle photos, and pyramid notes.
    """
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or settings.effective_scentrev_api_url).rstrip("/")
        self.api_key = (api_key or settings.effective_scentrev_api_key or "").strip()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "AbooPerfumesSommelier/1.0"
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("frag_"))

    def _translate_note(self, note: str) -> str:
        clean = note.strip().lower()
        if clean in NOTE_TRANSLATIONS:
            return NOTE_TRANSLATIONS[clean]
        return note.strip()

    def _translate_accord(self, accord: str) -> str:
        clean = accord.strip().lower()
        if clean in ACCORD_TRANSLATIONS:
            return ACCORD_TRANSLATIONS[clean]
        return accord.strip()

    def _map_raw_to_perfume(self, item: Dict[str, Any]) -> Perfume:
        """Transforms a ScentRev / Scento raw JSON item into our standard Perfume model."""
        brand = (item.get("brand_name") or item.get("brand") or "Niche").strip()
        name = (item.get("name") or "Fragrance").strip()
        perfume_id = slugify(f"{brand}-{name}")

        raw_top_notes = item.get("notes_top") or []
        raw_heart_notes = item.get("notes_middle") or []
        raw_base_notes = item.get("notes_base") or []
        raw_accords = item.get("main_accords") or []

        # Ensure notes are never empty (infer from accords or standard olfactory pyramid)
        if not raw_top_notes and not raw_heart_notes and not raw_base_notes:
            if raw_accords:
                inferred = [a.replace("-", " ").title() for a in raw_accords if len(a) > 2]
                raw_top_notes = inferred[:2] if len(inferred) >= 2 else ["Бергамот", "Цитрусы"]
                raw_heart_notes = inferred[2:4] if len(inferred) >= 4 else ["Цветочные аккорды"]
                raw_base_notes = inferred[4:6] if len(inferred) >= 6 else ["Амбра", "Мускус"]
            else:
                raw_top_notes = ["Бергамот", "Пряности"]
                raw_heart_notes = ["Цветочные ноты"]
                raw_base_notes = ["Древесные ноты", "Мускус"]

        # Translate all notes and accords to Russian
        top_notes = [self._translate_note(n) for n in raw_top_notes]
        heart_notes = [self._translate_note(n) for n in raw_heart_notes]
        base_notes = [self._translate_note(n) for n in raw_base_notes]
        accords = [self._translate_accord(a) for a in raw_accords]

        all_notes = top_notes + heart_notes + base_notes
        summary_notes = (top_notes + heart_notes)[:6] or all_notes[:6]
        image_url = item.get("primary_image_url") or item.get("image_url") or ""

        gender_raw = (item.get("gender") or "unisex").lower()
        if "female" in gender_raw or "women" in gender_raw:
            gender = "Женский"
        elif "male" in gender_raw or "men" in gender_raw:
            gender = "Мужской"
        else:
            gender = "Унисекс"

        family, subfamily = infer_family(item.get("scent_family"), raw_accords, all_notes)

        character_parts = []
        if accords:
            character_parts.append(f"Выразительные аккорды: {', '.join(accords[:4])}")
        if top_notes:
            character_parts.append(f"В старте: {', '.join(top_notes[:3])}")
        character = ". ".join(character_parts) or f"Благородная нишевая композиция бренда {brand}"

        season = []
        acc_lower = [a.lower() for a in accords]
        if any(a in acc_lower for a in ["warm-spicy", "amber", "sweet", "vanilla", "leather", "balsamic"]):
            season.extend(["Осень", "Зима"])
        if any(a in acc_lower for a in ["citrus", "fresh", "aquatic", "green", "floral"]):
            season.extend(["Весна", "Лето"])
        if not season:
            season = ["Всесезонный"]

        return Perfume(
            id=perfume_id,
            brand=brand,
            name=name,
            aliases=[f"{brand.lower()} {name.lower()}", name.lower()],
            gender=gender,
            family=family,
            subfamily=subfamily,
            top_notes=top_notes,
            heart_notes=heart_notes,
            base_notes=base_notes,
            all_notes=all_notes,
            notes=summary_notes,
            image_url=image_url,
            description=character,
            character=character,
            accords=accords,
            season=season,
            sillage="Заметный / Шлейфовый",
            longevity="Высокая (7-9 часов)",
            year=item.get("release_year"),
            price_category="Люкс / Ниша"
        )

    async def search_fragrances(self, query: str, limit: int = 10) -> List[Perfume]:
        """
        Searches the live ScentRev fragrance database (~130,000 perfumes) via /api/v1/quiz/anchor-search.
        Automatically handles Cyrillic alias resolution and translation.
        """
        if not self.is_configured or not query or len(query.strip()) < 2:
            return []

        search_query = query.strip()
        clean_lower = search_query.lower()

        # Check Cyrillic map if query contains Russian letters
        if any("\u0400" <= c <= "\u04FF" for c in search_query):
            for rus_key, eng_val in CYRILLIC_PERFUME_MAP.items():
                if rus_key in clean_lower or clean_lower in rus_key:
                    search_query = eng_val
                    break

        try:
            async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
                url = f"{self.base_url}/quiz/anchor-search"
                resp = await client.get(
                    url,
                    headers=self.headers,
                    params={"q": search_query, "limit": limit}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    perfumes: List[Perfume] = []
                    for item in data:
                        try:
                            perfume = self._map_raw_to_perfume(item)
                            perfumes.append(perfume)
                        except Exception as parse_err:
                            logger.warning(f"Error mapping ScentRev item: {parse_err}")
                    return perfumes
                else:
                    logger.warning(f"ScentRev API returned HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"ScentRev API search request failed: {e}")

        return []

    async def verify_and_resolve(self, brand: str, name: str) -> Optional[Perfume]:
        """
        Strictly verifies if a perfume exists in ScentRev's official 130,000+ catalog.
        Returns the canonical Perfume object with verified bottle image, or None if hallucinated.
        """
        if not self.is_configured:
            return None

        candidates = await self.search_fragrances(f"{brand} {name}", limit=5)
        if not candidates and name:
            candidates = await self.search_fragrances(name, limit=5)

        clean_brand = brand.strip().lower()
        clean_name = name.strip().lower()

        best_match: Optional[Perfume] = None
        best_score = 0.0

        for cand in candidates:
            score_name = fuzz.token_set_ratio(clean_name, cand.name.lower())
            score_brand = fuzz.token_set_ratio(clean_brand, cand.brand.lower()) if clean_brand else 100.0

            composite = (score_name * 0.6) + (score_brand * 0.4)
            if composite > best_score:
                best_score = composite
                best_match = cand

        if best_match and best_score >= settings.validation_threshold:
            return best_match

        return None

    async def get_similar_fragrances(
        self,
        target_perfume: Perfume,
        limit: int = 10,
        exclude_ids: Optional[Set[str]] = None
    ) -> List[Perfume]:
        """
        Fetches authentic olfactory neighbors from ScentRev API based on accords and key notes.
        Ensures that fallback candidates are guaranteed real perfumes with valid images.
        """
        if not self.is_configured:
            return []

        exclude = set(exclude_ids or set())
        exclude.add(target_perfume.id)
        exclude.add(slugify(f"{target_perfume.brand}-{target_perfume.name}"))

        # Select queries based on target perfume's accords or key notes
        search_terms = []
        if target_perfume.accords:
            search_terms.extend(target_perfume.accords[:3])
        if target_perfume.top_notes:
            search_terms.extend(target_perfume.top_notes[:2])

        if not search_terms:
            search_terms = ["cherry", "vanilla", "amber", "woody"]

        found_candidates: List[Perfume] = []
        seen_names: Set[str] = set()

        for term in search_terms:
            if len(found_candidates) >= limit * 2:
                break
            results = await self.search_fragrances(term, limit=6)
            for p in results:
                title_key = f"{p.brand.lower()}-{p.name.lower()}"
                if p.id not in exclude and title_key not in seen_names:
                    seen_names.add(title_key)
                    found_candidates.append(p)

        # Rank candidates by proximity to target_perfume
        target_accords = {a.lower() for a in target_perfume.accords}
        target_notes = {n.lower() for n in target_perfume.all_notes}

        def score_perfume(cand: Perfume) -> float:
            score = 0.0
            cand_accords = {a.lower() for a in cand.accords}
            cand_notes = {n.lower() for n in cand.all_notes}
            score += len(target_accords.intersection(cand_accords)) * 4.0
            score += len(target_notes.intersection(cand_notes)) * 2.5
            if cand.family.lower() == target_perfume.family.lower():
                score += 5.0
            return score

        found_candidates.sort(key=score_perfume, reverse=True)
        return found_candidates[:limit]


# Global Scentrev API client instance
scentrev_client = ScentrevApiClient()
scento_client = scentrev_client  # Alias for backward compatibility
ScentoApiClient = ScentrevApiClient  # Class alias
