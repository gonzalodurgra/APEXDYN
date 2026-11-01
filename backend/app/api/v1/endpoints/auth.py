"""Router de autenticación para obtener JWT."""

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status
from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class TokenRequest(BaseModel):
    api_key: str = Field(..., description="Clave de acceso de administración definida en DOCS_API_KEY")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


@router.post("/token", response_model=TokenResponse)
def login_for_token(payload: TokenRequest):
    """
    Genera un token JWT si la api_key coincide con la variable de entorno DOCS_API_KEY.
    """
    if payload.api_key != settings.DOCS_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave de API inválida",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": "admin", "scope": "docs"})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

