"""Esquemas Pydantic para Transmisión y Relaciones de Cambio."""

import uuid
from typing import Optional, List
from pydantic import Field
from app.schemas.common import AppBaseModel


class GearRatioBase(AppBaseModel):
    gear_number: int = Field(..., ge=0, description="Número de marcha (0=marcha atrás o neutral, 1=primera...)")
    ratio: float = Field(..., gt=0, description="Relación de transmisión del engranaje")
    label: Optional[str] = Field(None, max_length=30, description="Etiqueta opcional (ej: 1ª, 2ª, R)")


class GearRatioCreate(GearRatioBase):
    pass


class GearRatioResponse(GearRatioBase):
    id: int
    gearbox_id: uuid.UUID


class GearboxBase(AppBaseModel):
    transmission_type: Optional[str] = Field(None, max_length=40, description="manual, automatic, dual_clutch, sequential, CVT")
    gear_count: Optional[int] = Field(None, ge=1, le=12, description="Número de marchas hacia adelante")
    final_drive_ratio: Optional[float] = Field(None, gt=0, description="Relación del grupo cónico diferencial")
    efficiency: Optional[float] = Field(None, ge=0.5, le=1.0, description="Rendimiento mecánico de la transmisión (ej: 0.92 = 92%)")
    shift_time_s: Optional[float] = Field(None, ge=0.0, description="Tiempo promedio de interrupción de potencia al cambiar de marcha")
    drivetrain_inertia_kg_m2: Optional[float] = Field(None, ge=0.0, description="Inercia rotacional equivalente de la cadena cinemática")
    source: Optional[str] = Field(None, max_length=200)


class GearboxCreate(GearboxBase):
    vehicle_id: uuid.UUID
    gears: Optional[List[GearRatioCreate]] = None


class GearboxUpdate(AppBaseModel):
    transmission_type: Optional[str] = None
    gear_count: Optional[int] = None
    final_drive_ratio: Optional[float] = None
    efficiency: Optional[float] = None
    shift_time_s: Optional[float] = None
    drivetrain_inertia_kg_m2: Optional[float] = None
    source: Optional[str] = None


class GearboxResponse(GearboxBase):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    gears: List[GearRatioResponse] = []
