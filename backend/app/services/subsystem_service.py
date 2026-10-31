"""Capa de servicios CRUD para Motores, Transmisiones, Chasis y Neumáticos."""

import uuid
from typing import Optional, List
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.models.vehicle import (
    Engine,
    EngineCurvePoint,
    Gearbox,
    GearRatio,
    Suspension,
    Aerodynamics,
    TireSetup,
    TireCurvePoint,
)
from app.schemas.engine import EngineCreate, EngineUpdate, EngineCurvePointCreate
from app.schemas.gearbox import GearboxCreate, GearboxUpdate, GearRatioCreate
from app.schemas.chassis import (
    SuspensionCreate,
    SuspensionUpdate,
    AerodynamicsCreate,
    AerodynamicsUpdate,
    TireSetupCreate,
    TireSetupUpdate,
    TireCurvePointCreate,
)


class SubsystemService:
    # --- ENGINE ---
    @staticmethod
    def get_engine_by_vehicle(db: Session, vehicle_id: uuid.UUID) -> Optional[Engine]:
        return db.execute(
            select(Engine).where(Engine.vehicle_id == vehicle_id).options(selectinload(Engine.curve_points))
        ).scalar_one_or_none()

    @staticmethod
    def create_or_replace_engine(db: Session, data: EngineCreate) -> Engine:
        existing = db.execute(select(Engine).where(Engine.vehicle_id == data.vehicle_id)).scalar_one_or_none()
        if existing:
            db.delete(existing)
            db.flush()

        eng_dict = data.model_dump(exclude={"curve_points"})
        engine = Engine(**eng_dict)
        db.add(engine)
        db.flush()

        if data.curve_points:
            for pt in data.curve_points:
                db.add(EngineCurvePoint(engine_id=engine.id, **pt.model_dump()))

        db.commit()
        db.refresh(engine)
        return SubsystemService.get_engine_by_vehicle(db, data.vehicle_id)

    @staticmethod
    def add_engine_curve_points(db: Session, engine_id: uuid.UUID, points: List[EngineCurvePointCreate]) -> List[EngineCurvePoint]:
        engine = db.get(Engine, engine_id)
        if not engine:
            return []
        created = []
        for pt in points:
            cp = EngineCurvePoint(engine_id=engine_id, **pt.model_dump())
            db.add(cp)
            created.append(cp)
        db.commit()
        return created

    # --- GEARBOX ---
    @staticmethod
    def get_gearbox_by_vehicle(db: Session, vehicle_id: uuid.UUID) -> Optional[Gearbox]:
        return db.execute(
            select(Gearbox).where(Gearbox.vehicle_id == vehicle_id).options(selectinload(Gearbox.gears))
        ).scalar_one_or_none()

    @staticmethod
    def create_or_replace_gearbox(db: Session, data: GearboxCreate) -> Gearbox:
        existing = db.execute(select(Gearbox).where(Gearbox.vehicle_id == data.vehicle_id)).scalar_one_or_none()
        if existing:
            db.delete(existing)
            db.flush()

        gb_dict = data.model_dump(exclude={"gears"})
        gearbox = Gearbox(**gb_dict)
        db.add(gearbox)
        db.flush()

        if data.gears:
            for g in data.gears:
                db.add(GearRatio(gearbox_id=gearbox.id, **g.model_dump()))

        db.commit()
        return SubsystemService.get_gearbox_by_vehicle(db, data.vehicle_id)

    # --- SUSPENSION ---
    @staticmethod
    def get_suspension_by_vehicle(db: Session, vehicle_id: uuid.UUID) -> Optional[Suspension]:
        return db.execute(select(Suspension).where(Suspension.vehicle_id == vehicle_id)).scalar_one_or_none()

    @staticmethod
    def create_or_replace_suspension(db: Session, data: SuspensionCreate) -> Suspension:
        existing = SubsystemService.get_suspension_by_vehicle(db, data.vehicle_id)
        if existing:
            db.delete(existing)
            db.flush()
        suspension = Suspension(**data.model_dump())
        db.add(suspension)
        db.commit()
        db.refresh(suspension)
        return suspension

    # --- AERODYNAMICS ---
    @staticmethod
    def get_aerodynamics_by_vehicle(db: Session, vehicle_id: uuid.UUID) -> Optional[Aerodynamics]:
        return db.execute(select(Aerodynamics).where(Aerodynamics.vehicle_id == vehicle_id)).scalar_one_or_none()

    @staticmethod
    def create_or_replace_aerodynamics(db: Session, data: AerodynamicsCreate) -> Aerodynamics:
        existing = SubsystemService.get_aerodynamics_by_vehicle(db, data.vehicle_id)
        if existing:
            db.delete(existing)
            db.flush()
        aero = Aerodynamics(**data.model_dump())
        db.add(aero)
        db.commit()
        db.refresh(aero)
        return aero

    # --- TIRES ---
    @staticmethod
    def get_tires_by_vehicle(db: Session, vehicle_id: uuid.UUID) -> List[TireSetup]:
        return list(
            db.execute(
                select(TireSetup)
                .where(TireSetup.vehicle_id == vehicle_id)
                .options(selectinload(TireSetup.tire_curve_points))
            ).scalars().all()
        )

    @staticmethod
    def create_tire_setup(db: Session, data: TireSetupCreate) -> TireSetup:
        t_dict = data.model_dump(exclude={"curve_points"})
        tire = TireSetup(**t_dict)
        db.add(tire)
        db.flush()
        if data.curve_points:
            for cp in data.curve_points:
                db.add(TireCurvePoint(tire_setup_id=tire.id, **cp.model_dump()))
        db.commit()
        db.refresh(tire)
        return tire
