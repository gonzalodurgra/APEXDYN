"""Esquemas Pydantic para Motores y Curvas de Par y Potencia."""

import uuid
from typing import Optional, List
from pydantic import Field, field_validator
from app.schemas.common import AppBaseModel


class EngineCurvePointBase(AppBaseModel):
    rpm: float = Field(..., ge=0, description="Régimen de giro en revoluciones por minuto")
    torque_nm: Optional[float] = Field(None, ge=0, description="Par motor medido en Newton-metro (Nm)")
    power_kw: Optional[float] = Field(None, ge=0, description="Potencia en kilovatios (kW)")
    source: Optional[str] = Field(None, max_length=200, description="Origen de medición (banco, ficha técnica)")

    @field_validator("power_kw", mode="after")
    @classmethod
    def calculate_power_if_missing(cls, v: Optional[float], info) -> Optional[float]:
        """Si falta la potencia pero hay par y rpm, calcula P(kW) = (T * RPM * 2 * pi) / 60000."""
        values = info.data
        if v is None and "torque_nm" in values and values["torque_nm"] is not None and "rpm" in values:
            rpm = values["rpm"]
            torque = values["torque_nm"]
            return round((torque * rpm * 3.141592653589793) / 30000.0, 2)
        return v


class EngineCurvePointCreate(EngineCurvePointBase):
    pass


class EngineCurvePointResponse(EngineCurvePointBase):
    id: int
    engine_id: uuid.UUID


class EngineBase(AppBaseModel):
    engine_code: Optional[str] = Field(None, max_length=80, description="Código de identificación del motor")
    fuel_type: Optional[str] = Field(None, max_length=40, description="gasoline, diesel, ethanol, electric...")
    aspiration: Optional[str] = Field(None, max_length=40, description="NA, turbo, twin-turbo, supercharged")
    layout: Optional[str] = Field(None, max_length=40, description="inline, V, boxer, rotary, electric")
    cylinders: Optional[int] = Field(None, gt=0, description="Número de cilindros o rotores")
    displacement_cc: Optional[float] = Field(None, gt=0, description="Cilindrada en centímetros cúbicos")
    compression_ratio: Optional[float] = Field(None, gt=0, description="Relación de compresión geométrica")
    max_power_kw: Optional[float] = Field(None, gt=0, description="Potencia máxima declarada en kW")
    max_power_rpm: Optional[float] = Field(None, gt=0, description="Régimen de potencia máxima")
    max_torque_nm: Optional[float] = Field(None, gt=0, description="Par motor máximo declarado en Nm")
    max_torque_rpm: Optional[float] = Field(None, gt=0, description="Régimen de par motor máximo")
    idle_rpm: Optional[float] = Field(None, ge=0, description="Régimen de ralentí")
    max_rpm: Optional[float] = Field(None, gt=0, description="Régimen de corte o límite de revoluciones")
    bsfc_g_kwh: Optional[float] = Field(None, gt=100.0, le=600.0, description="Consumo específico de combustible al freno (BSFC) en g/kWh")
    power_source: Optional[str] = Field(None, max_length=200, description="ICE, BEV, Hybrid")
    notes: Optional[str] = None


class EngineCreate(EngineBase):
    vehicle_id: uuid.UUID
    curve_points: Optional[List[EngineCurvePointCreate]] = None


class EngineUpdate(AppBaseModel):
    engine_code: Optional[str] = None
    fuel_type: Optional[str] = None
    aspiration: Optional[str] = None
    layout: Optional[str] = None
    cylinders: Optional[int] = None
    displacement_cc: Optional[float] = None
    compression_ratio: Optional[float] = None
    max_power_kw: Optional[float] = None
    max_power_rpm: Optional[float] = None
    max_torque_nm: Optional[float] = None
    max_torque_rpm: Optional[float] = None
    idle_rpm: Optional[float] = None
    max_rpm: Optional[float] = None
    bsfc_g_kwh: Optional[float] = None
    power_source: Optional[str] = None
    notes: Optional[str] = None


class EngineResponse(EngineBase):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    curve_points: List[EngineCurvePointResponse] = []
