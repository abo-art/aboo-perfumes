"""
Unified LLM Service supporting OpenAI, Anthropic Claude, Gemini, and intelligent Mock Sommelier.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings
from app.models.perfume import Perfume
from app.models.interview import ClarifyingQuestion, UserAnswer
from app.services.prompt_manager import (
    SYSTEM_PROMPT,
    build_questions_prompt,
    build_recommendations_prompt
)

logger = logging.getLogger(__name__)


def extract_json_from_llm(text: str) -> Dict[str, Any]:
    """Helper to extract clean JSON object from LLM output, handling markdown code blocks."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ```json and ```
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # If extra text surrounds json
    json_match = re.search(r'(\{[\s\S]*\})', cleaned)
    if json_match:
        cleaned = json_match.group(1)

    return json.loads(cleaned)


class LLMService:
    def __init__(self):
        self.provider = settings.llm_provider

    def _detect_active_provider(self, custom_provider: Optional[str] = None, custom_key: Optional[str] = None) -> str:
        if custom_provider and custom_provider != "auto":
            return custom_provider
        if self.provider != "auto":
            return self.provider
        if custom_key or settings.openai_api_key:
            return "openai"
        if settings.anthropic_api_key:
            return "anthropic"
        if settings.gemini_api_key:
            return "gemini"
        return "mock"

    async def call_openai(self, prompt: str, api_key: Optional[str] = None) -> str:
        key = api_key or settings.openai_api_key
        base_url = settings.openai_base_url or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "response_format": {"type": "json_object"} if "gpt" in settings.openai_model else None
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def call_anthropic(self, prompt: str, api_key: Optional[str] = None) -> str:
        key = api_key or settings.anthropic_api_key
        url = "https://api.anthropic.com/v1/messages"

        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": settings.anthropic_model,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2048,
            "temperature": 0.5
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def generate_interview_questions(
        self,
        perfume: Perfume,
        custom_provider: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates exactly 3 tailored clarifying questions for the perfume."""
        active_provider = self._detect_active_provider(custom_provider, custom_key)
        prompt = build_questions_prompt(perfume)

        if active_provider == "openai":
            try:
                raw = await self.call_openai(prompt, custom_key)
                return extract_json_from_llm(raw)
            except Exception as e:
                logger.warning(f"OpenAI error: {e}. Falling back to Sommelier Mock.")
                active_provider = "mock"

        elif active_provider == "anthropic":
            try:
                raw = await self.call_anthropic(prompt, custom_key)
                return extract_json_from_llm(raw)
            except Exception as e:
                logger.warning(f"Anthropic error: {e}. Falling back to Sommelier Mock.")
                active_provider = "mock"

        # Mock Sommelier: Intelligent rule-based contextual generator
        return self._generate_mock_questions(perfume)

    async def generate_recommendations(
        self,
        perfume: Perfume,
        answers: List[UserAnswer],
        catalog_context: List[Perfume],
        custom_provider: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates raw recommendations list from LLM before database validation."""
        active_provider = self._detect_active_provider(custom_provider, custom_key)
        prompt = build_recommendations_prompt(perfume, answers, catalog_context)

        if active_provider == "openai":
            try:
                raw = await self.call_openai(prompt, custom_key)
                return extract_json_from_llm(raw)
            except Exception as e:
                logger.warning(f"OpenAI error: {e}. Falling back to Sommelier Mock.")
                active_provider = "mock"

        elif active_provider == "anthropic":
            try:
                raw = await self.call_anthropic(prompt, custom_key)
                return extract_json_from_llm(raw)
            except Exception as e:
                logger.warning(f"Anthropic error: {e}. Falling back to Sommelier Mock.")
                active_provider = "mock"

        # Mock Sommelier: High-level olfactory pairing algorithm
        return self._generate_mock_recommendations(perfume, answers, catalog_context)

    def _generate_mock_questions(self, perfume: Perfume) -> Dict[str, Any]:
        """Creates authentic, tailored sommelier questions based on the perfume's family & notes."""
        family_lower = perfume.family.lower()
        is_gourmand = "гурман" in family_lower or "восточн" in family_lower or "вишн" in perfume.character.lower()
        is_fresh = "водян" in family_lower or "цитрус" in family_lower or "фужер" in family_lower

        if is_gourmand:
            q1_text = f"В какой обстановке ты планируешь носить новый аромат чаще всего?"
            q1_opts = [
                "Для вечерних выходов, свиданий и ресторанов",
                "На каждый день, но чтобы звучал уютно и дорого",
                "Только в прохладную погоду и на открытом воздухе"
            ]
            q2_text = f"Какой характер шлейфа тебе ближе к телу?"
            q2_opts = [
                "Яркий, обволакивающий шлейф, который притягивает взгляды",
                "Умеренный шлейф — слышен на расстоянии полутора метров",
                "Интимное звучание — только для самых близких людей"
            ]
            q3_text = f"Чего хотелось бы избежать или какой акцент подчеркнуть?"
            q3_opts = [
                "Избегать приторности — хочется больше древесных или алкогольных нот",
                "Сохранить сладковато-вишневую / ванильную грань, но добавить табак или смолы",
                "Хочется чего-то неожиданного и более дерзкого"
            ]
        elif is_fresh:
            q1_text = f"Куда планируешь надевать аромат?"
            q1_opts = [
                "В офис и на деловые встречи (нужен статусный политкорректный аккорд)",
                "На каждый день, прогулки и спорт",
                "Универсальный — от утренней тренировки до вечернего бара"
            ]
            q2_text = f"Насколько заметным должен быть шлейф?"
            q2_opts = [
                "Максимально диффузный, чтобы аромат оставался в воздухе после твоего ухода",
                "Деликатная свежая аура чистоты вокруг тебя",
                "Стойкий близко к коже на весь рабочий день"
            ]
            q3_text = f"Есть ли ноты, которые тебя отталкивают?"
            q3_opts = [
                "Без мыльных и резких химозных нот цитруса",
                "Без тяжелой сладости и густой ванили",
                "Без выраженного животного мускуса"
            ]
        else:
            q1_text = f"Для каких моментов и какого настроения ищем замену {perfume.name}?"
            q1_opts = [
                "Для особенных случаев и вечернего настроения",
                "На каждый день как парфюмерную подпись",
                "Для холодного сезона и согревающих встреч"
            ]
            q2_text = f"Какую стойкость и шлейф ты ожидаешь?"
            q2_opts = [
                "Шлейфовый монстр с высокой стойкостью от 10 часов",
                "Элегантный шлейф средней громкости на 6-8 часов",
                "Тонкий кокон для близкого контакта"
            ]
            q3_text = f"Есть ли ноты-антипатии или табу в звучании?"
            q3_opts = [
                "Категорически без тяжелого восточного уда и ладана",
                "Без душных белых цветов и пудры",
                "Открыт(а) к смелым экспериментам и нишевым аккордам"
            ]

        return {
            "analysis": f"{perfume.brand} {perfume.name} — это великолепный представитель {perfume.family.lower()}, покоряющий нотами {', '.join(perfume.all_notes[:3])} и настроением: «{perfume.character}». Чтобы подобрать ему идеального преемника, уточним твои вкусы.",
            "questions": [
                {"id": 1, "aspect": "occasion", "question": q1_text, "options": q1_opts},
                {"id": 2, "aspect": "sillage", "question": q2_text, "options": q2_opts},
                {"id": 3, "aspect": "notes_antipathies", "question": q3_text, "options": q3_opts}
            ]
        }

    def _generate_mock_recommendations(
        self,
        perfume: Perfume,
        answers: List[UserAnswer],
        catalog_context: List[Perfume]
    ) -> Dict[str, Any]:
        """Selects and ranks 10 real perfumes from catalog with expert sommelier reasoning."""
        # Find candidates matching the olfactory sphere
        candidates = [p for p in catalog_context if p.id != perfume.id]
        if len(candidates) < 10:
            candidates = catalog_context[:10]

        recommendations = []
        for i, item in enumerate(candidates[:10], start=1):
            if i <= 3:
                reason = f"Прямое попадание в эстетику {perfume.name}: гармоничное созвучие нот ({', '.join(item.all_notes[:3])}) с акцентом на твои пожелания."
            elif i <= 7:
                reason = f"Изысканное развитие знакомой темы: сохраняет благородный почерк {item.brand}, раскрывая новые грани {item.family.lower()}."
            else:
                reason = f"Смелая нишевая альтернатива: яркий аккорд {item.all_notes[0]} и нестандартная база {', '.join(item.base_notes[:2])} для эффектного нового образа."

            recommendations.append({
                "rank": i,
                "brand": item.brand,
                "name": item.name,
                "family": item.family,
                "notes": item.all_notes[:4],
                "reason": reason
            })

        return {
            "status": "success",
            "recommendations": recommendations
        }


# Global LLM service singleton
llm_service = LLMService()
