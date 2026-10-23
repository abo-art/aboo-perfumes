"""
Pydantic models for Perfume entity, search queries, and catalog entries.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Perfume(BaseModel):
    id: str
    brand: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    gender: str = "Унисекс"
    family: str
    subfamily: Optional[str] = None
    top_notes: List[str] = Field(default_factory=list)
    heart_notes: List[str] = Field(default_factory=list)
    base_notes: List[str] = Field(default_factory=list)
    all_notes: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list, description="Массив ключевых нот: верх, сердце, база")
    image_url: str = Field(default="", description="Ссылка на качественное изображение флакона")
    description: str = Field(default="", description="Краткое описание характера / mood")
    character: str = ""
    accords: List[str] = Field(default_factory=list)
    season: List[str] = Field(default_factory=list)
    sillage: str = ""
    longevity: str = ""
    year: Optional[int] = None
    price_category: str = "Ниша / Люкс"


class PerfumeSearchResult(BaseModel):
    perfume: Perfume
    score: float = Field(..., description="Fuzzy match confidence score (0-100)")
    match_source: str = Field(default="catalog", description="'catalog', 'alias', or 'external'")


class PerfumeSearchResponse(BaseModel):
    query: str
    count: int
    results: List[PerfumeSearchResult]
