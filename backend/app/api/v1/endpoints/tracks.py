"""Rutas API REST para Circuitos, Tramos de Rally, Variantes y Geometría PostGIS."""

import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.track import (
    TrackCreate,
    TrackUpdate,
    TrackListItem,
    TrackDetailResponse,
    TrackVariantCreate,
    TrackVariantResponse,
    TrackVariantDetailResponse,
    TrackGeometryPointCreate,
    SurfaceSegmentCreate,
    SurfaceSegmentResponse,
    TrackConditionCreate,
    TrackConditionResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.track_service import TrackService

router = APIRouter(prefix="/tracks", tags=["Circuitos y Tramos"])


@router.get("", response_model=PaginatedResponse[TrackListItem])
def list_tracks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    track_type: Optional[str] = Query(None, description="CIRCUIT, RALLY_STAGE, HILLCLIMB"),
    country_code: Optional[str] = Query(None, max_length=2),
    search: Optional[str] = Query(None, description="Búsqueda por nombre o región"),
    db: Session = Depends(get_db),
):
    skip = (page - 1) * page_size
    items, total = TrackService.list(
        db,
        skip=skip,
        limit=page_size,
        track_type=track_type,
        country_code=country_code,
        search=search,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    list_items = []
    for t in items:
        lat = None
        lon = None
        # Si la geometría location está cargada, extraer punto
        list_items.append(
            TrackListItem(
                id=t.id,
                name=t.name,
                track_type=t.track_type,
                country_code=t.country_code,
                region=t.region,
                official_length_m=t.official_length_m,
                description=t.description,
                website=t.website,
                is_public_road=t.is_public_road,
                variants_count=len(t.variants),
                latitude=lat,
                longitude=lon,
                created_at=t.created_at,
            )
        )

    return PaginatedResponse(
        items=list_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=TrackDetailResponse, status_code=status.HTTP_201_CREATED)
def create_track(data: TrackCreate, db: Session = Depends(get_db)):
    track = TrackService.create(db, data)
    return track


@router.get("/{track_id}", response_model=TrackDetailResponse)
def get_track(track_id: uuid.UUID, db: Session = Depends(get_db)):
    track = TrackService.get_by_id(db, track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trazado con ID {track_id} no encontrado.",
        )
    return track


@router.put("/{track_id}", response_model=TrackDetailResponse)
def update_track(track_id: uuid.UUID, data: TrackUpdate, db: Session = Depends(get_db)):
    track = TrackService.get_by_id(db, track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trazado con ID {track_id} no encontrado.",
        )
    return TrackService.update(db, track, data)


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_track(track_id: uuid.UUID, db: Session = Depends(get_db)):
    track = TrackService.get_by_id(db, track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trazado con ID {track_id} no encontrado.",
        )
    TrackService.delete(db, track)
    return None

# --- VARIANTES Y GEOMETRÍA ---
@router.post("/{track_id}/variants", response_model=TrackVariantResponse, status_code=status.HTTP_201_CREATED)
def create_track_variant(
    track_id: uuid.UUID,
    data: TrackVariantCreate,
    db: Session = Depends(get_db),
):
    track = TrackService.get_by_id(db, track_id)
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trazado no encontrado.")
    return TrackService.create_variant(db, track_id, data)

@router.get("/{track_id}/variants", response_model=PaginatedResponse[TrackVariantDetailResponse])
def get_track_variants(track_id: uuid.UUID, db: Session = Depends(get_db)):
    track = TrackService.get_by_id(db, track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trazado con ID {track_id} no encontrado.",
        )
    return PaginatedResponse(
        items=track.variants,
        total=len(track.variants),
        page=1,
        page_size=len(track.variants),
        total_pages=1,
    )

@router.get("/variants/{variant_id}", response_model=TrackVariantDetailResponse)
def get_variant_detail(variant_id: uuid.UUID, db: Session = Depends(get_db)):
    variant = TrackService.get_variant_by_id(db, variant_id)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variante con ID {variant_id} no encontrada.",
        )
    return variant


@router.post("/variants/{variant_id}/import-geometry", response_model=Dict[str, Any])
def import_variant_geometry(
    variant_id: uuid.UUID,
    points: List[TrackGeometryPointCreate],
    is_closed: bool = Query(True, description="Indica si es un circuito cerrado o tramo abierto"),
    db: Session = Depends(get_db),
):
    if len(points) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requieren al menos 2 puntos GPS para procesar la geometría de un trazado.",
        )
    try:
        return TrackService.import_and_process_track_geometry(db, variant_id, points, is_closed=is_closed)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/variants/{variant_id}/surfaces", response_model=SurfaceSegmentResponse, status_code=status.HTTP_201_CREATED)
def add_surface_segment(
    variant_id: uuid.UUID,
    data: SurfaceSegmentCreate,
    db: Session = Depends(get_db),
):
    variant = TrackService.get_variant_by_id(db, variant_id)
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada.")
    return TrackService.add_surface_segment(db, data)


@router.post("/variants/{variant_id}/conditions", response_model=TrackConditionResponse, status_code=status.HTTP_201_CREATED)
def add_track_condition(
    variant_id: uuid.UUID,
    data: TrackConditionCreate,
    db: Session = Depends(get_db),
):
    variant = TrackService.get_variant_by_id(db, variant_id)
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada.")
    return TrackService.add_track_condition(db, data)
