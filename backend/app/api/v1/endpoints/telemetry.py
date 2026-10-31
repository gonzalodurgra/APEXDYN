"""Endpoints REST para la gestión de sesiones de telemetría real y validación física."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.simulation import TelemetrySession
from app.schemas.telemetry import (
    TelemetrySessionResponse,
    TelemetryValidationComparison,
    TelemetryImportResult,
)
from app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/sessions", response_model=List[TelemetrySessionResponse])
def list_telemetry_sessions(db: Session = Depends(get_db)):
    """Lista las sesiones de telemetría registradas."""
    sessions = db.execute(select(TelemetrySession).order_by(TelemetrySession.started_at.desc())).scalars().all()
    results = []
    for s in sessions:
        results.append(
            TelemetrySessionResponse(
                id=s.id,
                vehicle_id=s.vehicle_id,
                variant_id=s.variant_id,
                driver_id=s.driver_id,
                started_at=s.started_at,
                sampling_rate_hz=s.sampling_rate_hz,
                data_source=s.data_source,
                quality_status=s.quality_status,
                samples_count=len(s.samples),
                notes=s.notes,
            )
        )
    return results


@router.post("/upload", response_model=TelemetryImportResult)
async def upload_telemetry_file(
    vehicle_id: uuid.UUID = Form(...),
    variant_id: uuid.UUID = Form(...),
    driver_id: uuid.UUID = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Sube e importa un archivo CSV de telemetría real (MoTeC / RaceChrono / AiM)."""
    try:
        content = (await file.read()).decode("utf-8", errors="replace")
        session = TelemetryService.import_session(
            db=db,
            vehicle_id=vehicle_id,
            variant_id=variant_id,
            driver_id=driver_id,
            csv_content=content,
            data_source=f"Upload: {file.filename}",
        )
        samples = session.samples
        duration = (samples[-1].timestamp - samples[0].timestamp).total_seconds() if len(samples) > 1 else 0.0
        max_v = max(((s.speed_m_s or 0.0) * 3.6 for s in samples), default=0.0)
        tot_d = max(((s.distance_m or 0.0) for s in samples), default=0.0)

        return TelemetryImportResult(
            session_id=session.id,
            samples_imported=len(samples),
            duration_s=round(duration, 2),
            max_speed_kmh=round(max_v, 1),
            total_distance_m=round(tot_d, 1),
            channels_detected=["time", "speed", "distance", "rpm", "gear", "throttle", "brake", "accel"],
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/validate/{session_id}", response_model=TelemetryValidationComparison)
def validate_telemetry_against_simulation(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Compara y valida los datos de una sesión real contra la predicción teórica
    del simulador físico QSS (velocidad, aceleraciones, tiempos y correlación Pearson).
    """
    try:
        return TelemetryService.validate_against_simulation(db, session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
