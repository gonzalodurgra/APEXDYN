"""Esquemas Pydantic para el módulo de simulación de resistencia y fiabilidad."""

from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

class PitStopStrategyInput(BaseModel):
    tank_capacity_l: float = Field(100.0, ge=10.0, le=250.0, description="Capacidad del tanque de combustible (L)")
    fuel_fill_rate_l_s: float = Field(2.5, ge=0.5, le=10.0, description="Caudal de repostaje (L/s)")
    tire_change_time_s: float = Field(14.0, ge=5.0, le=60.0, description="Tiempo de cambio de 4 neumáticos (s)")
    brake_service_time_s: float = Field(120.0, ge=30.0, le=600.0, description="Tiempo de sustitución de pastillas/discos (s)")
    pit_lane_delta_s: float = Field(22.0, ge=10.0, le=60.0, description="Tiempo de tránsito por pit lane (s)")
    min_fuel_reserve_l: float = Field(5.0, ge=1.0, le=20.0, description="Reserva mínima de combustible para forzar parada")
    tire_wear_threshold: float = Field(0.75, ge=0.2, le=0.95, description="Umbral de desgaste de neumáticos para parada")
    brake_wear_threshold: float = Field(0.80, ge=0.3, le=0.98, description="Umbral de desgaste de frenos para servicio")
    repair_on_pit: bool = Field(True, description="Intentar reparaciones mecánicas en boxes")
    force_pit_laps: List[int] = Field(default_factory=list, description="Vueltas forzadas programadas")

class ComponentOverrideInput(BaseModel):
    life_eta: Optional[float] = Field(None, ge=1.0, description="Escala Weibull η (horas de vida nominal)")
    life_beta: Optional[float] = Field(None, ge=0.5, le=8.0, description="Forma Weibull β (parámetro de envejecimiento)")
    initial_wear: Optional[float] = Field(None, ge=0.0, le=0.9, description="Desgaste inicial (0 = nuevo)")
    initial_temp_c: Optional[float] = Field(None, ge=0.0, le=200.0, description="Temperatura inicial (°C)")

class EnduranceRequest(BaseModel):
    vehicle_id: uuid.UUID
    variant_id: uuid.UUID

    # Criterio de terminación (al menos uno debe definirse o se usa laps=50 por defecto)
    race_duration_hours: Optional[float] = Field(None, ge=0.1, le=48.0, description="Duración de carrera en horas (ej: 6, 12, 24)")
    race_laps: Optional[int] = Field(None, ge=1, le=1000, description="Número fijo de vueltas")
    race_distance_km: Optional[float] = Field(None, ge=5.0, le=6000.0, description="Distancia total de carrera en km")

    # Condiciones y modo
    ambient_temp_c: float = Field(25.0, ge=-10.0, le=50.0, description="Temperatura ambiente")
    bsfc_g_kwh: float = Field(260.0, ge=180.0, le=450.0, description="Consumo específico (g/kWh)")
    initial_fuel_l: Optional[float] = Field(None, ge=1.0, description="Combustible inicial (None = lleno)")
    power_mode: float = Field(1.0, ge=0.5, le=1.1, description="Modo de potencia de motor [0.5=ahorro extremo, 1.0=100%, 1.1=push/qualifying]")
    driver_aggression: float = Field(1.0, ge=0.7, le=1.3, description="Agresividad del piloto (afecta desgaste neumáticos/frenos)")

    # Estrategia y reproducibilidad
    strategy: PitStopStrategyInput = Field(default_factory=PitStopStrategyInput)
    random_seed: Optional[int] = Field(42, description="Semilla aleatoria para reproducir averías idénticas")
    component_overrides: Dict[str, ComponentOverrideInput] = Field(default_factory=dict)

# Schemas de respuesta
class PitStopOutput(BaseModel):
    lap: int
    race_time_s: float
    duration_s: float
    fuel_added_l: float
    tyres_changed: bool
    brakes_serviced: bool
    repaired_components: List[str]
    reason: str

class FailureEventOutput(BaseModel):
    lap: int
    race_time_s: float
    component: str
    cause: str
    is_terminal: bool

class ComponentStatusOutput(BaseModel):
    name: str
    wear_percent: float
    final_temp_c: float
    life_consumed_hours: float
    total_life_consumed_hours: float  # Vida total consumida incluyendo después de servicios
    services_count: int               # Número de veces que el componente fue serviciado/cambiado
    survival_probability: float
    failed: bool
    degraded: bool

class LapTelemetrySummary(BaseModel):
    lap: int
    lap_time_s: float
    fuel_remaining_l: float
    tyre_wear_percent: float
    brake_wear_percent: float
    engine_temp_c: float
    tyre_temp_c: float
    brakes_temp_c: float
    pit_time_s: float

class EnduranceResult(BaseModel):
    vehicle_id: str
    variant_id: str
    status: str  # "finished" | "dnf"
    reason_dnf: Optional[str] = None
    terminal_lap: int
    total_laps_completed: int
    total_distance_km: float
    total_race_time_s: float
    best_lap_time_s: float
    average_lap_time_s: float
    fuel_consumed_total_l: float
    fuel_consumption_per_lap_l: float
    fuel_remaining_l: float
    total_pit_stops: int
    total_time_in_pits_s: float
    finish_probability: float
    pit_stops: List[PitStopOutput]
    failures: List[FailureEventOutput]
    components: Dict[str, ComponentStatusOutput]
    lap_history: List[LapTelemetrySummary]

