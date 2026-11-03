"""Motor de estrategia de carrera y gestión de paradas en boxes (Pit Stops)."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np

from app.simulation.endurance.component_state import ComponentState

@dataclass
class PitStopStrategy:
    tank_capacity_l: float = 100.0
    fuel_fill_rate_l_s: float = 2.5       # Caudal reglamentario de repostaje
    tire_change_time_s: float = 14.0      # Tiempo cambio de 4 ruedas
    brake_service_time_s: float = 150.0   # Cambio de pastillas/discos
    pit_lane_delta_s: float = 22.0        # Tiempo perdido en circular por pit lane a 60-80 km/h
    min_fuel_reserve_l: float = 5.0       # Reserva mínima antes de forzar parada
    tire_wear_threshold: float = 0.75     # Umbral de desgaste para cambio de neumáticos
    brake_wear_threshold: float = 0.80    # Umbral de desgaste para servicio de frenos
    repair_on_pit: bool = True
    force_pit_laps: List[int] = field(default_factory=list)

@dataclass
class PitStopRecord:
    lap: int
    race_time_s: float
    duration_s: float
    fuel_added_l: float
    tyres_changed: bool
    brakes_serviced: bool
    repaired_components: List[str] = field(default_factory=list)
    reason: str = "scheduled"

def should_pit(
    lap: int,
    states: Dict[str, ComponentState],
    fuel_remaining_l: float,
    consumption_l_lap: float,
    strategy: PitStopStrategy
) -> Tuple[bool, str]:
    """Evalúa si el vehículo debe entrar a boxes al final de la vuelta."""
    if lap in strategy.force_pit_laps:
        return True, "scheduled_lap"

    if fuel_remaining_l - consumption_l_lap < strategy.min_fuel_reserve_l:
        return True, "fuel_depleted"

    if states.get("tyres") and states["tyres"].wear_fraction >= strategy.tire_wear_threshold:
        return True, "tire_wear"

    if states.get("brakes") and states["brakes"].wear_fraction >= strategy.brake_wear_threshold:
        return True, "brake_wear"

    if strategy.repair_on_pit:
        for comp_name, state in states.items():
            if state.failed and state.repair_time_s > 0:
                return True, f"repair_{comp_name}"
            if state.degraded and state.repair_time_s > 0:
                return True, f"service_{comp_name}"

    return False, ""

def execute_pit_stop(
    lap: int,
    race_time_s: float,
    states: Dict[str, ComponentState],
    fuel_remaining_l: float,
    strategy: PitStopStrategy,
    reason: str
) -> Tuple[Dict[str, ComponentState], float, float, PitStopRecord]:
    """Ejecuta las operaciones de la parada y devuelve el tiempo consumido."""
    pit_ops_time = 0.0

    # 1. Repostaje
    fuel_to_add = max(0.0, strategy.tank_capacity_l - fuel_remaining_l)
    fuel_time = fuel_to_add / strategy.fuel_fill_rate_l_s if strategy.fuel_fill_rate_l_s > 0 else 0.0
    new_fuel = strategy.tank_capacity_l

    # En muchas competiciones (WEC / IMSA), el repostaje y el cambio de gomas se hacen secuencialmente o en paralelo
    # Modelamos concurrente: pit_stop_base = pit_lane_delta + max(fuel_time, tire_time) + reparaciones
    tyres_changed = False
    tire_time = 0.0
    if states.get("tyres") and (states["tyres"].wear_fraction >= strategy.tire_wear_threshold or reason in ("tire_wear", "fuel_depleted")):
        tyres_changed = True
        tire_time = strategy.tire_change_time_s
        states["tyres"].wear_fraction = 0.0
        states["tyres"].life_consumed = 0.0
        states["tyres"].temperature_c = states["tyres"].temp_ambient_c + 30.0  # mantas térmicas
        states["tyres"].failed = False
        states["tyres"].degraded = False

    brakes_serviced = False
    brake_time = 0.0
    if states.get("brakes") and (states["brakes"].wear_fraction >= strategy.brake_wear_threshold or reason == "brake_wear"):
        brakes_serviced = True
        brake_time = strategy.brake_service_time_s
        states["brakes"].wear_fraction = 0.0
        states["brakes"].life_consumed = 0.0
        states["brakes"].temperature_c = states["brakes"].temp_ambient_c + 50.0
        states["brakes"].failed = False
        states["brakes"].degraded = False

    repaired_comps = []
    repair_time = 0.0
    if strategy.repair_on_pit:
        for comp_name, state in states.items():
            if comp_name in ("tyres", "brakes"):
                continue
            if (state.failed or state.degraded) and state.repair_time_s > 0:
                repair_time += state.repair_time_s
                state.failed = False
                state.degraded = False
                state.wear_fraction = max(0.0, state.wear_fraction - 0.5)
                state.life_consumed = state.wear_fraction * state.life_eta
                repaired_comps.append(comp_name)

    ops_duration = max(fuel_time, tire_time) + brake_time + repair_time
    total_pit_duration = strategy.pit_lane_delta_s + ops_duration

    record = PitStopRecord(
        lap=lap,
        race_time_s=round(race_time_s + total_pit_duration, 2),
        duration_s=round(total_pit_duration, 2),
        fuel_added_l=round(fuel_to_add, 2),
        tyres_changed=tyres_changed,
        brakes_serviced=brakes_serviced,
        repaired_components=repaired_comps,
        reason=reason
    )

    return states, new_fuel, total_pit_duration, record

