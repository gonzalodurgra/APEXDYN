"""Aplicación FastAPI principal con soporte de CORS, OpenAPI y ciclo de vida."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.api.v1.api import api_router

# Directorio de imágenes estáticas (se crea si no existe)
# STATIC_DIR = Path(__file__).resolve().parents[2] / "static" / "vehicle_images"
# STATIC_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verificación de conexión en arranque
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield
    # Limpieza en apagado
    engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Incluir rutas API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Servir imágenes estáticas: GET /static/vehicle_images/<filename>
# app.mount("/static/vehicle_images", StaticFiles(directory=str(STATIC_DIR)), name="vehicle_images")

# Configuración de CORS para cliente Angular
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health", tags=["Salud"])
def health_check():
    """Endpoint de estado del servicio y base de datos con PostGIS."""
    with engine.connect() as conn:
        postgis_ver = conn.execute(text("SELECT postgis_version()")).scalar()
    return {
        "status": "healthy",
        "database": "connected",
        "postgis_version": postgis_ver,
    }
