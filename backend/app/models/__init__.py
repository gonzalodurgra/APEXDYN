"""Punto de acceso unificado a todos los modelos SQLAlchemy."""

from app.models.base import Base, uuid4
from app.models.vehicle import (
    Manufacturer,
    Vehicle,
    Engine,
    EngineCurvePoint,
    Gearbox,
    GearRatio,
    Suspension,
    Aerodynamics,
    TireSetup,
    TireCurvePoint,
)
from app.models.track import (
    Track,
    TrackVariant,
    TrackGeometryPoint,
    ElevationPoint,
    SurfaceSegment,
    FrictionModel,
    TrackFeature,
    TrackBoundary,
    TrackCondition,
)
from app.models.simulation import (
    DriverProfile,
    TelemetrySession,
    TelemetrySample,
    MeasuredResult,
    SimulationRun,
)

__all__ = [
    "Base",
    "uuid4",
    "Manufacturer",
    "Vehicle",
    "Engine",
    "EngineCurvePoint",
    "Gearbox",
    "GearRatio",
    "Suspension",
    "Aerodynamics",
    "TireSetup",
    "TireCurvePoint",
    "Track",
    "TrackVariant",
    "TrackGeometryPoint",
    "ElevationPoint",
    "SurfaceSegment",
    "FrictionModel",
    "TrackFeature",
    "TrackBoundary",
    "TrackCondition",
    "DriverProfile",
    "TelemetrySession",
    "TelemetrySample",
    "MeasuredResult",
    "SimulationRun",
]
