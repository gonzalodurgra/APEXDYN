"""Esquemas Pydantic completos para la entidad Vehicle."""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import Field
from app.schemas.common import AppBaseModel
from app.schemas.manufacturer import ManufacturerResponse
from app.schemas.engine import EngineResponse, EngineCreate
from app.schemas.gearbox import GearboxResponse, GearboxCreate
from app.schemas.chassis import (
    SuspensionResponse,
    SuspensionCreate,
    AerodynamicsResponse,
    AerodynamicsCreate,
    TireSetupResponse,
    TireSetupCreate,
)


class VehicleBase(AppBaseModel):
    model: str = Field(..., max_length=120, description="Modelo de gama (ej: 911, M3, Civic)")
    generation: Optional[str] = Field(None, max_length=80, description="Generación del modelo (ej: 992, E46, FK8)")
    variant: Optional[str] = Field(None, max_length=120, description="Variante concreta (ej: GT3, Competition, Type R)")
    trim_level: Optional[str] = Field(None, max_length=120)
    model_year: Optional[int] = Field(None, ge=1900, le=2100)
    production_start_year: Optional[int] = Field(None, ge=1900, le=2100)
    production_end_year: Optional[int] = Field(None, ge=1900, le=2100)
    body_style: Optional[str] = Field(None, max_length=60, description="coupe, sedan, hatchback, roadster")
    market: Optional[str] = Field(None, max_length=80, description="EU, US, JDM, Global")
    country_of_origin: Optional[str] = Field(None, max_length=2)
    is_stock_specification: bool = Field(True, description="Indica si representa especificación de serie estricta")

    # Masas y dimensiones (SI)
    mass_kg: float = Field(..., gt=0, description="Masa del vehículo en kg")
    mass_definition: str = Field("kerb_weight", max_length=40, description="kerb_weight, curb_weight, DIN, EU, dry")
    front_mass_fraction: Optional[float] = Field(None, ge=0.1, le=0.9, description="Reparto de masa delante (ej: 0.52 = 52% delante)")
    wheelbase_m: float = Field(..., gt=0, description="Batalla o distancia entre ejes en metros")
    front_track_m: Optional[float] = Field(None, gt=0, description="Vía delantera en metros")
    rear_track_m: Optional[float] = Field(None, gt=0, description="Vía trasera en metros")
    length_m: Optional[float] = Field(None, gt=0)
    width_m: Optional[float] = Field(None, gt=0)
    height_m: Optional[float] = Field(None, gt=0)
    ground_clearance_m: Optional[float] = Field(None, gt=0)
    seats: Optional[int] = Field(None, ge=1, le=9)
    doors: Optional[int] = Field(None, ge=0, le=6)
    fuel_tank_capacity_l: Optional[float] = Field(None, gt=0, le=300, description="Capacidad del tanque de combustible en litros")
    # Defaults de estrategia de pit-stop intrínsecos al vehículo
    pit_fuel_fill_rate_l_s: Optional[float] = Field(None, le=10.0, description="Caudal de repostaje (L/s)")
    pit_tire_wear_threshold: Optional[float] = Field(None, ge=0.2, le=0.95, description="Umbral de desgaste de neumáticos para parada [0-1]")

    # Chasis, tracción y frenos
    drive_type: Optional[str] = Field(None, max_length=20, description="FWD, RWD, AWD, 4WD")
    differential_type: Optional[str] = Field(None, max_length=60, description="Open, Mechanical LSD, TorSen, Electronic torque vectoring")
    steering_type: Optional[str] = Field(None, max_length=80, description="Rack and pinion, EPS, Hydraulic")
    brake_front_type: Optional[str] = Field(None, max_length=80, description="Ventilated disc, Carbon ceramic, Solid disc")
    brake_rear_type: Optional[str] = Field(None, max_length=80)
    abs: Optional[bool] = None
    stability_control: Optional[bool] = None

    # Trazabilidad y fuentes
    source_url: Optional[str] = Field(None, max_length=1000)
    source_name: Optional[str] = Field(None, max_length=200)
    data_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nivel de confianza en los datos (0 a 1)")
    notes: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500, description="URL pública de la imagen del vehículo")


class VehicleCreate(VehicleBase):
    manufacturer_id: uuid.UUID
    # Posibilidad de crear subsistemas asociados en el mismo alta
    engine: Optional[EngineCreate] = None
    gearbox: Optional[GearboxCreate] = None
    suspension: Optional[SuspensionCreate] = None
    aerodynamics: Optional[AerodynamicsCreate] = None
    tires: Optional[List[TireSetupCreate]] = None


class VehicleUpdate(AppBaseModel):
    manufacturer_id: Optional[uuid.UUID] = None
    model: Optional[str] = None
    generation: Optional[str] = None
    variant: Optional[str] = None
    trim_level: Optional[str] = None
    model_year: Optional[int] = None
    production_start_year: Optional[int] = None
    production_end_year: Optional[int] = None
    body_style: Optional[str] = None
    market: Optional[str] = None
    country_of_origin: Optional[str] = None
    is_stock_specification: Optional[bool] = None
    mass_kg: Optional[float] = None
    mass_definition: Optional[str] = None
    front_mass_fraction: Optional[float] = None
    wheelbase_m: Optional[float] = None
    front_track_m: Optional[float] = None
    rear_track_m: Optional[float] = None
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    ground_clearance_m: Optional[float] = None
    seats: Optional[int] = None
    doors: Optional[int] = None
    fuel_tank_capacity_l: Optional[float] = None
    pit_fuel_fill_rate_l_s: Optional[float] = None
    pit_tire_wear_threshold: Optional[float] = None
    drive_type: Optional[str] = None
    differential_type: Optional[str] = None
    steering_type: Optional[str] = None
    brake_front_type: Optional[str] = None
    brake_rear_type: Optional[str] = None
    abs: Optional[bool] = None
    stability_control: Optional[bool] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    data_confidence: Optional[float] = None
    notes: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500, description="URL pública de la imagen del vehículo")


class VehicleListItem(VehicleBase):
    """Esquema ligero para listados, catálogos y búsquedas."""
    id: uuid.UUID
    manufacturer: ManufacturerResponse
    created_at: datetime
    updated_at: datetime


class VehicleDetailResponse(VehicleBase):
    """Esquema completo con todos los subsistemas técnicos asociados."""
    id: uuid.UUID
    manufacturer: ManufacturerResponse
    created_at: datetime
    updated_at: datetime
    engine: Optional[EngineResponse] = None
    gearbox: Optional[GearboxResponse] = None
    suspension: Optional[SuspensionResponse] = None
    aerodynamics: Optional[AerodynamicsResponse] = None
    tires: List[TireSetupResponse] = []
