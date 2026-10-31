"""Rutas API REST para Vehículos de Serie (Vehicles)."""

import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleListItem,
    VehicleDetailResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.vehicle_service import VehicleService
from app.services.manufacturer_service import ManufacturerService

router = APIRouter(prefix="/vehicles", tags=["Vehículos"])

# Directorio donde se almacenan las imágenes (compatible con Vercel Serverless /tmp)
import os
if os.environ.get("VERCEL"):
    IMAGES_DIR = Path("/tmp/vehicle_images")
else:
    IMAGES_DIR = Path(__file__).resolve().parents[5] / "static" / "vehicle_images"

try:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

# URL base pública con la que el frontend accede a las imágenes
IMAGES_BASE_URL = "http://localhost:8000/static/vehicle_images"


@router.get("", response_model=PaginatedResponse[VehicleDetailResponse])
def list_vehicles(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    manufacturer_id: Optional[uuid.UUID] = Query(None, description="Filtro por fabricante"),
    search: Optional[str] = Query(None, description="Búsqueda por modelo, variante o generación"),
    drive_type: Optional[str] = Query(None, description="FWD, RWD, AWD"),
    min_year: Optional[int] = Query(None, description="Año mínimo"),
    max_year: Optional[int] = Query(None, description="Año máximo"),
    min_power_kw: Optional[float] = Query(None, description="Potencia mínima en kW"),
    max_mass_kg: Optional[float] = Query(None, description="Masa máxima en kg"),
    db: Session = Depends(get_db),
):
    skip = (page - 1) * page_size
    items, total = VehicleService.list_detailed(
        db,
        skip=skip,
        limit=page_size,
        manufacturer_id=manufacturer_id,
        model_search=search,
        drive_type=drive_type,
        min_year=min_year,
        max_year=max_year,
        min_power_kw=min_power_kw,
        max_mass_kg=max_mass_kg,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
    



@router.post("", response_model=VehicleDetailResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    data: VehicleCreate,
    db: Session = Depends(get_db),
):
    # Validar que el fabricante existe
    mfg = ManufacturerService.get_by_id(db, data.manufacturer_id)
    if not mfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fabricante con ID {data.manufacturer_id} no existe.",
        )
    return VehicleService.create(db, data)


@router.get("/{vehicle_id}", response_model=VehicleDetailResponse)
def get_vehicle(
    vehicle_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    vehicle = VehicleService.get_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehículo con ID {vehicle_id} no encontrado.",
        )
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleDetailResponse)
def update_vehicle(
    vehicle_id: uuid.UUID,
    data: VehicleUpdate,
    db: Session = Depends(get_db),
):
    vehicle = VehicleService.get_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehículo con ID {vehicle_id} no encontrado.",
        )
    if data.manufacturer_id:
        mfg = ManufacturerService.get_by_id(db, data.manufacturer_id)
        if not mfg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fabricante con ID {data.manufacturer_id} no existe.",
            )
    return VehicleService.update(db, vehicle, data)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    vehicle = VehicleService.get_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehículo con ID {vehicle_id} no encontrado.",
        )
    VehicleService.delete(db, vehicle)
    return None


@router.post("/{vehicle_id}/image", response_model=VehicleDetailResponse)
def upload_vehicle_image(
    vehicle_id: uuid.UUID,
    image: UploadFile = File(..., description="Imagen del vehículo (jpg, png, webp)"),
    db: Session = Depends(get_db),
):
    """Sube una imagen para el vehículo y guarda su URL pública en la base de datos."""
    vehicle = VehicleService.get_by_id(db, vehicle_id)
    vehicle_manufacturer = vehicle.manufacturer.name.replace(" ", "_")
    vehicle_model = vehicle.model.replace(" ", "_")
    vehicle_variant = vehicle.variant.replace(" ", "_")
    vehicle_generation = vehicle.generation.replace(" ", "_")
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehículo con ID {vehicle_id} no encontrado.",
        )

    # Validar extensión
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    suffix = Path(image.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no soportado '{suffix}'. Usa jpg, png o webp.",
        )

    # Guardar con nombre único basado en el ID del vehículo
    filename = f"{vehicle_manufacturer}_{vehicle_model}_{vehicle_variant}_{vehicle_generation}{suffix}"
    dest = IMAGES_DIR / filename
    with dest.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Actualizar image_url en BD
    from app.schemas.vehicle import VehicleUpdate as VU
    update = VU(image_url=f"{IMAGES_BASE_URL}/{filename}")
    return VehicleService.update(db, vehicle, update)

