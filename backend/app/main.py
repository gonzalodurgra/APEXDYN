"""Aplicación FastAPI principal con soporte de CORS, OpenAPI y ciclo de vida."""

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.security import verify_token
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verificación de conexión en arranque
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield
    # Limpieza en apagado
    engine.dispose()


# docs_url=None y redoc_url=None para proteger las rutas manualmente con JWT
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=None,  # Protegido manualmente
    docs_url=None,     # Protegido manualmente
    redoc_url=None,    # Protegido manualmente
    lifespan=lifespan,
)

# Incluir rutas API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Configuración de CORS para cliente Angular
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def authenticate_docs_request(request: Request) -> dict:
    """
    Verifica JWT desde Header 'Authorization: Bearer <token>'
    o desde parámetro URL '?token=<token>' (para abrir Swagger cómodamente en navegador).
    """
    token: Optional[str] = None
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    elif "token" in request.query_params:
        token = request.query_params["token"]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticación JWT para acceder a la documentación. Usa el header 'Authorization: Bearer <token>' o el parámetro '?token=<token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(token)


@app.get(f"{settings.API_V1_STR}/openapi.json", include_in_schema=False)
@app.get("/openapi.json", include_in_schema=False)
def get_protected_openapi(user: dict = Depends(authenticate_docs_request)):
    """Esquema OpenAPI protegido con JWT."""
    return JSONResponse(app.openapi())


@app.get(f"{settings.API_V1_STR}/docs", include_in_schema=False)
@app.get("/docs", include_in_schema=False)
def get_protected_swagger_ui(request: Request, user: dict = Depends(authenticate_docs_request)):
    """Documentación Swagger UI protegida con JWT."""
    openapi_url = f"/openapi.json?token={request.query_params.get('token', '')}" if 'token' in request.query_params else "/openapi.json"
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title=f"{settings.PROJECT_NAME} - Swagger UI",
    )


@app.get(f"{settings.API_V1_STR}/redoc", include_in_schema=False)
@app.get("/redoc", include_in_schema=False)
def get_protected_redoc(request: Request, user: dict = Depends(authenticate_docs_request)):
    """Documentación ReDoc protegida con JWT."""
    openapi_url = f"/openapi.json?token={request.query_params.get('token', '')}" if 'token' in request.query_params else "/openapi.json"
    return get_redoc_html(
        openapi_url=openapi_url,
        title=f"{settings.PROJECT_NAME} - ReDoc",
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
