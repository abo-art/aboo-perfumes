"""
Main FastAPI Application for Aboo Perfume Sommelier.
Implements the 3-step User Flow, anti-hallucination validation, and OpenAPI documentation.
"""

from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.models.perfume import Perfume, PerfumeSearchResponse
from app.models.interview import InterviewStartRequest, InterviewStartResponse, UserAnswer
from app.models.recommendation import RecommendationRequest, Top10Response
from app.services.catalog_service import catalog_service
from app.services.sommelier_service import sommelier_service

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Интеллектуальный веб-сервис «Парфюмерный Сомелье» (FastAPI + LLM).
    
    User Flow:
    1. Инициализация (Ввод прошлого любимого парфюма, валидация по базе, подтягивание нот и семейства).
    2. Интервью (Генерация ровно 3 точечных вопросов сомелье для уточнения предпочтений).
    3. Финальный подбор (Формирование ТОП-10 реальных ароматов со строгой анти-галлюцинационной валидацией).
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local and web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files path
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the luxury Sommelier frontend interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Aboo Perfume Sommelier API is online. Visit /docs for OpenAPI documentation."}


@app.get("/api/health", tags=["System"])
async def health_check():
    """Service health and catalog status check."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "catalog_size": len(catalog_service.get_all()),
        "llm_provider": settings.llm_provider
    }


@app.get("/api/perfumes/search", response_model=PerfumeSearchResponse, tags=["Catalog"])
async def search_perfumes(
    q: str = Query(..., min_length=2, description="Search query in Russian or English (e.g. 'Tom Ford', 'Lost Cherry', 'бакара')"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Search real perfumes in the verified catalog with fuzzy/alias matching.
    """
    results = catalog_service.search(q, limit=limit)
    return PerfumeSearchResponse(
        query=q,
        count=len(results),
        results=results
    )


@app.get("/api/perfumes/{perfume_id}", response_model=Perfume, tags=["Catalog"])
async def get_perfume_by_id(perfume_id: str):
    """Retrieve full details of a specific perfume by its slug ID."""
    perfume = catalog_service.get_by_id(perfume_id)
    if not perfume:
        raise HTTPException(status_code=404, detail=f"Perfume '{perfume_id}' not found in catalog.")
    return perfume


@app.post("/api/sommelier/start", response_model=InterviewStartResponse, tags=["Sommelier Flow"])
async def start_sommelier_interview(
    request: InterviewStartRequest,
    x_llm_provider: Optional[str] = Header(None, description="Optional custom LLM provider override"),
    x_api_key: Optional[str] = Header(None, description="Optional custom API key override")
):
    """
    Шаг 1 & Шаг 2:
    - Принимает название прошлого любимого парфюма пользователя.
    - Проверяет по каталогу существование аромата, подтягивает его ноты и семейство.
    - Генерирует ровно 3 точечных вопроса для уточнения предпочтений.
    - Возвращает session_id, данные найденного аромата и 3 вопроса.
    """
    try:
        response = await sommelier_service.start_interview(
            perfume_name=request.perfume_name,
            custom_provider=x_llm_provider,
            custom_key=x_api_key
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")


@app.post("/api/sommelier/recommend", response_model=Top10Response, tags=["Sommelier Flow"])
async def get_top10_recommendations(
    request: RecommendationRequest,
    x_llm_provider: Optional[str] = Header(None, description="Optional custom LLM provider override"),
    x_api_key: Optional[str] = Header(None, description="Optional custom API key override")
):
    """
    Шаг 3: Финальный подбор (ТОП-10)
    - Принимает session_id и ответы пользователя на 3 вопроса.
    - Формирует список из 10 реальных ароматов.
    - Строгое требование: Каждый элемент выдачи проходит валидацию по базе данных (никаких выдуманных брендов).
    - Ранжирован от точного попадания к смелым альтернативам.
    """
    if request.session_id:
        try:
            return await sommelier_service.get_recommendations_for_session(
                session_id=request.session_id,
                answers=request.answers,
                custom_provider=x_llm_provider,
                custom_key=x_api_key
            )
        except KeyError as ke:
            raise HTTPException(status_code=404, detail=str(ke))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

    elif request.perfume_name:
        try:
            return await sommelier_service.direct_recommend(
                perfume_name=request.perfume_name,
                answers=request.answers,
                custom_provider=x_llm_provider,
                custom_key=x_api_key
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail="Either 'session_id' or 'perfume_name' must be provided.")


@app.get("/api/sommelier/session/{session_id}", tags=["Sommelier Flow"])
async def get_session_info(session_id: str):
    """Retrieve details and state of an existing sommelier interview session."""
    session = sommelier_service.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "session_id": session.session_id,
        "perfume": session.perfume,
        "analysis": session.analysis,
        "questions": session.questions,
        "answers": session.answers,
        "has_recommendations": session.recommendations is not None
    }
