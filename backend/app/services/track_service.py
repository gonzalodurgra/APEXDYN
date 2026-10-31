"""Capa de servicios CRUD y procesamiento geométrico para Circuitos y Variantes."""

import uuid
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, and_
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point, LineString

from app.models.track import (
    Track,
    TrackVariant,
    TrackGeometryPoint,
    ElevationPoint,
    SurfaceSegment,
    FrictionModel,
    TrackCondition,
)
from app.schemas.track import (
    TrackCreate,
    TrackUpdate,
    TrackVariantCreate,
    SurfaceSegmentCreate,
    TrackConditionCreate,
    TrackGeometryPointCreate,
)
from app.simulation.track_processing import (
    wgs84_to_local_enu,
    filter_gps_noise,
    calculate_track_derivatives,
)


class TrackService:
    @staticmethod
    def get_by_id(db: Session, track_id: uuid.UUID) -> Optional[Track]:
        return db.execute(
            select(Track)
            .where(Track.id == track_id)
            .options(
                selectinload(Track.variants).selectinload(TrackVariant.surface_segments)
            )
        ).scalar_one_or_none()

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        track_type: Optional[str] = None,
        country_code: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Track], int]:
        query = select(Track).options(selectinload(Track.variants))
        count_query = select(func.count(Track.id))

        conditions = []
        if track_type:
            conditions.append(Track.track_type == track_type.upper())
        if country_code:
            conditions.append(Track.country_code == country_code.upper())
        if search:
            search_str = f"%{search}%"
            conditions.append(
                (Track.name.ilike(search_str)) |
                (Track.region.ilike(search_str))
            )

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total = db.execute(count_query).scalar_one()
        items = db.execute(
            query.order_by(Track.name.asc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        return list(items), total

    @staticmethod
    def create(db: Session, data: TrackCreate) -> Track:
        location_geom = None
        if data.latitude is not None and data.longitude is not None:
            location_geom = f"SRID=4326;POINT({data.longitude} {data.latitude})"

        track_dict = data.model_dump(exclude={"latitude", "longitude", "variants"})
        track = Track(**track_dict, location=location_geom)
        db.add(track)
        db.flush()

        if data.variants:
            for v_data in data.variants:
                TrackService.create_variant(db, track.id, v_data)

        db.commit()
        return TrackService.get_by_id(db, track.id)

    @staticmethod
    def update(db: Session, track: Track, data: TrackUpdate) -> Track:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(track, field, value)
        db.commit()
        return TrackService.get_by_id(db, track.id)

    @staticmethod
    def delete(db: Session, track: Track) -> None:
        db.delete(track)
        db.commit()

    # --- VARIANTES Y PROCESAMIENTO GEOMÉTRICO ---
    @staticmethod
    def get_variant_by_id(db: Session, variant_id: uuid.UUID) -> Optional[TrackVariant]:
        return db.execute(
            select(TrackVariant)
            .where(TrackVariant.id == variant_id)
            .options(
                selectinload(TrackVariant.points),
                selectinload(TrackVariant.elevation_profile),
                selectinload(TrackVariant.surface_segments),
            )
        ).scalar_one_or_none()

    @staticmethod
    def create_variant(
        db: Session,
        track_id: uuid.UUID,
        data: TrackVariantCreate,
    ) -> TrackVariant:
        variant = TrackVariant(
            track_id=track_id,
            name=data.name,
            direction=data.direction,
            is_closed_loop=data.is_closed_loop,
            length_m=data.length_m,
            version_number=data.version_number,
            quality_status=data.quality_status,
            geometry_source=data.geometry_source,
        )
        db.add(variant)
        db.flush()

        if data.raw_points and len(data.raw_points) >= 2:
            TrackService.import_and_process_track_geometry(db, variant.id, data.raw_points, is_closed=data.is_closed_loop)

        db.commit()
        return TrackService.get_variant_by_id(db, variant.id)

    @staticmethod
    def import_and_process_track_geometry(
        db: Session,
        variant_id: uuid.UUID,
        raw_points: List[TrackGeometryPointCreate],
        is_closed: bool = True,
    ) -> Dict[str, Any]:
        """Importa puntos crudos GPS, filtra el ruido, calcula curvaturas, pendientes,

        genera la línea central PostGIS y almacena los puntos geométricos y perfil de elevación.
        """
        variant = db.get(TrackVariant, variant_id)
        if not variant:
            raise ValueError(f"Variante {variant_id} no encontrada.")

        coords_input = [
            (p.longitude, p.latitude, p.elevation_m if p.elevation_m is not None else 0.0)
            for p in raw_points
        ]

        # 1. Conversión de coordenadas GPS a plano métrico local
        enu_raw, origin = wgs84_to_local_enu(coords_input)

        # 2. Filtrado de ruido GPS con Savitzky-Golay
        enu_filtered = filter_gps_noise(enu_raw, window_length=7, polyorder=2)

        # 3. Derivadas numéricas, curvatura y distancias acumuladas
        derivatives = calculate_track_derivatives(enu_filtered, is_closed_loop=is_closed)
        s_dist = derivatives["distance_m"]
        grades = derivatives["grade_percent"]
        total_length_m = float(s_dist[-1])

        # 4. Actualizar longitud calculada y línea central en TrackVariant
        line_coords = [(p.longitude, p.latitude) for p in raw_points]
        if is_closed and line_coords[0] != line_coords[-1]:
            line_coords.append(line_coords[0])
        linestring = LineString(line_coords)
        variant.centerline = f"SRID=4326;{linestring.wkt}"
        variant.length_m = total_length_m
        variant.processing_method = "Savitzky-Golay (w=7, p=2) + Local ENU metric projection"
        variant.quality_status = "validated"

        # 5. Eliminar puntos antiguos si existían
        existing_pts = db.execute(select(TrackGeometryPoint).where(TrackGeometryPoint.variant_id == variant_id)).scalars().all()
        for ep in existing_pts:
            db.delete(ep)
        existing_elev = db.execute(select(ElevationPoint).where(ElevationPoint.variant_id == variant_id)).scalars().all()
        for ee in existing_elev:
            db.delete(ee)
        db.flush()

        # 6. Guardar puntos de geometría procesados
        for idx, (p, s, enu, grade) in enumerate(zip(raw_points, s_dist, enu_filtered, grades)):
            geom_wkt = f"SRID=4326;POINT({p.longitude} {p.latitude})"
            geom_pt = TrackGeometryPoint(
                variant_id=variant_id,
                sequence=idx + 1,
                distance_m=float(s),
                geom=geom_wkt,
                longitude=float(p.longitude),
                latitude=float(p.latitude),
                x_m=float(enu[0]),
                y_m=float(enu[1]),
                elevation_m=float(p.elevation_m if p.elevation_m is not None else 0.0),
                source="GPS filtered",
            )
            db.add(geom_pt)

            elev_pt = ElevationPoint(
                variant_id=variant_id,
                distance_m=float(s),
                elevation_m=float(p.elevation_m if p.elevation_m is not None else 0.0),
                grade_percent=float(grade),
            )
            db.add(elev_pt)

        db.commit()
        return {
            "variant_id": variant_id,
            "total_points": len(raw_points),
            "calculated_length_m": total_length_m,
            "max_grade_percent": float(np.max(np.abs(grades))),
            "min_radius_m": float(np.min(derivatives["radius_m"])),
        }

    # --- SUPERFICIES Y CONDICIONES ---
    @staticmethod
    def add_surface_segment(db: Session, data: SurfaceSegmentCreate) -> SurfaceSegment:
        segment = SurfaceSegment(**data.model_dump())
        db.add(segment)
        db.commit()
        db.refresh(segment)
        return segment

    @staticmethod
    def add_track_condition(db: Session, data: TrackConditionCreate) -> TrackCondition:
        condition = TrackCondition(**data.model_dump())
        db.add(condition)
        db.commit()
        db.refresh(condition)
        return condition
