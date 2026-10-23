"""
Sommelier Service orchestrating the complete 3-step User Flow:
1. Input perfume validation & extraction of olfactory notes.
2. Generating exactly 3 targeted interview questions via LLM.
3. Forming and strictly validating the ranked TOP-10 real perfumes.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.models.perfume import Perfume
from app.models.interview import ClarifyingQuestion, InterviewStartResponse, UserAnswer
from app.models.recommendation import RecommendationItem, Top10Response
from app.services.catalog_service import catalog_service
from app.services.llm_service import llm_service
from app.services.validator import validator

logger = logging.getLogger(__name__)


class SommelierSession:
    def __init__(self, session_id: str, perfume: Perfume, questions: List[ClarifyingQuestion], analysis: str):
        self.session_id = session_id
        self.perfume = perfume
        self.questions = questions
        self.analysis = analysis
        self.created_at = datetime.now(timezone.utc)
        self.answers: List[UserAnswer] = []
        self.recommendations: Optional[List[RecommendationItem]] = None


class SommelierService:
    def __init__(self):
        self.catalog = catalog_service
        self.llm = llm_service
        self.validator = validator
        self.sessions: Dict[str, SommelierSession] = {}

    async def start_interview(
        self,
        perfume_name: str,
        custom_provider: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> InterviewStartResponse:
        """
        Step 1 & 2:
        - Resolves perfume name in database.
        - Pulls notes, family, accords, character.
        - LLM generates exactly 3 clarifying questions.
        - Creates a new session.
        """
        # Step 1: Catalog lookup and verification
        perfume, score = self.catalog.find_best_match(perfume_name)

        if not perfume:
            # Fallback: create dynamic placeholder if not in local catalog
            perfume = Perfume(
                id=f"custom-{uuid.uuid4().hex[:8]}",
                brand="Любимый парфюм",
                name=perfume_name.strip(),
                family="Восточные древесные",
                top_notes=["Бергамот", "Пряности"],
                heart_notes=["Цветочные ноты", "Древесные аккорды"],
                base_notes=["Амбра", "Мускус", "Сандал"],
                all_notes=["Бергамот", "Пряности", "Цветочные ноты", "Амбра", "Мускус", "Сандал"],
                character="Индивидуальный парфюмерный профиль пользователя",
                accords=["Пряный", "Древесный", "Амбровый"],
                season=["Всесезонный"]
            )
            score = 50.0

        # Step 2: Interview generation (exactly 3 targeted questions)
        llm_output = await self.llm.generate_interview_questions(
            perfume=perfume,
            custom_provider=custom_provider,
            custom_key=custom_key
        )

        analysis = llm_output.get("analysis", f"{perfume.brand} {perfume.name} — яркий образец семейства {perfume.family}.")
        raw_questions = llm_output.get("questions", [])

        questions: List[ClarifyingQuestion] = []
        for q_data in raw_questions[:3]:
            questions.append(ClarifyingQuestion(
                id=q_data.get("id", len(questions) + 1),
                aspect=q_data.get("aspect", "general"),
                question=q_data.get("question", ""),
                options=q_data.get("options", [])
            ))

        # Ensure exactly 3 questions
        while len(questions) < 3:
            idx = len(questions) + 1
            if idx == 1:
                questions.append(ClarifyingQuestion(
                    id=1,
                    aspect="occasion",
                    question="Для каких случаев и в какое время года ты чаще всего хочешь его носить?",
                    options=["На каждый день в офис", "Для вечера и свиданий", "Универсальный на любой сезон"]
                ))
            elif idx == 2:
                questions.append(ClarifyingQuestion(
                    id=2,
                    aspect="sillage",
                    question="Какой шлейф и стойкость ты предпочитаешь?",
                    options=["Заметный шлейф на метр и более", "Умеренный элегантный шлейф", "Близкий к коже, интимный"]
                ))
            elif idx == 3:
                questions.append(ClarifyingQuestion(
                    id=3,
                    aspect="notes_antipathies",
                    question="Есть ли ноты, которые ты категорически не любишь, или наоборот, акцент, который хочешь добавить?",
                    options=["Без тяжелой сладости", "Без животного мускуса", "Без резкого дыма и смол", "Любые смелые ноты"]
                ))

        session_id = str(uuid.uuid4())
        session = SommelierSession(session_id, perfume, questions, analysis)
        self.sessions[session_id] = session

        return InterviewStartResponse(
            session_id=session_id,
            matched_perfume=perfume,
            confidence=round(score, 1),
            analysis=analysis,
            questions=questions
        )

    async def get_recommendations_for_session(
        self,
        session_id: str,
        answers: List[UserAnswer],
        custom_provider: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Top10Response:
        """
        Step 3:
        - Receives user answers to the 3 questions.
        - Grounds LLM with verified catalog context.
        - Generates raw candidates.
        - Strictly validates each item against catalog to eliminate hallucinations.
        - Returns ranked TOP-10 real perfumes.
        """
        session = self.sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found. Please start a new interview.")

        session.answers = answers
        return await self._generate_and_validate_top10(
            perfume=session.perfume,
            answers=answers,
            custom_provider=custom_provider,
            custom_key=custom_key
        )

    async def direct_recommend(
        self,
        perfume_name: str,
        answers: List[UserAnswer],
        custom_provider: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Top10Response:
        """Convenience method to recommend directly from perfume name and answers without an explicit prior session."""
        perfume, _ = self.catalog.find_best_match(perfume_name)
        if not perfume:
            perfume = (await self.start_interview(perfume_name)).matched_perfume

        return await self._generate_and_validate_top10(
            perfume=perfume,
            answers=answers,
            custom_provider=custom_provider,
            custom_key=custom_key
        )

    async def _generate_and_validate_top10(
        self,
        perfume: Perfume,
        answers: List[UserAnswer],
        custom_provider: Optional[str] = None,
        custom_key: Optional[str] = None
    ) -> Top10Response:
        """Core logic to invoke LLM, then strictly validate output against database."""
        # Olfactory context pool from database to feed into LLM prompt
        catalog_context = self.catalog.find_similar_by_profile(perfume, limit=35)
        if len(catalog_context) < 15:
            catalog_context = self.catalog.get_all()[:35]

        # Call LLM
        raw_output = await self.llm.generate_recommendations(
            perfume=perfume,
            answers=answers,
            catalog_context=catalog_context,
            custom_provider=custom_provider,
            custom_key=custom_key
        )

        raw_recs = raw_output.get("recommendations", [])

        # Strict validation: Check every item against real database, remove hallucinations, replace with real matches
        validated_top10 = self.validator.validate_and_correct_top10(
            raw_recommendations=raw_recs,
            original_perfume=perfume,
            answers=answers
        )

        sommelier_note = (
            f"Опираясь на твою симпатию к {perfume.brand} {perfume.name} и твои ответы, "
            f"я сформировал персональный рейтинг из 10 реальных ароматов: "
            f"первые позиции — максимально близкие по ольфакторному ДНК, средние — элегантное развитие идеи, "
            f"а замыкающие — смелые альтернативы для расширения твоего парфюмерного гардероба."
        )

        return Top10Response(
            status="success",
            recommendations=validated_top10,
            original_perfume=perfume,
            sommelier_note=sommelier_note
        )


# Global sommelier service singleton
sommelier_service = SommelierService()
