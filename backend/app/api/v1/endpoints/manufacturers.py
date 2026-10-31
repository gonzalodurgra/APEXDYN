"""Rutas API REST para Fabricantes (Manufacturers)."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.manufacturer import (
    ManufacturerCreate,
    ManufacturerUpdate,
    ManufacturerResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.manufacturer_service import ManufacturerService

router = APIRouter(prefix="/manufacturers", tags=["Fabricantes"])


@router.get("", response_model=PaginatedResponse[ManufacturerResponse])
def list_manufacturers(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre de marca"),
    country_code: Optional[str] = Query(None, max_length=2, description="Filtro por país ISO 2"),
    db: Session = Depends(get_db),
):
    skip = (page - 1) * page_size
    items, total = ManufacturerService.list(
        db, skip=skip, limit=page_size, search=search, country_code=country_code
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=ManufacturerResponse, status_code=status.HTTP_201_CREATED)
def create_manufacturer(
    data: ManufacturerCreate,
    db: Session = Depends(get_db),
):
    existing = ManufacturerService.get_by_name(db, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El fabricante '{data.name}' ya está registrado.",
        )
    return ManufacturerService.create(db, data)


@router.get("/{manufacturer_id}", response_model=ManufacturerResponse)
def get_manufacturer(
    manufacturer_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    manufacturer = ManufacturerService.get_by_id(db, manufacturer_id)
    if not manufacturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fabricante con ID {manufacturer_id} no encontrado.",
        )
    return manufacturer


@router.put("/{manufacturer_id}", response_model=ManufacturerResponse)
def update_manufacturer(
    manufacturer_id: uuid.UUID,
    data: ManufacturerUpdate,
    db: Session = Depends(get_db),
):
    manufacturer = ManufacturerService.get_by_id(db, manufacturer_id)
    if not manufacturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fabricante con ID {manufacturer_id} no encontrado.",
        )
    return ManufacturerService.update(db, manufacturer, data)


@router.delete("/{manufacturer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manufacturer(
    manufacturer_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    manufacturer = ManufacturerService.get_by_id(db, manufacturer_id)
    if not manufacturer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fabricante con ID {manufacturer_id} no encontrado.",
        )
    ManufacturerService.delete(db, manufacturer)
    return None
