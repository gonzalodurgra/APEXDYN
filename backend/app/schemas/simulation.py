"""Esquemas Pydantic para la API de Simulación."""

from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator
from app.schemas.common import AppBaseModel


class SimulationRequest(AppBaseModel):
    """Parámetros de entrada para lanzar una simulación QSS."""
    vehicle_id: uuid.UUID = Field(..., description="UUID del vehículo a simular")
    variant_id: uuid.UUID = Field(..., description="UUID de la variante de trazado")
    driver_profile_id: Optional[uuid.UUID] = Field(None, description="UUID del perfil de piloto (opcional)")
    condition_id: Optional[uuid.UUID] = Field(None, description="UUID de las condiciones de pista (opcional)")
    simulation_mode: str = Field(
        "vehicle_limit",
        description="'vehicle_limit': límite físico absoluto del vehículo. 'human_driver': con corrección por piloto.",
        max_length=40,
    )
    surface_wetness: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Fuerza un nivel de humedad global [0=seco, 1=encharcado]. Si se omite, usa el valor de la BD.",
    )
    tire_mu_override: Optional[float] = Field(
        None, ge=0.1, le=2.0,
        description="Sobreescribe el coeficiente de fricción longitudinal de los neumáticos.",
    )
    num_sectors: int = Field(3, ge=1, le=10, description="Número de sectores para el desglose de tiempos.")
    initial_speed_kmh: Optional[float] = Field(
        None, ge=0.0, le=400.0,
        description="Velocidad inicial en km/h al inicio de la simulación.",
    )
    v_max_cap_kph: Optional[float] = Field(
        None, gt=0, le=500.0,
        description="Velocidad máxima absoluta del simulador (km/h). Si es None, se usa el valor por defecto del backend.",
    )

    @field_validator("simulation_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid = {"vehicle_limit", "human_driver"}
        if v not in valid:
            raise ValueError(f"simulation_mode debe ser uno de: {valid}")
        return v


class CompareRequest(AppBaseModel):
    """Parámetros para comparar múltiples vehículos en el mismo trazado."""
    vehicle_ids: List[uuid.UUID] = Field(..., min_length=1, max_length=20, description="Lista de UUID de vehículos a comparar")
    variant_id: uuid.UUID = Field(..., description="UUID de la variante de trazado común")
    surface_wetness: Optional[float] = Field(None, ge=0.0, le=1.0)
    num_sectors: int = Field(3, ge=1, le=10)
    v_max_cap_kph: Optional[float] = Field(None, gt=0, le=500.0)
    initial_speed_kmh: Optional[float] = Field(
        None, ge=0.0, le=400.0,
        description="Velocidad inicial en km/h al inicio de la simulación.",
    )


class ProfilePoint(AppBaseModel):
    """Punto de un perfil de velocidad/marcha/RPM para visualización."""
    d: float = Field(..., description="Distancia desde el inicio del trazado (m)")
    v: float = Field(..., description="Valor del perfil en este punto")


class SimulationResponse(AppBaseModel):
    """Respuesta completa de la simulación QSS."""
    simulation_run_id: Optional[str] = None
    vehicle_id: str
    vehicle_label: str = ""
    variant_id: str
    model_version: str

    # Tiempo total y sectores
    total_time_s: float = Field(..., description="Tiempo total predicho (segundos)")
    sector_times_s: List[float] = Field([], description="Tiempos por sector (segundos)")

    # Métricas de velocidad
    max_speed_m_s: float
    computed_v_max_cap_kph: Optional[float] = None
    max_speed_kph: float
    min_speed_m_s: float
    min_speed_kph: float
    avg_speed_m_s: float
    avg_speed_kph: float

    # Métricas dinámicas (en g)
    max_lateral_g: float
    max_longitudinal_accel_g: float
    max_braking_g: float

    # Perfiles de velocidad, marcha, RPM, aceleración (muestreados para visualización)
    speed_profile: List[ProfilePoint] = Field([], description="Perfil de velocidad (km/h) vs distancia (m)")
    gear_profile: List[ProfilePoint] = Field([], description="Perfil de marcha vs distancia (m)")
    rpm_profile: List[ProfilePoint] = Field([], description="Perfil de RPM vs distancia (m)")
    accel_profile: List[ProfilePoint] = Field([], description="Perfil de aceleración longitudinal (g) vs distancia (m)")
    radius_profile: List[ProfilePoint] = Field([], description="Perfil de radio de curva (m, limitado a 500m) vs distancia (m)")

    # Parámetros usados
    parameters: Dict[str, Any] = {}
    notes: str = ""


class CompareResultItem(AppBaseModel):
    """Resultado de un vehículo en la comparativa."""
    vehicle_id: str
    vehicle_label: str = ""
    total_time_s: Optional[float] = None
    max_speed_kph: Optional[float] = None
    avg_speed_kph: Optional[float] = None
    max_lateral_g: Optional[float] = None
    error: Optional[str] = None
    rank: Optional[int] = None


class CompareResponse(AppBaseModel):
    """Respuesta de la comparativa de múltiples vehículos."""
    variant_id: str
    results: List[CompareResultItem]
    fastest_vehicle_id: Optional[str] = None
    time_gap_to_fastest_s: Optional[List[float]] = None
