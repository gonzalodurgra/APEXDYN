"""Simulador principal de carreras de resistencia.

Ejecuta la carrera vuelta a vuelta orquestando:
- Rendimiento físico por vuelta (apoyándose en QSSSimulator)
- Evolución térmica
- Acumulación de desgaste mecánico dependiente de carga
- Fallos probabilísticos (Weibull) y degradación progresiva
- Consumo y masa de combustible
- Estrategia de pit stops (repostaje, neumáticos, reparaciones)
"""

from __future__ import annotations
import math
import copy
from typing import Dict, List, Optional, Tuple
import numpy as np

from app.simulation.vehicle_physics import VehiclePhysicsModel
from app.simulation.qss_simulator import QSSSimulator, TrackProfile, SimulationResult
from app.simulation.endurance.component_state import ComponentState, default_component_states
from app.simulation.endurance.thermal_model import (
    update_temperature,
    engine_power_factor,
    brake_fade_factor,
    tire_thermal_grip_factor,
)
from app.simulation.endurance.wear_model import compute_wear_delta
from app.simulation.endurance.failure_model import (
    sample_failure,
    degradation_check,
    survival_probability,
)
from app.simulation.endurance.fuel_model import (
    fuel_consumption_rate_l_s,
    update_fuel,
    fuel_mass_effect_on_lap_time,
)
from app.simulation.endurance.tire_model import tire_wear_rate, tire_grip_factor
from app.simulation.endurance.brake_model import brake_wear_rate, brake_effectiveness
from app.simulation.endurance.strategy_engine import (
    PitStopStrategy,
    execute_pit_stop,
    should_pit,
    PitStopRecord,
)
from app.schemas.endurance import (
    EnduranceRequest,
    EnduranceResult,
    PitStopOutput,
    FailureEventOutput,
    ComponentStatusOutput,
    LapTelemetrySummary,
)

# ---------------------------------------------------------------------------
# Mapeo y traducción al español de motivos de pit stop y componentes
# ---------------------------------------------------------------------------
COMPONENT_NAMES_ES: Dict[str, str] = {
    "engine": "Motor",
    "turbo": "Turbo / Admisión",
    "gearbox": "Caja de cambios",
    "clutch": "Embrague",
    "transmission": "Transmisión",
    "cooling": "Refrigeración",
    "lubrication": "Lubricación",
    "brakes": "Frenos",
    "suspension": "Suspensión",
    "tyres": "Neumáticos",
    "electrical": "Sistema eléctrico",
    "powertrain": "Tren motriz",
    "fuel_system": "Sistema de combustible",
}

REASON_TRANSLATIONS: Dict[str, str] = {
    # Repostaje y paradas programadas
    "fuel_depleted": "Bajo nivel de combustible (Repostaje)",
    "scheduled": "Parada programada",
    "scheduled_lap": "Parada programada por vuelta",
    "Fuel low": "Bajo nivel de combustible",
    "Strategy pit": "Parada estratégica",
    # Desgaste de consumibles estándar
    "tire_wear": "Desgaste de neumáticos (Cambio de gomas)",
    "brake_wear": "Desgaste excesivo de frenos",
    # Reparaciones por avería de módulos / componentes
    "repair_engine": "Reparación de motor",
    "repair_turbo": "Reparación de turbo / admisión",
    "repair_gearbox": "Reparación de caja de cambios",
    "repair_clutch": "Reparación de embrague",
    "repair_transmission": "Reparación de transmisión",
    "repair_cooling": "Reparación de circuito de refrigeración",
    "repair_lubrication": "Reparación de sistema de lubricación",
    "repair_brakes": "Reparación del sistema de frenos",
    "repair_suspension": "Reparación de suspensión",
    "repair_tyres": "Sustitución de neumáticos dañados",
    "repair_electrical": "Reparación del sistema eléctrico",
    # Mantenimiento / servicio por degradación
    "service_engine": "Mantenimiento preventivo de motor",
    "service_turbo": "Revisión de turbo / admisión",
    "service_gearbox": "Mantenimiento de caja de cambios",
    "service_clutch": "Ajuste / cambio de embrague",
    "service_transmission": "Servicio de transmisión",
    "service_cooling": "Purga y servicio de refrigeración",
    "service_lubrication": "Reposición / cambio de aceite (Lubricación)",
    "service_brakes": "Sustitución de pastillas / discos de freno",
    "service_suspension": "Ajuste de suspensión",
    "service_tyres": "Revisión / cambio de neumáticos",
    "service_electrical": "Diagnóstico y servicio eléctrico",
}

