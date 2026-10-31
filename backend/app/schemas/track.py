"""Esquemas Pydantic para Circuitos, Variantes, Geometría, Perfiles de Elevación y Superficies."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pydantic import Field, field_validator
from app.schemas.common import AppBaseModel


# --- PUNTOS DE GEOMETRÍA ---
class TrackGeometryPointBase(AppBaseModel):
    sequence: int = Field(..., ge=0, description="Índice secuencial de posición a lo largo del trazado")
    distance_m: float = Field(..., ge=0, description="Distancia acumulada desde la línea de salida/meta")
    longitude: float = Field(..., ge=-180, le=180, description="Longitud geográfica WGS84")
    latitude: float = Field(..., ge=-90, le=90, description="Latitud geográfica WGS84")
    x_m: Optional[float] = Field(None, description="Coordenada métrica proyectada X (Este)")
    y_m: Optional[float] = Field(None, description="Coordenada métrica proyectada Y (Norte)")
    elevation_m: Optional[float] = Field(None, description="Altitud sobre el nivel del mar en metros")
    horizontal_accuracy_m: Optional[float] = None
    vertical_accuracy_m: Optional[float] = None
    source: Optional[str] = None


class TrackGeometryPointCreate(AppBaseModel):
    sequence: Optional[int] = None
    longitude: float
    latitude: float
    elevation_m: Optional[float] = None


class TrackGeometryPointResponse(TrackGeometryPointBase):
    id: int
    variant_id: uuid.UUID


# --- PUNTOS DE ELEVACIÓN Y PENDIENTE ---
class ElevationPointBase(AppBaseModel):
    distance_m: float = Field(..., ge=0)
    elevation_m: float
    grade_percent: Optional[float] = Field(None, description="Pendiente longitudinal en porcentaje (+ subida, - bajada)")
    cross_slope_percent: Optional[float] = Field(None, description="Peralte transversal en porcentaje")
    source: Optional[str] = None


class ElevationPointResponse(ElevationPointBase):
    id: int
    variant_id: uuid.UUID


# --- MODELOS DE FRICCIÓN Y SEGMENTOS DE SUPERFICIE ---
class FrictionModelBase(AppBaseModel):
    name: str = Field(..., max_length=120)
    model_type: str = Field("constant", max_length=60, description="constant, lookup, Pacejka, surface_decay")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="mu_nominal, sensitivity, slip_limits...")
    source: Optional[str] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None


class FrictionModelCreate(FrictionModelBase):
    pass


class FrictionModelResponse(FrictionModelBase):
    id: uuid.UUID


class SurfaceSegmentBase(AppBaseModel):
    start_distance_m: float = Field(..., ge=0)
    end_distance_m: float = Field(..., gt=0)
    surface_type: str = Field(..., max_length=60, description="asphalt, coarse_asphalt, smooth_asphalt, gravel, mud, snow, wet_asphalt")
    roughness_index: Optional[float] = Field(None, description="Índice de irregularidad/rugosidad (IRI)")
    loose_gravel_depth_mm: Optional[float] = Field(None, ge=0)
    wetness: Optional[float] = Field(None, ge=0, le=1.0, description="Nivel de humedad (0=seco, 1=encharcado)")
    friction_model_id: Optional[uuid.UUID] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class SurfaceSegmentCreate(SurfaceSegmentBase):
    variant_id: uuid.UUID


class SurfaceSegmentResponse(SurfaceSegmentBase):
    id: uuid.UUID
    variant_id: uuid.UUID
    friction_model: Optional[FrictionModelResponse] = None


# --- CONDICIONES METEOROLÓGICAS DE SESIÓN ---
class TrackConditionBase(AppBaseModel):
    recorded_at: Optional[datetime] = None
    air_temperature_c: Optional[float] = Field(None, description="Temperatura ambiente en °C")
    surface_temperature_c: Optional[float] = Field(None, description="Temperatura del asfalto o pista en °C")
    wetness: Optional[float] = Field(None, ge=0.0, le=1.0)
    rainfall_mm_h: Optional[float] = Field(None, ge=0.0)
    wind_speed_m_s: Optional[float] = Field(None, ge=0.0)
    wind_direction_deg: Optional[float] = Field(None, ge=0.0, le=360.0)
    surface_condition: Optional[str] = Field(None, max_length=60, description="dry, damp, wet, standing_water, ice")
    source: Optional[str] = None


class TrackConditionCreate(TrackConditionBase):
    variant_id: uuid.UUID


class TrackConditionResponse(TrackConditionBase):
    id: uuid.UUID
    variant_id: uuid.UUID


# --- VARIANTES DE TRAZADO ---
class TrackVariantBase(AppBaseModel):
    name: str = Field("Principal", max_length=160, description="Nombre de configuración (ej: GP, Nacional, Club, Tramo Shakedown)")
    direction: str = Field("forward", max_length=30, description="forward, reverse, clockwise, counter_clockwise")
    is_closed_loop: bool = Field(True, description="True para circuito cerrado, False para tramo de rally abierto A -> B")
    length_m: Optional[float] = Field(None, gt=0)
    geometry_source: Optional[str] = None
    geometry_accuracy_m: Optional[float] = None
    sampling_interval_m: Optional[float] = None
    processing_method: Optional[str] = None
    version_number: int = Field(1, ge=1)
    quality_status: str = Field("provisional", max_length=30, description="provisional, validated, telemetry_calibrated")


class TrackVariantCreate(TrackVariantBase):
    track_id: uuid.UUID
    raw_points: Optional[List[TrackGeometryPointCreate]] = None


class TrackVariantResponse(TrackVariantBase):
    id: uuid.UUID
    track_id: uuid.UUID
    points_count: int = 0
    surface_segments: List[SurfaceSegmentResponse] = []


class TrackVariantDetailResponse(TrackVariantBase):
    id: uuid.UUID
    track_id: uuid.UUID
    points: List[TrackGeometryPointResponse] = []
    elevation_profile: List[ElevationPointResponse] = []
    surface_segments: List[SurfaceSegmentResponse] = []


# --- CIRCUITOS Y TRAMOS PRINCIPALES ---
class TrackBase(AppBaseModel):
    name: str = Field(..., max_length=200, description="Nombre oficial del circuito o tramo (ej: Nürburgring Nordschleife, Col de Turini)")
    track_type: str = Field(..., max_length=30, description="CIRCUIT, RALLY_STAGE, HILLCLIMB")
    country_code: Optional[str] = Field(None, max_length=2)
    region: Optional[str] = Field(None, max_length=120)
    official_length_m: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    website: Optional[str] = Field(None, max_length=500)
    is_public_road: bool = Field(False, description="Indica si es carretera abierta al tráfico o circuito permanente")


class TrackCreate(TrackBase):
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    variants: Optional[List[TrackVariantCreate]] = None


class TrackUpdate(AppBaseModel):
    name: Optional[str] = None
    track_type: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    official_length_m: Optional[float] = None
    description: Optional[str] = None
    website: Optional[str] = None
    is_public_road: Optional[bool] = None


class TrackListItem(TrackBase):
    id: uuid.UUID
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    variants_count: int = 0
    created_at: datetime


class TrackDetailResponse(TrackBase):
    id: uuid.UUID
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    variants: List[TrackVariantResponse] = []
