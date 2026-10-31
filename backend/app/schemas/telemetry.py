"""Esquemas Pydantic para la Fase 7: Telemetría Real, Sesiones, Muestras y Comparación Sim vs Real."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import Field
from app.schemas.common import AppBaseModel


class TelemetrySampleIn(AppBaseModel):
    """Muestra de telemetría individual."""
    sample_index: int = Field(..., ge=0)
    timestamp: datetime
    distance_m: Optional[float] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    speed_m_s: Optional[float] = None
    longitudinal_acceleration_m_s2: Optional[float] = None
    lateral_acceleration_m_s2: Optional[float] = None
    heading_deg: Optional[float] = None
    steering_angle_deg: Optional[float] = None
    throttle_percent: Optional[float] = None
    brake_percent: Optional[float] = None
    engine_rpm: Optional[float] = None
    gear: Optional[int] = None


class TelemetrySessionCreate(AppBaseModel):
    """Creación de una sesión de telemetría."""
    vehicle_id: uuid.UUID
    variant_id: uuid.UUID
    driver_id: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    sampling_rate_hz: Optional[float] = 10.0
    data_source: Optional[str] = "CSV / Datalogger"
    notes: Optional[str] = None


class TelemetrySessionResponse(AppBaseModel):
    """Respuesta con los datos de una sesión de telemetría."""
    id: uuid.UUID
    vehicle_id: uuid.UUID
    variant_id: uuid.UUID
    driver_id: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    sampling_rate_hz: Optional[float] = None
    data_source: Optional[str] = None
    quality_status: str
    samples_count: int = 0
    notes: Optional[str] = None


class TelemetryImportResult(AppBaseModel):
    """Resultado del parseo e importación de archivo de telemetría."""
    session_id: uuid.UUID
    samples_imported: int
    duration_s: float
    max_speed_kmh: float
    total_distance_m: float
    channels_detected: List[str]


class TelemetryValidationComparison(AppBaseModel):
    """Comparativa y validación cruzada entre telemetría real y simulación física QSS."""
    session_id: uuid.UUID
    vehicle_id: uuid.UUID
    variant_id: uuid.UUID
    real_lap_time_s: float
    simulated_lap_time_s: float
    delta_s: float
    percentage_error: float
    real_max_speed_kmh: float
    simulated_max_speed_kmh: float
    real_avg_speed_kmh: float
    simulated_avg_speed_kmh: float
    speed_rmse_kmh: float
    correlation_coefficient: float
    sampled_comparison: List[Dict[str, Any]]
