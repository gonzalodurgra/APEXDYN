"""Esquemas base reutilizables, paginación y respuestas estándar."""

from typing import Generic, List, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class AppBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(AppBaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
