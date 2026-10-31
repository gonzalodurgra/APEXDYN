"""Capa de servicios CRUD para Vehículos de Serie y búsqueda técnica."""

import uuid
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, and_

from app.models.vehicle import (
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
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


class VehicleService:
    @staticmethod
    def get_by_id(db: Session, vehicle_id: uuid.UUID) -> Optional[Vehicle]:
        stmt = (
            select(Vehicle)
            .where(Vehicle.id == vehicle_id)
            .options(
                selectinload(Vehicle.manufacturer),
                selectinload(Vehicle.engine).selectinload(Engine.curve_points),
                selectinload(Vehicle.gearbox).selectinload(Gearbox.gears),
                selectinload(Vehicle.suspension),
                selectinload(Vehicle.aerodynamics),
                selectinload(Vehicle.tires).selectinload(TireSetup.tire_curve_points),
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        manufacturer_id: Optional[uuid.UUID] = None,
        model_search: Optional[str] = None,
        drive_type: Optional[str] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_power_kw: Optional[float] = None,
        max_mass_kg: Optional[float] = None,
    ) -> Tuple[List[Vehicle], int]:
        query = select(Vehicle).options(selectinload(Vehicle.manufacturer))
        count_query = select(func.count(Vehicle.id))

        conditions = []
        if manufacturer_id:
            conditions.append(Vehicle.manufacturer_id == manufacturer_id)
        if model_search:
            search_str = f"%{model_search}%"
            conditions.append(
                (Vehicle.model.ilike(search_str)) |
                (Vehicle.variant.ilike(search_str)) |
                (Vehicle.generation.ilike(search_str))
            )
        if drive_type:
            conditions.append(Vehicle.drive_type == drive_type.upper())
        if min_year:
            conditions.append(Vehicle.model_year >= min_year)
        if max_year:
            conditions.append(Vehicle.model_year <= max_year)
        if max_mass_kg:
            conditions.append(Vehicle.mass_kg <= max_mass_kg)

        if min_power_kw:
            # Filter by engine power
            query = query.join(Vehicle.engine)
            count_query = count_query.join(Vehicle.engine)
            conditions.append(Engine.max_power_kw >= min_power_kw)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total = db.execute(count_query).scalar_one()
        items = db.execute(
            query.order_by(Vehicle.model_year.desc().nullslast(), Vehicle.model.asc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        return list(items), total

    @staticmethod
    def list_detailed(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        manufacturer_id: Optional[uuid.UUID] = None,
        model_search: Optional[str] = None,
        drive_type: Optional[str] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_power_kw: Optional[float] = None,
        max_mass_kg: Optional[float] = None,
    ) -> Tuple[List[Vehicle], int]:
        """Return vehicles with all related subsystems eagerly loaded."""
        query = select(Vehicle).options(
            selectinload(Vehicle.manufacturer),
            selectinload(Vehicle.engine).selectinload(Engine.curve_points),
            selectinload(Vehicle.gearbox).selectinload(Gearbox.gears),
            selectinload(Vehicle.suspension),
            selectinload(Vehicle.aerodynamics),
            selectinload(Vehicle.tires).selectinload(TireSetup.tire_curve_points),
        )
        count_query = select(func.count(Vehicle.id))
        conditions = []
        if manufacturer_id:
            conditions.append(Vehicle.manufacturer_id == manufacturer_id)
        if model_search:
            search_str = f"%{model_search}%"
            conditions.append(
                (Vehicle.model.ilike(search_str)) |
                (Vehicle.variant.ilike(search_str)) |
                (Vehicle.generation.ilike(search_str))
            )
        if drive_type:
            conditions.append(Vehicle.drive_type == drive_type.upper())
        if min_year:
            conditions.append(Vehicle.model_year >= min_year)
        if max_year:
            conditions.append(Vehicle.model_year <= max_year)
        if max_mass_kg:
            conditions.append(Vehicle.mass_kg <= max_mass_kg)
        if min_power_kw:
            query = query.join(Vehicle.engine)
            count_query = count_query.join(Vehicle.engine)
            conditions.append(Engine.max_power_kw >= min_power_kw)
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        total = db.execute(count_query).scalar_one()
        items = db.execute(
            query.order_by(Vehicle.model_year.desc().nullslast(), Vehicle.model.asc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        return list(items), total

    @staticmethod
    def create(db: Session, data: VehicleCreate) -> Vehicle:
        vehicle_dict = data.model_dump(exclude={"engine", "gearbox", "suspension", "aerodynamics", "tires"})
        vehicle = Vehicle(**vehicle_dict)
        db.add(vehicle)
        db.flush()

        # Crear motor si se adjuntó
        if data.engine:
            eng_dict = data.engine.model_dump(exclude={"curve_points", "vehicle_id"})
            engine = Engine(vehicle_id=vehicle.id, **eng_dict)
            db.add(engine)
            db.flush()
            if data.engine.curve_points:
                for pt in data.engine.curve_points:
                    db.add(EngineCurvePoint(engine_id=engine.id, **pt.model_dump()))

        # Crear caja de cambios si se adjuntó
        if data.gearbox:
            gb_dict = data.gearbox.model_dump(exclude={"gears", "vehicle_id"})
            gearbox = Gearbox(vehicle_id=vehicle.id, **gb_dict)
            db.add(gearbox)
            db.flush()
            if data.gearbox.gears:
                for g in data.gearbox.gears:
                    db.add(GearRatio(gearbox_id=gearbox.id, **g.model_dump()))

        # Crear suspensión
        if data.suspension:
            susp_dict = data.suspension.model_dump(exclude={"vehicle_id"})
            db.add(Suspension(vehicle_id=vehicle.id, **susp_dict))

        # Crear aerodinámica
        if data.aerodynamics:
            aero_dict = data.aerodynamics.model_dump(exclude={"vehicle_id"})
            db.add(Aerodynamics(vehicle_id=vehicle.id, **aero_dict))

        # Crear neumáticos
        if data.tires:
            for t in data.tires:
                t_dict = t.model_dump(exclude={"curve_points", "vehicle_id"})
                tire_setup = TireSetup(vehicle_id=vehicle.id, **t_dict)
                db.add(tire_setup)
                db.flush()
                if t.curve_points:
                    for cp in t.curve_points:
                        db.add(TireCurvePoint(tire_setup_id=tire_setup.id, **cp.model_dump()))

        db.commit()
        return VehicleService.get_by_id(db, vehicle.id)

    @staticmethod
    def update(db: Session, vehicle: Vehicle, data: VehicleUpdate) -> Vehicle:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(vehicle, field, value)
        db.commit()
        return VehicleService.get_by_id(db, vehicle.id)

    @staticmethod
    def delete(db: Session, vehicle: Vehicle) -> None:
        db.delete(vehicle)
        db.commit()
