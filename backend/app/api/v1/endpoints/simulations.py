"""Endpoints de la API REST para Simulación QSS de Tiempos por Vuelta y Tramo."""

from __future__ import annotations

import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.simulation import (
    SimulationRequest,
    SimulationResponse,
    CompareRequest,
    CompareResponse,
    CompareResultItem,
    ProfilePoint,
)
from app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulations", tags=["Simulación Física"])


@router.post(
    "",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar simulación QSS punto-masa",
    description="""
Lanza una simulación quasi-steady-state (QSS) del vehículo indicado sobre la variante
de trazado dada.

El algoritmo implementa el método clásico de velocidad límite con pasadas forward/backward:
1. Calcula el perfil de velocidad máxima sostenida en cada curva (Kamm circle).
2. Pasada forward: propaga velocidades con la máxima tracción disponible.
3. Pasada backward: propaga velocidades con la máxima frenada disponible.
4. Integra el tiempo total como Σ(ds / v_medio).

Requiere que el vehículo tenga motor, caja de cambios y que la variante tenga
geometría procesada (coordenadas métricas x_m, y_m de cada punto).
""",
)
def run_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_db),
) -> SimulationResponse:
    try:
        result = SimulationService.run(
            db=db,
            vehicle_id=request.vehicle_id,
            variant_id=request.variant_id,
            driver_profile_id=request.driver_profile_id,
            condition_id=request.condition_id,
            simulation_mode=request.simulation_mode,
            surface_wetness=request.surface_wetness,
            tire_mu_override=request.tire_mu_override,
            num_sectors=request.num_sectors,
            initial_speed_kmh=request.initial_speed_kmh,
            v_max_cap_kph=request.v_max_cap_kph,
            persist=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la simulación: {str(e)}",
        )

    return _dict_to_response(result)


@router.post(
    "/compare",
    response_model=CompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Comparar múltiples vehículos en el mismo trazado",
    description="""
Ejecuta la simulación QSS para múltiples vehículos sobre el mismo trazado y devuelve
un ranking ordenado por tiempo ascendente, con las diferencias de tiempo respecto
al vehículo más rápido.
""",
)
def compare_vehicles(
    request: CompareRequest,
    db: Session = Depends(get_db),
) -> CompareResponse:
    try:
        results = SimulationService.compare(
            db=db,
            vehicle_ids=request.vehicle_ids,
            variant_id=request.variant_id,
            surface_wetness=request.surface_wetness,
            num_sectors=request.num_sectors,
            v_max_cap_kph=request.v_max_cap_kph,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la comparativa: {str(e)}",
        )

    # Construir items de comparativa
    items: List[CompareResultItem] = []
    fastest_time = None
    fastest_id = None

    for i, r in enumerate(results):
        if "error" in r:
            items.append(CompareResultItem(
                vehicle_id=r.get("vehicle_id", ""),
                error=r["error"],
            ))
            continue

        t = r.get("total_time_s")
        if t is not None and fastest_time is None:
            fastest_time = t
            fastest_id = r.get("vehicle_id")

        items.append(CompareResultItem(
            vehicle_id=r.get("vehicle_id", ""),
            vehicle_label=r.get("vehicle_label", ""),
            total_time_s=t,
            max_speed_kph=r.get("max_speed_kph"),
            avg_speed_kph=r.get("avg_speed_kph"),
            max_lateral_g=r.get("max_lateral_g"),
            rank=i + 1,
        ))

    # Diferencias de tiempo
    gaps = []
    for item in items:
        if item.total_time_s is not None and fastest_time is not None:
            gaps.append(round(item.total_time_s - fastest_time, 3))
        else:
            gaps.append(None)

    return CompareResponse(
        variant_id=str(request.variant_id),
        results=items,
        fastest_vehicle_id=fastest_id,
        time_gap_to_fastest_s=gaps,
    )


@router.get(
    "/history/{variant_id}",
    summary="Historial de simulaciones para una variante de trazado",
    description="Devuelve las últimas simulaciones guardadas para una variante, ordenadas por fecha descendente.",
)
def simulation_history(
    variant_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    from sqlalchemy import select, desc
    from app.models.simulation import SimulationRun
    from app.models.vehicle import Vehicle

    stmt = (
        select(SimulationRun, Vehicle.model, Vehicle.variant.label("vehicle_variant"))
        .join(Vehicle, SimulationRun.vehicle_id == Vehicle.id)
        .where(SimulationRun.variant_id == variant_id)
        .order_by(desc(SimulationRun.created_at))
        .limit(limit)
    )

    rows = db.execute(stmt).all()
    history = []
    for run, model_name, vehicle_variant in rows:
        history.append({
            "simulation_run_id": str(run.id),
            "vehicle_id": str(run.vehicle_id),
            "vehicle_label": f"{model_name} {vehicle_variant or ''}".strip(),
            "model_version": run.model_version,
            "simulation_mode": run.simulation_mode,
            "predicted_time_s": run.predicted_time_s,
            "metrics": run.metrics,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "status": run.status,
        })

    return history


# ---------------------------------------------------------------------------
# Helper: dict → SimulationResponse
# ---------------------------------------------------------------------------

def _dict_to_response(d: Dict[str, Any]) -> SimulationResponse:
    return SimulationResponse(
        simulation_run_id=d.get("simulation_run_id"),
        vehicle_id=d.get("vehicle_id", ""),
        vehicle_label=d.get("vehicle_label", ""),
        variant_id=d.get("variant_id", ""),
        model_version=d.get("model_version", "QSS-v1.0"),
        total_time_s=d.get("total_time_s", 0.0),
        sector_times_s=d.get("sector_times_s", []),
        max_speed_m_s=d.get("max_speed_m_s", 0.0),
        max_speed_kph=d.get("max_speed_kph", 0.0),
        min_speed_m_s=d.get("min_speed_m_s", 0.0),
        min_speed_kph=d.get("min_speed_kph", 0.0),
        avg_speed_m_s=d.get("avg_speed_m_s", 0.0),
        avg_speed_kph=d.get("avg_speed_kph", 0.0),
        max_lateral_g=d.get("max_lateral_g", 0.0),
        max_longitudinal_accel_g=d.get("max_longitudinal_accel_g", 0.0),
        max_braking_g=d.get("max_braking_g", 0.0),
        speed_profile=[ProfilePoint(**p) for p in d.get("speed_profile", [])],
        gear_profile=[ProfilePoint(**p) for p in d.get("gear_profile", [])],
        rpm_profile=[ProfilePoint(**p) for p in d.get("rpm_profile", [])],
        accel_profile=[ProfilePoint(**p) for p in d.get("accel_profile", [])],
        radius_profile=[ProfilePoint(**p) for p in d.get("radius_profile", [])],
        parameters=d.get("parameters", {}),
        notes=d.get("notes", ""),
    )
