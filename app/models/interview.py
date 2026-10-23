"""
Pydantic models for Sommelier Interview dialog and user answers.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.perfume import Perfume


class ClarifyingQuestion(BaseModel):
    id: int = Field(..., description="Question number: 1, 2, or 3")
    aspect: str = Field(..., description="Aspect being clarified: 'occasion', 'sillage', or 'notes_antipathies'")
    question: str = Field(..., description="Natural conversational question in Russian")
    options: List[str] = Field(default_factory=list, description="Curated quick-reply suggestions for the UI")


class InterviewStartRequest(BaseModel):
    perfume_name: str = Field(..., min_length=2, max_length=150, description="Name or partial name of user's favorite perfume, e.g. 'Tom Ford Lost Cherry'")


class InterviewStartResponse(BaseModel):
    session_id: str
    matched_perfume: Perfume
    confidence: float
    analysis: str = Field(..., description="Sommelier's brief olfactory breakdown of the perfume")
    questions: List[ClarifyingQuestion] = Field(..., min_length=3, max_length=3, description="Exactly 3 clarifying questions")


class UserAnswer(BaseModel):
    question_id: int = Field(..., ge=1, le=3)
    question: Optional[str] = None
    answer: str = Field(..., min_length=1, description="User's response (e.g. choice option or custom text)")
