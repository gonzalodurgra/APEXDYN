"""Esquemas Pydantic para Fabricantes (Manufacturer)."""

import uuid
from typing import Optional
from pydantic import Field
from app.schemas.common import AppBaseModel


class ManufacturerBase(AppBaseModel):
    name: str = Field(..., max_length=120, description="Nombre oficial del fabricante")
    country_code: Optional[str] = Field(None, max_length=2, description="Código ISO alfa-2 (ej: DE, JP, IT)")
    website: Optional[str] = Field(None, max_length=300, description="Sitio web oficial")
    notes: Optional[str] = Field(None, description="Notas históricas o técnicas")


class ManufacturerCreate(ManufacturerBase):
    pass


class ManufacturerUpdate(AppBaseModel):
    name: Optional[str] = Field(None, max_length=120)
    country_code: Optional[str] = Field(None, max_length=2)
    website: Optional[str] = Field(None, max_length=300)
    notes: Optional[str] = None


class ManufacturerResponse(ManufacturerBase):
    id: uuid.UUID
