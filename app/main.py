"""
Main FastAPI Application for Aboo Perfume Sommelier.
Implements the 3-step User Flow, anti-hallucination validation, and OpenAPI documentation.
"""

import logging
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Header, Query

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response

from app.config import settings
from app.models.perfume import Perfume, PerfumeSearchResponse
from app.models.interview import InterviewStartRequest, InterviewStartResponse, UserAnswer
from app.models.recommendation import RecommendationRequest, Top10Response
from app.services.catalog_service import catalog_service
from app.services.sommelier_service import sommelier_service
from app.services.image_service import generate_perfume_svg_badge

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


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_index():
    """Serves the luxury Sommelier frontend interface with no-cache headers."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(
            index_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
    return {"message": "Aboo Perfume Sommelier API is online. Visit /docs for OpenAPI documentation."}


@app.get("/manifest.json", include_in_schema=False)
async def serve_manifest():
    manifest_file = STATIC_DIR / "manifest.json"
    if manifest_file.exists():
        return FileResponse(manifest_file, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="manifest.json not found")


@app.get("/sw.js", include_in_schema=False)
async def serve_service_worker():
    sw_file = STATIC_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(sw_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="sw.js not found")


@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    icon_file = STATIC_DIR / "images" / "pwa-icon.svg"
    if icon_file.exists():
        return FileResponse(icon_file, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="favicon not found")


@app.get("/apple-touch-icon.png", include_in_schema=False)
async def serve_apple_touch_icon():
    icon_file = STATIC_DIR / "images" / "apple-touch-icon.png"
    if icon_file.exists():
        return FileResponse(icon_file, media_type="image/png")
    raise HTTPException(status_code=404, detail="apple-touch-icon not found")


@app.get("/api/health", tags=["System"])
async def health_check():
    """Service health and catalog status check."""
    from app.services.external_api import scentrev_client
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "catalog_size": len(catalog_service.get_all()),
        "scentrev_connected": scentrev_client.is_configured,
        "llm_provider": settings.llm_provider
    }


@app.get("/api/perfumes/search", response_model=PerfumeSearchResponse, tags=["Catalog"])
async def search_perfumes(
    q: str = Query(..., min_length=2, description="Search query in Russian or English (e.g. 'Tom Ford', 'Lost Cherry', 'бакара')"),
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None, description="Optional gender category filter: 'Мужской', 'Женский', 'Унисекс'")
):
    """
    Search real perfumes in the official ScentRev / Scento catalog (130,000+ items),
    with local cached database fallback, category boosting and Russian/English alias matching.
    """
    results = await catalog_service.async_search(q, limit=limit)
    if category and category in ("Мужской", "Женский"):
        allowed = {category, "Унисекс"}
        # Prioritize matching category
        results = sorted(results, key=lambda r: (r.perfume.gender in allowed, r.score), reverse=True)

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


@app.get("/api/perfumes/{perfume_id}/badge.svg", tags=["Catalog"])
async def get_perfume_badge_svg(perfume_id: str):
    """
    Dynamically renders an authentic, vector SVG luxury flacon badge for the perfume,
    with colors and atmosphere tailored to the perfume's olfactory family.
    """
    perfume = catalog_service.get_by_id(perfume_id)
    if perfume:
        svg_content = generate_perfume_svg_badge(
            perfume_id=perfume.id,
            brand=perfume.brand,
            name=perfume.name,
            family=perfume.family
        )
    else:
        # Fallback for dynamic/unknown slug
        brand_guess = perfume_id.split("-")[0].title() if "-" in perfume_id else "Aboo"
        name_guess = " ".join(perfume_id.split("-")[1:]).title() if "-" in perfume_id else perfume_id.title()
        svg_content = generate_perfume_svg_badge(
            perfume_id=perfume_id,
            brand=brand_guess,
            name=name_guess,
            family="Нишевая парфюмерия"
        )
    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Type": "image/svg+xml; charset=utf-8"
        }
    )


@app.post("/api/sommelier/start", response_model=InterviewStartResponse, tags=["Sommelier Flow"])
async def start_sommelier_interview(
    request: InterviewStartRequest,
    x_llm_provider: Optional[str] = Header(None, description="Optional custom LLM provider override"),
    x_api_key: Optional[str] = Header(None, description="Optional custom API key override")
):
    """
    Шаг 0, 1 & 2:
    - Принимает категорию (Мужской/Женский/Унисекс) и название прошлого любимого парфюма.
    - Проверяет по каталогу Scento существование аромата, подтягивает его ноты и семейство.
    - Генерирует ровно 5 интеллектуальных вопросов для калибровки предпочтений:
      1. Контекст и стиль жизни
      2. Шлейф и интимность
      3. Температура, плотность и характер нот
      4. Парфюмерные антипатии
      5. Степень ольфакторной смелости
    - Возвращает session_id, данные найденного аромата, категорию и 5 вопросов.
    """
    category = request.category or request.gender or "Унисекс"
    try:
        response = await sommelier_service.start_interview(
            perfume_name=request.perfume_name,
            category=category,
            custom_provider=x_llm_provider,
            custom_key=x_api_key
        )
        return response
    except Exception as e:
        logger.exception("Failed to start interview:")
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")


@app.post("/api/sommelier/recommend", response_model=Top10Response, tags=["Sommelier Flow"])
async def get_top10_recommendations(
    request: RecommendationRequest,
    x_llm_provider: Optional[str] = Header(None, description="Optional custom LLM provider override"),
    x_api_key: Optional[str] = Header(None, description="Optional custom API key override")
):
    """
    Шаг 3: Цепочка рассуждений (Chain-of-Thought) и выдача ТОП-10
    - Принимает session_id и ответы пользователя на 5 вопросов сомелье.
    - Активирует режим глубокого анализа Chain-of-Thought от лица Главного сомелье ABOO PERFUMES.
    - Сопоставляет параметры через Scento API и формирует ранжированный список из 10 реальных ароматов:
      позиции 1–3 (точные попадания), 4–7 (вариации), 8–10 (смелая ниша).
    - Строгое требование: Каждый элемент выдачи проходит валидацию по базе данных.
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
            logger.exception("Recommendation error in session flow:")
            raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

    elif request.perfume_name:
        category = request.category or request.gender or "Унисекс"
        try:
            return await sommelier_service.direct_recommend(
                perfume_name=request.perfume_name,
                answers=request.answers,
                category=category,
                custom_provider=x_llm_provider,
                custom_key=x_api_key
            )
        except Exception as e:
            logger.exception("Recommendation error in direct flow:")
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
