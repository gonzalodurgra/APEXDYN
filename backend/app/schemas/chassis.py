"""Esquemas Pydantic para Suspensión, Aerodinámica y Neumáticos."""

import uuid
from typing import Optional, List, Dict, Any
from pydantic import Field
from app.schemas.common import AppBaseModel


# --- SUSPENSIÓN ---
class SuspensionBase(AppBaseModel):
    front_type: Optional[str] = Field(None, max_length=200, description="MacPherson, Double wishbone, Multi-link")
    rear_type: Optional[str] = Field(None, max_length=200, description="Multi-link, Torsion beam, Double wishbone")
    front_spring_rate_n_m: Optional[float] = Field(None, gt=0, description="Rigidez de muelles delanteros en N/m")
    rear_spring_rate_n_m: Optional[float] = Field(None, gt=0, description="Rigidez de muelles traseros en N/m")
    front_antiroll_stiffness_nm_rad: Optional[float] = Field(None, gt=0, description="Rigidez barra estabilizadora delantera en Nm/rad")
    rear_antiroll_stiffness_nm_rad: Optional[float] = Field(None, gt=0, description="Rigidez barra estabilizadora trasera en Nm/rad")
    front_damper_data: Optional[Dict[str, Any]] = Field(None, description="Curvas o coeficientes de amortiguación delantera")
    rear_damper_data: Optional[Dict[str, Any]] = Field(None, description="Curvas o coeficientes de amortiguación trasera")
    front_travel_m: Optional[float] = Field(None, gt=0, description="Recorrido de suspensión delantera en metros")
    rear_travel_m: Optional[float] = Field(None, gt=0, description="Recorrido de suspensión trasera en metros")
    notes: Optional[str] = None


class SuspensionCreate(SuspensionBase):
    vehicle_id: uuid.UUID


class SuspensionUpdate(AppBaseModel):
    front_type: Optional[str] = None
    rear_type: Optional[str] = None
    front_spring_rate_n_m: Optional[float] = None
    rear_spring_rate_n_m: Optional[float] = None
    front_antiroll_stiffness_nm_rad: Optional[float] = None
    rear_antiroll_stiffness_nm_rad: Optional[float] = None
    front_damper_data: Optional[Dict[str, Any]] = None
    rear_damper_data: Optional[Dict[str, Any]] = None
    front_travel_m: Optional[float] = None
    rear_travel_m: Optional[float] = None
    notes: Optional[str] = None


class SuspensionResponse(SuspensionBase):
    id: uuid.UUID
    vehicle_id: uuid.UUID


# --- AERODINÁMICA ---
class AerodynamicsBase(AppBaseModel):
    drag_coefficient_cd: Optional[float] = Field(None, gt=0, description="Coeficiente de resistencia aerodinámica Cx (Cd)")
    frontal_area_m2: Optional[float] = Field(None, gt=0, description="Área frontal efectiva A en m²")
    lift_coefficient_cl: Optional[float] = Field(None, description="Coeficiente de sustentación/carga aerodinámica Cz (Cl)")
    front_downforce_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fracción de carga aerodinámica en el eje delantero (0 a 1)")
    aero_reference_speed_m_s: Optional[float] = Field(None, gt=0, description="Velocidad de referencia de los datos en m/s")
    notes: Optional[str] = None


class AerodynamicsCreate(AerodynamicsBase):
    vehicle_id: uuid.UUID


class AerodynamicsUpdate(AppBaseModel):
    drag_coefficient_cd: Optional[float] = None
    frontal_area_m2: Optional[float] = None
    lift_coefficient_cl: Optional[float] = None
    front_downforce_fraction: Optional[float] = None
    aero_reference_speed_m_s: Optional[float] = None
    notes: Optional[str] = None


class AerodynamicsResponse(AerodynamicsBase):
    id: uuid.UUID
    vehicle_id: uuid.UUID


# --- NEUMÁTICOS ---
class TireCurvePointBase(AppBaseModel):
    curve_type: str = Field(..., max_length=60, description="lateral_force_vs_slip_angle, longitudinal_vs_slip_ratio")
    slip_ratio: Optional[float] = None
    slip_angle_deg: Optional[float] = None
    vertical_load_n: Optional[float] = None
    temperature_c: Optional[float] = None
    pressure_kpa: Optional[float] = None
    longitudinal_force_n: Optional[float] = None
    lateral_force_n: Optional[float] = None
    aligning_moment_nm: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None
    source: Optional[str] = None


class TireCurvePointCreate(TireCurvePointBase):
    pass


class TireCurvePointResponse(TireCurvePointBase):
    id: int
    tire_setup_id: uuid.UUID


class TireSetupBase(AppBaseModel):
    axle: str = Field("ALL", max_length=10, description="FRONT, REAR, ALL")
    tire_brand: Optional[str] = Field(None, max_length=100)
    tire_model: Optional[str] = Field(None, max_length=120)
    tire_category: Optional[str] = Field("road", max_length=60, description="road, sport, semi-slick, slick, rally_gravel, snow")
    width_mm: Optional[int] = Field(None, gt=100, lt=450, description="Anchura de sección en mm (ej: 245)")
    aspect_ratio: Optional[int] = Field(None, gt=20, lt=100, description="Perfil o serie (ej: 40)")
    rim_diameter_in: Optional[float] = Field(None, gt=10, lt=26, description="Diámetro de llanta en pulgadas (ej: 18.0)")
    construction: Optional[str] = Field("R", max_length=40, description="Radial (R)")
    compound: Optional[str] = Field(None, max_length=80)
    load_index: Optional[str] = Field(None, max_length=10)
    speed_rating: Optional[str] = Field(None, max_length=10)
    cold_pressure_front_kpa: Optional[float] = Field(None, gt=0, description="Presión delantera en frío (kPa)")
    cold_pressure_rear_kpa: Optional[float] = Field(None, gt=0, description="Presión trasera en frío (kPa)")
    nominal_radius_m: Optional[float] = Field(None, gt=0, description="Radio exterior estático o dinámico estimado (m)")
    rolling_resistance_coefficient: Optional[float] = Field(None, gt=0, lt=0.1, description="Coeficiente de resistencia a la rodadura Crr (ej: 0.012)")
    source: Optional[str] = None
    notes: Optional[str] = None


class TireSetupCreate(TireSetupBase):
    vehicle_id: uuid.UUID
    curve_points: Optional[List[TireCurvePointCreate]] = None


class TireSetupUpdate(AppBaseModel):
    axle: Optional[str] = None
    tire_brand: Optional[str] = None
    tire_model: Optional[str] = None
    tire_category: Optional[str] = None
    width_mm: Optional[int] = None
    aspect_ratio: Optional[int] = None
    rim_diameter_in: Optional[float] = None
    construction: Optional[str] = None
    compound: Optional[str] = None
    load_index: Optional[str] = None
    speed_rating: Optional[str] = None
    cold_pressure_front_kpa: Optional[float] = None
    cold_pressure_rear_kpa: Optional[float] = None
    nominal_radius_m: Optional[float] = None
    rolling_resistance_coefficient: Optional[float] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class TireSetupResponse(TireSetupBase):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    tire_curve_points: List[TireCurvePointResponse] = []
