"""Capa de servicios CRUD para Fabricantes."""

import uuid
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.vehicle import Manufacturer
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerUpdate


class ManufacturerService:
    @staticmethod
    def get_by_id(db: Session, manufacturer_id: uuid.UUID) -> Optional[Manufacturer]:
        return db.get(Manufacturer, manufacturer_id)

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Manufacturer]:
        return db.execute(select(Manufacturer).where(Manufacturer.name == name)).scalar_one_or_none()

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> Tuple[List[Manufacturer], int]:
        query = select(Manufacturer)
        count_query = select(func.count(Manufacturer.id))

        if search:
            search_filter = Manufacturer.name.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if country_code:
            query = query.where(Manufacturer.country_code == country_code.upper())
            count_query = count_query.where(Manufacturer.country_code == country_code.upper())

        total = db.execute(count_query).scalar_one()
        items = db.execute(query.order_by(Manufacturer.name.asc()).offset(skip).limit(limit)).scalars().all()
        return list(items), total

    @staticmethod
    def create(db: Session, data: ManufacturerCreate) -> Manufacturer:
        manufacturer = Manufacturer(
            name=data.name,
            country_code=data.country_code.upper() if data.country_code else None,
            website=data.website,
            notes=data.notes,
        )
        db.add(manufacturer)
        db.commit()
        db.refresh(manufacturer)
        return manufacturer

    @staticmethod
    def update(db: Session, manufacturer: Manufacturer, data: ManufacturerUpdate) -> Manufacturer:
        update_data = data.model_dump(exclude_unset=True)
        if "country_code" in update_data and update_data["country_code"]:
            update_data["country_code"] = update_data["country_code"].upper()
        for field, value in update_data.items():
            setattr(manufacturer, field, value)
        db.commit()
        db.refresh(manufacturer)
        return manufacturer

    @staticmethod
    def delete(db: Session, manufacturer: Manufacturer) -> None:
        db.delete(manufacturer)
        db.commit()
