"""Enrutador central para la versión 1 de la API REST."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    manufacturers,
    vehicles,
    subsystems,
    tracks,
    simulations,
    telemetry,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(manufacturers.router)
api_router.include_router(vehicles.router)
api_router.include_router(subsystems.router)
api_router.include_router(tracks.router)
api_router.include_router(simulations.router)
api_router.include_router(telemetry.router)
