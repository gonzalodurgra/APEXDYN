"""Configuración global de la aplicación usando Pydantic Settings."""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Simulador y Catálogo de Rendimiento de Vehículos de Serie"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

    # Configuración de S3 / Neon Object Storage
    AWS_ENDPOINT_URL_S3: Optional[str] = os.getenv("AWS_ENDPOINT_URL_S3")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "vehicle-images")

    # Configuración JWT y Acceso Seguro
    DOCS_API_KEY: str = os.getenv("DOCS_API_KEY")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))  # 24 horas por defecto

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
