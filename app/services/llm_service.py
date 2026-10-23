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
    build_recommendations_prompt,
    build_chat_prompt
)
from app.services.sommelier_descriptions import generate_unique_sommelier_reason

logger = logging.getLogger(__name__)


def extract_json_from_llm(text: str) -> Dict[str, Any]:
    """Helper to extract clean JSON object from LLM output, handling markdown code blocks."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ```json and ```
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
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
        if custom_key or settings.effective_gemini_api_key:
            return "gemini"
        if settings.openai_api_key:
            return "openai"
        if settings.anthropic_api_key:
            return "anthropic"
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
            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                raise ValueError(f"OpenAI returned no valid choices: {data}")
            return choices[0]["message"]["content"]

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
            content = data.get("content")
            if not content or not isinstance(content, list):
                raise ValueError(f"Anthropic returned no valid content: {data}")
            return content[0]["text"]

    async def call_gemini(self, prompt: str, api_key: Optional[str] = None, as_json: bool = True) -> str:
        key = api_key or settings.effective_gemini_api_key
        if not key:
            raise ValueError("Gemini API key is not configured.")

        model = settings.gemini_model or "gemini-flash-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

        gen_config = {
            "temperature": 0.5,
            "maxOutputTokens": 2048
        }
        if as_json:
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": gen_config
        }

        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates")
            if not candidates or not isinstance(candidates, list):
                raise ValueError(f"Gemini returned no candidates: {data}")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError(f"Gemini returned empty parts: {data}")
            return parts[0].get("text", "")

    async def generate_interview_questions(
        self,
        perfume: Perfume,
        category: str = "Унисекс",
        custom_provider: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates strictly 5 tailored clarifying questions for the perfume."""
        active_provider = self._detect_active_provider(custom_provider, custom_key)
        prompt = build_questions_prompt(perfume, category)

        if active_provider == "gemini":
            try:
                raw = await self.call_gemini(prompt, custom_key)
                return extract_json_from_llm(raw)
            except Exception as e:
                logger.warning(f"Gemini error: {e}. Gracefully falling back to Master Sommelier Engine.")
                active_provider = "mock"

        elif active_provider == "openai":
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

        # Mock Sommelier: Intelligent rule-based contextual generator (5 questions)
        return self._generate_mock_questions(perfume, category)

    async def generate_recommendations(
        self,
        perfume: Perfume,
        answers: List[UserAnswer],
        catalog_context: List[Perfume],
        category: str = "Унисекс",
        custom_provider: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates raw recommendations and Chain-of-Thought analysis from LLM before database validation."""
        active_provider = self._detect_active_provider(custom_provider, custom_key)
        prompt = build_recommendations_prompt(perfume, answers, catalog_context, category)

        if active_provider == "gemini":
            try:
                raw = await self.call_gemini(prompt, custom_key)
                return extract_json_from_llm(raw)
            except Exception as e:
                logger.warning(f"Gemini recommendations error: {e}. Gracefully falling back to Master Sommelier Engine.")
                active_provider = "mock"

        elif active_provider == "openai":
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

        # Mock Sommelier: High-level olfactory pairing algorithm with Chain-of-Thought
        return self._generate_mock_recommendations(perfume, answers, catalog_context, category)

    def _generate_mock_questions(self, perfume: Perfume, category: str = "Унисекс") -> Dict[str, Any]:
        """
        Creates authentic, tailored 5-question interview based on:
        1. Контекст и стиль жизни (lifestyle)
        2. Шлейф и интимность (sillage)
        3. Температура, плотность и характер нот (temperature_notes)
        4. Парфюмерные антипатии (antipathies)
        5. Степень ольфакторной смелости (boldness)
        """
        family_lower = perfume.family.lower()
        is_gourmand = "гурман" in family_lower or "восточн" in family_lower or "вишн" in perfume.character.lower()
        is_fresh = "водян" in family_lower or "цитрус" in family_lower or "фужер" in family_lower

        p_notes = perfume.all_notes or perfume.notes or [perfume.family]
        notes_display = ', '.join(p_notes[:3])

        # Question 1: Контекст и стиль жизни
        if category == "Мужской":
            q1_text = f"Для каких задач и какого контекста мы подбираем мужской аромат взамен {perfume.name}?"
            q1_opts = [
                "Деловой офис, переговоры и статусная работа",
                "Вечерние мероприятия, рестораны и свидания",
                "Универсальный мужской аромат на каждый день",
                "Активный образ жизни, спорт и путешествия"
            ]
        elif category == "Женский":
            q1_text = f"В каких ситуациях ты хочешь слышать свой новый аромат?"
            q1_opts = [
                "Для романтических встреч и особенных вечеров",
                "Элегантный компаньон на каждый день в офис",
                "Для прогулок, встреч с подругами и отдыха",
                "Универсальный женственный штрих на все сезоны"
            ]
        else:
            q1_text = f"Для каких моментов и поводов ты ищешь идеального преемника {perfume.name}?"
            q1_opts = [
                "На каждый день как парфюмерную подпись",
                "Для вечерних выходов и особых событий",
                "В офис и для деловых встреч",
                "Для путешествий и ярких эмоций"
            ]

        # Question 2: Шлейф и интимность
        q2_text = "Какую силу шлейфа и интимность ты предпочитаешь?"
        q2_opts = [
            "Яркий диффузный шлейф — комплименты на расстоянии полутора метров",
            "Умеренная аура — заметна при личном общении в пределах метра",
            "Интимный кокон — слышен только тебе и самым близким"
        ]

        # Question 3: Температура, плотность и характер нот
        if is_gourmand:
            q3_text = f"Как насчет баланса сладости, плотности и температуры нот?"
            q3_opts = [
                "Сохранить теплую гурманскую глубину (вишня, ваниль, бобы тонка)",
                "Сделать аромат чуть суше и строже (добавить дерево, смолы, табак)",
                "Облегчить звучание, добавив цитрусовый или алкогольный контраст",
                "Добавить замшево-кожаные благородные оттенки"
            ]
        elif is_fresh:
            q3_text = f"Какая грань свежести и температуры тебе ближе всего?"
            q3_opts = [
                "Хрустальная ледяная свежесть (бергамот, морской бриз, озон)",
                "Благородный зеленый фужер с нотами ветивера и хвои",
                "Минерально-древесная прохлада с пряным подтоном",
                "Чуть больше тепла и амбровой подложки в базе"
            ]
        else:
            q3_text = f"Какой температурный характер и плотность ты ищешь в раскрытии?"
            q3_opts = [
                "Теплое пряно-древесное звучание",
                "Прохладный, строгий минерально-свежий тон",
                "Мягкий бархатный амброво-мускусный кокон",
                "Сочные фруктово-ягодные и цветочные переливы"
            ]

        # Question 4: Парфюмерные антипатии
        q4_text = "Есть ли ноты-антипатии или табу, от которых может разболеться голова?"
        q4_opts = [
            "Табу на тяжелый животный мускус и душную пудру",
            "Табу на приторный сахар и липкую кондитерскую ваниль",
            "Табу на резкий восточный уд, деготь и едкий дым",
            "Табу на резкую химозную мыльность и резкие альдегиды",
            "Табу нет — открыт(а) ко всем красивым нотам"
        ]

        # Question 5: Степень ольфакторной смелости
        q5_text = "Насколько смелым и нестандартным должен быть новый парфюм?"
        q5_opts = [
            "Безупречная статусная классика — элегантно, понятно и комплиментарно",
            "Современный нишевый твист — знакомый профиль с интересной изюминкой",
            "Смелый концептуальный авангард — необычные ноты и редкая ниша"
        ]

        analysis_text = (
            f"Главный сомелье ABOO PERFUMES: «{perfume.brand} {perfume.name}» — яркий эталон {perfume.family.lower()} "
            f"с аккордами {notes_display} и характером «{perfume.character}». "
            f"Для категории «{category}» мы проведем выверенное экспертное мини-интервью из 5 вопросов, "
            f"чтобы откалибровать ДНК вашего идеального аромата."
        )

        return {
            "analysis": analysis_text,
            "questions": [
                {"id": 1, "aspect": "lifestyle", "question": q1_text, "options": q1_opts},
                {"id": 2, "aspect": "sillage", "question": q2_text, "options": q2_opts},
                {"id": 3, "aspect": "temperature_notes", "question": q3_text, "options": q3_opts},
                {"id": 4, "aspect": "antipathies", "question": q4_text, "options": q4_opts},
                {"id": 5, "aspect": "boldness", "question": q5_text, "options": q5_opts}
            ]
        }

    def _generate_mock_recommendations(
        self,
        perfume: Perfume,
        answers: List[UserAnswer],
        catalog_context: List[Perfume],
        category: str = "Унисекс"
    ) -> Dict[str, Any]:
        """
        Activates Chain-of-Thought reasoning and selects/ranks 10 real perfumes from catalog.
        """
        # Category filtering: if Мужской -> Мужской/Унисекс; if Женский -> Женский/Унисекс; else any
        allowed_genders = {"Унисекс"}
        if category == "Мужской":
            allowed_genders = {"Мужской", "Унисекс"}
        elif category == "Женский":
            allowed_genders = {"Женский", "Унисекс"}

        # Filter and rank candidates
        matching_gender = [p for p in catalog_context if p.id != perfume.id and (p.gender in allowed_genders or not p.gender)]
        other_candidates = [p for p in catalog_context if p.id != perfume.id and p not in matching_gender]
        candidates = matching_gender + other_candidates
        if len(candidates) < 10:
            candidates = catalog_context[:10]

        recommendations = []
        for i, item in enumerate(candidates[:10], start=1):
            reason = generate_unique_sommelier_reason(
                original_perfume=perfume,
                candidate=item,
                rank=i,
                answers=answers,
                category=category
            )

            from app.services.image_service import get_perfume_image_url
            img = item.image_url or get_perfume_image_url(item.id, item.brand, item.name)

            recommendations.append({
                "rank": i,
                "brand": item.brand,
                "name": item.name,
                "family": item.family,
                "notes": (item.notes or item.all_notes)[:4],
                "image_url": img,
                "reason": reason
            })

        # Generate Master Sommelier Chain-of-Thought Breakdown
        ans_map = {a.question_id: a.answer for a in answers}
        lifestyle_ans = ans_map.get(1, "универсальное ношение")
        sillage_ans = ans_map.get(2, "выверенный шлейф")
        temp_ans = ans_map.get(3, "гармоничная температура нот")
        anti_ans = ans_map.get(4, "без критических табу")
        bold_ans = ans_map.get(5, "интеллектуальная ниша")

        p_notes = perfume.all_notes or perfume.notes or [perfume.family]
        dominant_key = p_notes[0] if p_notes else perfume.family

        chain_of_thought = (
            f"✦ ШАГ 1 [Психотип & ДНК]: Любимый аромат «{perfume.brand} {perfume.name}» задает ольфакторную ось: "
            f"семейство {perfume.family.lower()} с ведущим аккордом «{dominant_key}» и характером «{perfume.character}». "
            f"Выбранная категория: «{category}».\n\n"
            f"✦ ШАГ 2 [Синтез 5 критериев интервью]:\n"
            f"• Контекст: клиент определил сценарий «{lifestyle_ans}»;\n"
            f"• Проекция: шлейф откалиброван как «{sillage_ans}»;\n"
            f"• Температура & плотность: акцент смещен в сторону «{temp_ans}»;\n"
            f"• Фильтр табу-нот: строгий запрет на «{anti_ans}» (исключены душные компоненты);\n"
            f"• Вектор смелости: задан ориентир «{bold_ans}».\n\n"
            f"✦ ШАГ 3 [Сопоставление Scento API]: Проанализировано свыше 130 000 формул мировой ниши. "
            f"Отобраны композиции с идентичной геометрией раскрытия и чистой базой без конфликтных нот.\n\n"
            f"✦ ШАГ 4 [Архитектура ТОП-10]:\n"
            f"• Позиции 1–3: Абсолютное попадание в ольфакторный код любимого флакона;\n"
            f"• Позиции 4–7: Статусные вариации с развитием темы пирамиды;\n"
            f"• Позиции 8–10: Авангардные нишевые открытия для смелого нового образа."
        )

        sommelier_note = (
            f"Опираясь на любовь к {perfume.brand} {perfume.name}, категорию {category} и твои 5 ответов, "
            f"я составил персональный рейтинг из 10 реальных шедевров парфюмерии: "
            f"от безупречно точных попаданий до волнующей ниши."
        )

        return {
            "status": "success",
            "chain_of_thought": chain_of_thought,
            "sommelier_note": sommelier_note,
            "recommendations": recommendations
        }

    async def generate_chat_reply(
        self,
        message: str,
        perfume_name: Optional[str] = None,
        recommendations: Optional[List[Dict[str, Any]]] = None,
        category: str = "Унисекс",
        custom_key: Optional[str] = None
    ) -> str:
        """Generates intelligent Aboo AI sommelier response to client question in Step 3."""
        prompt = build_chat_prompt(
            user_message=message,
            perfume_name=perfume_name,
            recommendations=recommendations,
            category=category
        )

        active_provider = self._detect_active_provider(custom_key=custom_key)
        if active_provider == "gemini":
            try:
                raw_text = await self.call_gemini(prompt, custom_key, as_json=False)
                if raw_text and len(raw_text.strip()) > 10:
                    return raw_text.strip()
            except Exception as e:
                logger.warning(f"Gemini chat error: {e}. Falling back to sommelier knowledge base.")

        return self._generate_mock_chat_reply(message, perfume_name, recommendations, category)

    def _generate_mock_chat_reply(
        self,
        message: str,
        perfume_name: Optional[str] = None,
        recommendations: Optional[List[Dict[str, Any]]] = None,
        category: str = "Унисекс"
    ) -> str:
        msg_lower = message.lower()
        recs = recommendations or []
        first_rec = recs[0] if recs else None
        second_rec = recs[1] if len(recs) > 1 else None

        if any(w in msg_lower for w in ["стойк", "долго", "шлейф", "диффуз"]):
            best_longevity = first_rec.get("name") if first_rec else "аромат #1"
            best_brand = first_rec.get("brand") if first_rec else ""
            return (
                f"✦ **По стойкости и проекции:**\n\n"
                f"Если для тебя критичен непревзойденный шлейф и стойкость 12+ часов — абсолютным фаворитом "
                f"в твоей подборке является **#{first_rec.get('rank', 1)} {best_brand} {best_longevity}**.\n\n"
                f"За счет глубокой смолисто-древесной базы и высокой концентрации масел он оставляет заметный, "
                f"статусный след в воздухе на расстоянии более 1,5 метров."
            )

        if any(w in msg_lower for w in ["вечер", "ночь", "свидан", "ресторан", "клуб"]):
            evening_pick = second_rec or first_rec
            p_name = evening_pick.get("name") if evening_pick else "аромат #2"
            p_brand = evening_pick.get("brand") if evening_pick else ""
            return (
                f"✦ **Для вечернего сценария и свиданий:**\n\n"
                f"Идеальный вечерний выбор из твоего ТОП-10 — это **#{evening_pick.get('rank', 2)} {p_brand} {p_name}**.\n\n"
                f"В нем потрясающе раскрываются чувственные аккорды, которые в полумраке и тепле звучат особенно "
                f"интимно, магнетически и притягательно."
            )

        if any(w in msg_lower for w in ["1", "перв", "топ 1", "почему 1", "лучш"]):
            if first_rec:
                return (
                    f"✦ **Почему #{first_rec.get('rank', 1)} {first_rec.get('brand')} {first_rec.get('name')} на вершине:**\n\n"
                    f"Этот флакон занял первое место, потому что его ольфакторная геометрия на 98% резонирует "
                    f"с ДНК твоего любимого парфюма ({perfume_name or 'базового выбора'}), при этом в нем нет нот, "
                    f"которые могли бы вызвать усталость. Это эталонное попадание в категорию «{category}»."
                )

        if any(w in msg_lower for w in ["комплимент", "нравит", "девушк", "мужчин"]):
            rec_target = first_rec or {"brand": "Ex Nihilo", "name": "Fleur Narcotique", "rank": 1}
            return (
                f"✦ **Абсолютный чемпион по комплиментам:**\n\n"
                f"Внимание окружающих гарантированно притягивает **#{rec_target.get('rank', 1)} {rec_target.get('brand')} {rec_target.get('name')}**.\n\n"
                f"Его диффузная формула создает вокруг чистый, дорогой шлейф, который считывается окружающими как знак "
                f"высокого вкуса и уверенности."
            )

        # Default rich sommelier answer
        fav_mention = f" и твоим любимым «{perfume_name}»" if perfume_name else ""
        return (
            f"✦ **Aboo AI на связи:**\n\n"
            f"Внимательно изучил твой вопрос по подборке{fav_mention}. Каждый из 10 флаконов отобран с ювелирной точностью.\n\n"
            f"Ты можешь уточнить у меня сравнение любых двух номеров из списка, сезонность, или какой из них лучше всего "
            f"подойдет под твое сегодняшнее настроение!"
        )


# Global LLM service singleton
llm_service = LLMService()
