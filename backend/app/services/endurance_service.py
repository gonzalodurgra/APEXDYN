"""Servicio para orquestar la simulación de resistencia conectando BD y EnduranceSimulator."""

from __future__ import annotations
import uuid
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.models.simulation import EnduranceSimulationRun
from app.schemas.endurance import EnduranceRequest, EnduranceResult
from app.services.simulation_service import build_vehicle_physics_model, build_track_profile
from app.simulation.endurance.endurance_simulator import EnduranceSimulator

class EnduranceService:
    @staticmethod
    def run(db: Session, request: EnduranceRequest, persist: bool = True) -> EnduranceResult:
        # Cargar modelo físico del vehículo y perfil de pista desde la BD
        vehicle_model = build_vehicle_physics_model(db, request.vehicle_id)
        track_profile = build_track_profile(db, request.variant_id)

        # Instanciar el simulador con la semilla solicitada para reproducibilidad
        simulator = EnduranceSimulator(rng_seed=request.random_seed)

        # Ejecutar la simulación de resistencia
        result = simulator.simulate(
            vehicle_model=vehicle_model,
            track_profile=track_profile,
            request=request,
        )

        if persist:
            try:
                run_record = EnduranceSimulationRun(
                    vehicle_id=request.vehicle_id,
                    variant_id=request.variant_id,
                    status=result.status,
                    reason_dnf=result.reason_dnf,
                    total_laps_completed=result.total_laps_completed,
                    total_distance_km=result.total_distance_km,
                    total_race_time_s=result.total_race_time_s,
                    best_lap_time_s=result.best_lap_time_s,
                    average_lap_time_s=result.average_lap_time_s,
                    fuel_consumed_total_l=result.fuel_consumed_total_l,
                    total_pit_stops=result.total_pit_stops,
                    total_time_in_pits_s=result.total_time_in_pits_s,
                    finish_probability=result.finish_probability,
                    parameters=request.model_dump(mode="json"),
                    summary_metrics={
                        "fuel_consumption_per_lap_l": result.fuel_consumption_per_lap_l,
                        "fuel_remaining_l": result.fuel_remaining_l,
                    },
                    components_status={k: v.model_dump(mode="json") for k, v in result.components.items()},
                    pit_stops=[p.model_dump(mode="json") for p in result.pit_stops],
                    failures=[f.model_dump(mode="json") for f in result.failures],
                )
                db.add(run_record)
                db.commit()
            except Exception:
                db.rollback()

        return result


