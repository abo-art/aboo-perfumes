"""
Pydantic models for Top-10 Recommendations according to project specification.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.perfume import Perfume
from app.models.interview import UserAnswer


class RecommendationItem(BaseModel):
    rank: int = Field(..., ge=1, le=10, description="Rank from 1 (closest hit) to 10 (bold alternative)")
    brand: str = Field(..., description="Perfume brand")
    name: str = Field(..., description="Perfume name")
    family: str = Field(..., description="Olfactory family")
    notes: List[str] = Field(..., description="Key notes: top, heart, base")
    image_url: str = Field(..., description="Ссылка на качественное изображение флакона")
    reason: str = Field(..., description="Sommelier justification: why it fits the user")
    
    # Supplementary verified metadata (enriched from database)
    id: Optional[str] = None
    description: Optional[str] = None
    character: Optional[str] = None
    accords: Optional[List[str]] = None
    sillage: Optional[str] = None
    longevity: Optional[str] = None
    gender: Optional[str] = None
    verified: bool = True


class Top10Response(BaseModel):
    status: str = "success"
    recommendations: List[RecommendationItem] = Field(..., min_length=10, max_length=10, description="Ranked TOP-10 real perfumes")
    original_perfume: Optional[Perfume] = None
    sommelier_note: Optional[str] = None


class RecommendationRequest(BaseModel):
    session_id: Optional[str] = None
    perfume_name: Optional[str] = None
    answers: List[UserAnswer] = Field(..., min_length=1, max_length=3, description="User answers to the 3 interview questions")