def translate_reason(reason: str) -> str:
    """Traduce cualquier motivo de parada técnica al español."""
    if not reason:
        return "Parada en boxes"
    if reason in REASON_TRANSLATIONS:
        return REASON_TRANSLATIONS[reason]
    if reason.startswith("repair_"):
        comp = reason.replace("repair_", "")
        comp_es = COMPONENT_NAMES_ES.get(comp, comp)
        return f"Reparación de {comp_es.lower()}"
    if reason.startswith("service_"):
        comp = reason.replace("service_", "")
        comp_es = COMPONENT_NAMES_ES.get(comp, comp)
        return f"Mantenimiento de {comp_es.lower()}"
    return reason


class EnduranceSimulator:
    def __init__(self, rng_seed: Optional[int] = 42):
        self.rng = np.random.default_rng(rng_seed)

    def simulate(
        self,
        vehicle_model: VehiclePhysicsModel,
        track_profile: TrackProfile,
        request: EnduranceRequest,
    ) -> EnduranceResult:
        # 1. Inicializar componentes y aplicar overrides
        states = default_component_states(ambient_temp_c=request.ambient_temp_c)
        for name, override in request.component_overrides.items():
            if name in states:
                if override.life_eta is not None:
                    states[name].life_eta = override.life_eta
                if override.life_beta is not None:
                    states[name].life_beta = override.life_beta
                if override.initial_wear is not None:
                    states[name].wear_fraction = override.initial_wear
                    states[name].life_consumed = override.initial_wear * states[name].life_eta
                if override.initial_temp_c is not None:
                    states[name].temperature_c = override.initial_temp_c

        # 2. Configuración de estrategia
        strat_in = request.strategy
        strategy = PitStopStrategy(
            tank_capacity_l=strat_in.tank_capacity_l,
            fuel_fill_rate_l_s=strat_in.fuel_fill_rate_l_s,
            tire_change_time_s=strat_in.tire_change_time_s,
            brake_service_time_s=strat_in.brake_service_time_s,
            pit_lane_delta_s=strat_in.pit_lane_delta_s,
            min_fuel_reserve_l=strat_in.min_fuel_reserve_l,
            tire_wear_threshold=strat_in.tire_wear_threshold,
            brake_wear_threshold=strat_in.brake_wear_threshold,
            repair_on_pit=strat_in.repair_on_pit,
            force_pit_laps=strat_in.force_pit_laps,
        )

        fuel_remaining_l = request.initial_fuel_l if request.initial_fuel_l is not None else strategy.tank_capacity_l
        fuel_consumed_total = 0.0

        # 3. Línea base con QSS para extraer métricas de referencia
        base_simulator = QSSSimulator(vehicle=vehicle_model)
        base_qss: SimulationResult = base_simulator.simulate(track_profile, num_sectors=3)
        base_lap_time = base_qss.total_time_s
        track_length_km = track_profile.total_length_m / 1000.0

        # Condiciones cinemáticas promedio de la vuelta
        avg_speed_m_s = base_qss.avg_speed_m_s or 40.0
        max_lat_g = base_qss.max_lateral_g or 1.2
        max_long_g = base_qss.max_longitudinal_accel_g or 0.8
        max_brake_g = abs(base_qss.max_braking_g) if base_qss.max_braking_g else 1.3
        avg_rpm = float(np.mean(base_qss.engine_rpm_profile)) if len(base_qss.engine_rpm_profile) > 0 else 5500.0

        # Estimación de potencia media en W (aceleración + arrastre)
        avg_power_w = 0.5 * (vehicle_model.mass_kg * 0.4 * 9.81 * avg_speed_m_s) * request.power_mode
        # Consumo de combustible base por vuelta
        base_cons_rate = fuel_consumption_rate_l_s(avg_power_w, request.bsfc_g_kwh)
        est_lap_fuel = base_cons_rate * base_lap_time

        # 4. Determinar condición de parada
        max_duration_s = (request.race_duration_hours * 3600.0) if request.race_duration_hours else None
        target_laps = request.race_laps
        if target_laps is None and request.race_distance_km and track_length_km > 0:
            target_laps = int(math.ceil(request.race_distance_km / track_length_km))
        if target_laps is None and max_duration_s is None:
            target_laps = 50  # Default

        # 5. Bucle principal de carrera vuelta a vuelta
        lap = 1
        race_time_s = 0.0
        total_pit_time_s = 0.0
        pit_records: List[PitStopRecord] = []
        failure_events: List[FailureEventOutput] = []
        lap_history: List[LapTelemetrySummary] = []
        status = "finished"
        reason_dnf: Optional[str] = None
        lap_times: List[float] = []

        # Seguimiento de vida total consumida (no se resetea con servicios) y conteos de servicio
        total_life_consumed: Dict[str, float] = {c: 0.0 for c in states}
        services_count: Dict[str, int] = {c: 0 for c in states}

        while True:
            # Comprobar límite de carrera
            if target_laps is not None and lap > target_laps:
                break
            if max_duration_s is not None and race_time_s >= max_duration_s:
                break

            # A. Factores que modifican el tiempo de vuelta
            # - Temperatura de motor y frenos
            eng_eff = engine_power_factor(states["engine"].temperature_c, states["engine"].temp_max_c, states["engine"].temp_critical_c)
            brake_eff = brake_effectiveness(states["brakes"].wear_fraction, states["brakes"].temperature_c)
            tire_grip = tire_grip_factor(states["tyres"].wear_fraction, states["tyres"].temperature_c)

            # Efectos de degradación acumulada general
            power_factor = request.power_mode * eng_eff
            for c_name in ("turbo", "gearbox", "transmission"):
                if states[c_name].failed:
                    power_factor *= 0.0
                elif states[c_name].degraded:
                    power_factor *= 0.85

            if power_factor <= 0.05:
                status = "dnf"
                reason_dnf = "Pérdida total de tracción o rotura de motor/transmisión"
                failure_events.append(FailureEventOutput(
                    lap=lap, race_time_s=round(race_time_s, 2), component="powertrain",
                    cause=reason_dnf, is_terminal=True
                ))
                break

            # Penalización en tiempo de vuelta estimada por física
            # Grip menor -> velocidad en curva menor -> lap time aumenta cuadráticamente con sqrt(grip)
            grip_penalty = (1.0 / math.sqrt(max(0.35, tire_grip))) - 1.0
            power_penalty = (1.0 / (power_factor ** 0.35)) - 1.0 if power_factor > 0 else 2.0
            brake_penalty = (1.0 - brake_eff) * 0.08

            lap_time_s = base_lap_time * (1.0 + 0.65 * grip_penalty + 0.35 * power_penalty + brake_penalty)
            # Efecto de masa del combustible
            lap_time_s = fuel_mass_effect_on_lap_time(
                fuel_l=fuel_remaining_l,
                fuel_density_kg_l=0.745,
                vehicle_mass_kg=vehicle_model.mass_kg,
                lap_time_base_s=lap_time_s
            )

            # B. Actualización de combustible
            lap_power_w = avg_power_w * power_factor
            cons_rate = fuel_consumption_rate_l_s(lap_power_w, request.bsfc_g_kwh)
            fuel_used_lap = cons_rate * lap_time_s
            if fuel_remaining_l < fuel_used_lap:
                # Se quedó sin combustible en pista
                status = "dnf"
                reason_dnf = "Sin combustible en pista (Out of Fuel)"
                failure_events.append(FailureEventOutput(
                    lap=lap, race_time_s=round(race_time_s, 2), component="fuel_system",
                    cause=reason_dnf, is_terminal=True
                ))
                break

            fuel_remaining_l = max(0.0, fuel_remaining_l - fuel_used_lap)
            fuel_consumed_total += fuel_used_lap

            # C. Actualización térmica de componentes
            lap_speed = (track_profile.total_length_m / lap_time_s) if lap_time_s > 0 else avg_speed_m_s
            update_temperature(states["engine"], load_factor=power_factor, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["turbo"], load_factor=power_factor, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["gearbox"], load_factor=power_factor * 0.9, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["clutch"], load_factor=0.6, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["transmission"], load_factor=power_factor * 0.8, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["cooling"], load_factor=power_factor, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["lubrication"], load_factor=power_factor, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["brakes"], load_factor=request.driver_aggression * 0.85, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["tyres"], load_factor=request.driver_aggression * 0.95, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["suspension"], load_factor=0.5, speed_m_s=lap_speed, dt_s=lap_time_s)
            update_temperature(states["electrical"], load_factor=0.6, speed_m_s=lap_speed, dt_s=lap_time_s)

            # D. Desgaste y fallos probabilísticos por componente
            conditions = {
                "rpm": avg_rpm * power_factor,
                "power_fraction": power_factor,
                "lateral_g": max_lat_g * tire_grip * request.driver_aggression,
                "longitudinal_g": max_long_g * tire_grip,
                "braking_g": max_brake_g * brake_eff * request.driver_aggression,
                "speed_m_s": lap_speed,
                "gear_changes_per_s": 0.08,
                "brake_energy_w": 180000.0 * request.driver_aggression,
                "power_output_w": lap_power_w,
            }

            dt_h = lap_time_s / 3600.0
            terminal_failure = False

            for c_name, st in states.items():
                if st.failed:
                    continue

                # Desgaste incremental
                d_life_consumed = compute_wear_delta(st, conditions, lap_time_s)
                st.life_consumed = max(0.0, st.life_consumed + d_life_consumed)
                st.wear_fraction = max(0.0, min(1.0, st.life_consumed / st.life_eta)) if st.life_eta > 0 else 1.0
                # Vida total acumulada (no se resetea con servicios)
                total_life_consumed[c_name] = total_life_consumed.get(c_name, 0.0) + d_life_consumed

                # Check degradación
                if degradation_check(st):
                    st.degraded = True

                # Check de fallo Weibull
                failed = sample_failure(st, self.rng, dt_h)
                if failed:
                    st.failed = True
                    is_terminal = (st.repair_time_s == 0)
                    comp_es = COMPONENT_NAMES_ES.get(c_name, c_name)
                    failure_events.append(FailureEventOutput(
                        lap=lap,
                        race_time_s=round(race_time_s + lap_time_s, 2),
                        component=c_name,
                        cause=f"Fallo mecánico de {comp_es.lower()} (fatiga acumulada / Weibull)",
                        is_terminal=is_terminal,
                    ))
                    if is_terminal:
                        terminal_failure = True
                        status = "dnf"
                        reason_dnf = f"Avería no reparable en pista: {comp_es}"

            if terminal_failure:
                race_time_s += lap_time_s
                lap_times.append(lap_time_s)
                break

            # E. Estrategia y Paradas en boxes
            pit_time_this_lap = 0.0
            need_pit, pit_reason = should_pit(lap, states, fuel_remaining_l, est_lap_fuel, strategy)
            if need_pit:
                # Capturar life_consumed antes del pit para detectar qué componentes fueron serviciados
                life_before_pit = {c: st.life_consumed for c, st in states.items()}
                # Traducir el motivo de la parada a español antes de registrar
                spanish_reason = translate_reason(pit_reason)
                states, fuel_remaining_l, pit_dur, record = execute_pit_stop(
                    lap=lap,
                    race_time_s=race_time_s + lap_time_s,
                    states=states,
                    fuel_remaining_l=fuel_remaining_l,
                    strategy=strategy,
                    reason=spanish_reason
                )
                # Contabilizar servicios: si life_consumed bajó, el componente fue serviciado
                for c_name, st in states.items():
                    if life_before_pit.get(c_name, 0.0) > 0.0 and st.life_consumed < life_before_pit[c_name]:
                        services_count[c_name] = services_count.get(c_name, 0) + 1
                pit_time_this_lap = pit_dur
                total_pit_time_s += pit_dur
                pit_records.append(record)

            # Resumen vuelta
            race_time_s += lap_time_s + pit_time_this_lap
            lap_times.append(lap_time_s)

            lap_history.append(LapTelemetrySummary(
                lap=lap,
                lap_time_s=round(lap_time_s, 3),
                fuel_remaining_l=round(fuel_remaining_l, 2),
                tyre_wear_percent=round(max(0.0, states["tyres"].wear_fraction * 100), 1),
                brake_wear_percent=round(max(0.0, states["brakes"].wear_fraction * 100), 1),
                engine_temp_c=round(states["engine"].temperature_c, 1),
                tyre_temp_c=round(states["tyres"].temperature_c, 1),
                brakes_temp_c=round(states["brakes"].temperature_c, 1),
                pit_time_s=round(pit_time_this_lap, 2),
            ))

            lap += 1

        # 6. Métricas finales y probabilidad global de finalización
        completed_laps = len(lap_times)
        best_lap = min(lap_times) if lap_times else 0.0
        avg_lap = (sum(lap_times) / completed_laps) if completed_laps > 0 else 0.0
        total_dist_km = round(completed_laps * track_length_km, 2)

        # Probabilidad de supervivencia del sistema (producto de probabilidades Weibull de cada componente crítico)
        p_finish_est = 1.0
        component_summaries: Dict[str, ComponentStatusOutput] = {}
        for c_name, st in states.items():
            # Para la supervivencia usamos la vida total consumida (no la actual del componente)
            total_lc = total_life_consumed.get(c_name, st.life_consumed)
            p_surv = survival_probability(total_lc, st.life_eta, st.life_beta)
            if st.repair_time_s == 0:  # Componentes críticos sin reparación en boxes
                p_finish_est *= p_surv
            component_summaries[c_name] = ComponentStatusOutput(
                name=c_name,
                wear_percent=round(max(0.0, st.wear_fraction * 100), 1),
                final_temp_c=round(st.temperature_c, 1),
                life_consumed_hours=round(max(0.0, st.life_consumed), 3),
                total_life_consumed_hours=round(max(0.0, total_lc), 3),
                services_count=services_count.get(c_name, 0),
                survival_probability=round(max(0.0, min(1.0, p_surv)), 4),
                failed=st.failed,
                degraded=st.degraded,
            )

        pit_outputs = [
            PitStopOutput(
                lap=r.lap,
                race_time_s=r.race_time_s,
                duration_s=r.duration_s,
                fuel_added_l=r.fuel_added_l,
                tyres_changed=r.tyres_changed,
                brakes_serviced=r.brakes_serviced,
                repaired_components=r.repaired_components,
                reason=r.reason,
            )
            for r in pit_records
        ]

        return EnduranceResult(
            vehicle_id=str(vehicle_model.vehicle_id),
            variant_id=track_profile.variant_id,
            status=status,
            reason_dnf=reason_dnf,
            terminal_lap=completed_laps,
            total_laps_completed=completed_laps,
            total_distance_km=total_dist_km,
            total_race_time_s=round(race_time_s, 2),
            best_lap_time_s=round(best_lap, 3),
            average_lap_time_s=round(avg_lap, 3),
            fuel_consumed_total_l=round(fuel_consumed_total, 2),
            fuel_consumption_per_lap_l=round(fuel_consumed_total / completed_laps, 3) if completed_laps > 0 else 0.0,
            fuel_remaining_l=round(fuel_remaining_l, 2),
            total_pit_stops=len(pit_records),
            total_time_in_pits_s=round(total_pit_time_s, 2),
            finish_probability=round(p_finish_est, 4),
            pit_stops=pit_outputs,
            failures=failure_events,
            components=component_summaries,
            lap_history=lap_history,
        )

