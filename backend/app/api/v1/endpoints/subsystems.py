"""Rutas API REST para Subsistemas Mecánicos: Motores, Cajas, Chasis y Neumáticos."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.engine import (
    EngineCreate,
    EngineResponse,
    EngineCurvePointCreate,
    EngineCurvePointResponse,
)
from app.schemas.gearbox import (
    GearboxCreate,
    GearboxResponse,
    GearRatioCreate,
    GearRatioResponse,
)
from app.schemas.chassis import (
    SuspensionCreate,
    SuspensionResponse,
    AerodynamicsCreate,
    AerodynamicsResponse,
    TireSetupCreate,
    TireSetupResponse,
)
from app.services.subsystem_service import SubsystemService
from app.services.vehicle_service import VehicleService

router = APIRouter(tags=["Subsistemas Técnicos"])


# --- MOTORES & CURVAS ---
@router.get("/vehicles/{vehicle_id}/engine", response_model=EngineResponse)
def get_vehicle_engine(vehicle_id: uuid.UUID, db: Session = Depends(get_db)):
    engine = SubsystemService.get_engine_by_vehicle(db, vehicle_id)
    if not engine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El vehículo con ID {vehicle_id} no tiene un motor registrado.",
        )
    return engine


@router.post("/engines", response_model=EngineResponse, status_code=status.HTTP_201_CREATED)
def create_or_replace_engine(data: EngineCreate, db: Session = Depends(get_db)):
    v = VehicleService.get_by_id(db, data.vehicle_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado.")
    return SubsystemService.create_or_replace_engine(db, data)


@router.post("/engines/{engine_id}/curve-points", response_model=List[EngineCurvePointResponse])
def add_engine_curve_points(
    engine_id: uuid.UUID,
    points: List[EngineCurvePointCreate],
    db: Session = Depends(get_db),
):
    res = SubsystemService.add_engine_curve_points(db, engine_id, points)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Motor no encontrado.")
    return res


# --- CAJAS DE CAMBIOS ---
@router.get("/vehicles/{vehicle_id}/gearbox", response_model=GearboxResponse)
def get_vehicle_gearbox(vehicle_id: uuid.UUID, db: Session = Depends(get_db)):
    gb = SubsystemService.get_gearbox_by_vehicle(db, vehicle_id)
    if not gb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El vehículo con ID {vehicle_id} no tiene transmisión registrada.",
        )
    return gb


@router.post("/gearboxes", response_model=GearboxResponse, status_code=status.HTTP_201_CREATED)
def create_or_replace_gearbox(data: GearboxCreate, db: Session = Depends(get_db)):
    v = VehicleService.get_by_id(db, data.vehicle_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado.")
    return SubsystemService.create_or_replace_gearbox(db, data)


# --- SUSPENSIÓN ---
@router.get("/vehicles/{vehicle_id}/suspension", response_model=SuspensionResponse)
def get_vehicle_suspension(vehicle_id: uuid.UUID, db: Session = Depends(get_db)):
    susp = SubsystemService.get_suspension_by_vehicle(db, vehicle_id)
    if not susp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suspensión no encontrada.")
    return susp


@router.post("/suspensions", response_model=SuspensionResponse, status_code=status.HTTP_201_CREATED)
def create_or_replace_suspension(data: SuspensionCreate, db: Session = Depends(get_db)):
    v = VehicleService.get_by_id(db, data.vehicle_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado.")
    return SubsystemService.create_or_replace_suspension(db, data)


# --- AERODINÁMICA ---
@router.get("/vehicles/{vehicle_id}/aerodynamics", response_model=AerodynamicsResponse)
def get_vehicle_aerodynamics(vehicle_id: uuid.UUID, db: Session = Depends(get_db)):
    aero = SubsystemService.get_aerodynamics_by_vehicle(db, vehicle_id)
    if not aero:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aerodinámica no encontrada.")
    return aero


@router.post("/aerodynamics", response_model=AerodynamicsResponse, status_code=status.HTTP_201_CREATED)
def create_or_replace_aerodynamics(data: AerodynamicsCreate, db: Session = Depends(get_db)):
    v = VehicleService.get_by_id(db, data.vehicle_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado.")
    return SubsystemService.create_or_replace_aerodynamics(db, data)


# --- NEUMÁTICOS ---
@router.get("/vehicles/{vehicle_id}/tires", response_model=List[TireSetupResponse])
def get_vehicle_tires(vehicle_id: uuid.UUID, db: Session = Depends(get_db)):
    return SubsystemService.get_tires_by_vehicle(db, vehicle_id)


@router.post("/tires", response_model=TireSetupResponse, status_code=status.HTTP_201_CREATED)
def create_tire_setup(data: TireSetupCreate, db: Session = Depends(get_db)):
    v = VehicleService.get_by_id(db, data.vehicle_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado.")
    return SubsystemService.create_tire_setup(db, data)
