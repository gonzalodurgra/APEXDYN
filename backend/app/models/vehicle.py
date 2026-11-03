"""Modelos de Vehículo, Fabricante y subsistemas mecánicos."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid4

if TYPE_CHECKING:
    from app.models.simulation import MeasuredResult, SimulationRun


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    website: Mapped[Optional[str]] = mapped_column(String(300))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicles: Mapped[list["Vehicle"]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan"
    )


class Vehicle(Base):
    """Una versión concreta de fábrica de un vehículo de serie."""

    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint(
            "manufacturer_id", "model", "generation", "variant", "model_year",
            name="uq_vehicle_factory_version",
        ),
        CheckConstraint("mass_kg > 0", name="ck_vehicle_mass_positive"),
        CheckConstraint("wheelbase_m > 0", name="ck_vehicle_wheelbase_positive"),
        CheckConstraint("doors IS NULL OR doors >= 0", name="ck_vehicle_doors_nonnegative"),
        Index("ix_vehicles_model_year", "model_year"),
        Index("ix_vehicles_manufacturer_model", "manufacturer_id", "model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="RESTRICT"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    generation: Mapped[Optional[str]] = mapped_column(String(80))
    variant: Mapped[Optional[str]] = mapped_column(String(120))
    trim_level: Mapped[Optional[str]] = mapped_column(String(120))
    model_year: Mapped[Optional[int]] = mapped_column(Integer)
    production_start_year: Mapped[Optional[int]] = mapped_column(Integer)
    production_end_year: Mapped[Optional[int]] = mapped_column(Integer)
    body_style: Mapped[Optional[str]] = mapped_column(String(60))
    market: Mapped[Optional[str]] = mapped_column(String(80))
    country_of_origin: Mapped[Optional[str]] = mapped_column(String(2))
    is_stock_specification: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Masas y cotas dimensionales
    mass_kg: Mapped[float] = mapped_column(Float, nullable=False)
    mass_definition: Mapped[str] = mapped_column(
        String(40), default="kerb_weight", nullable=False
    )  # kerb_weight, curb_weight, DIN, EU, dry_mass...
    front_mass_fraction: Mapped[Optional[float]] = mapped_column(Float)
    wheelbase_m: Mapped[float] = mapped_column(Float, nullable=False)
    front_track_m: Mapped[Optional[float]] = mapped_column(Float)
    rear_track_m: Mapped[Optional[float]] = mapped_column(Float)
    length_m: Mapped[Optional[float]] = mapped_column(Float)
    width_m: Mapped[Optional[float]] = mapped_column(Float)
    height_m: Mapped[Optional[float]] = mapped_column(Float)
    ground_clearance_m: Mapped[Optional[float]] = mapped_column(Float)
    seats: Mapped[Optional[int]] = mapped_column(Integer)
    doors: Mapped[Optional[int]] = mapped_column(Integer)
    fuel_tank_capacity_l: Mapped[Optional[float]] = mapped_column(Float)

    # Chasis, tracción y frenos
    drive_type: Mapped[Optional[str]] = mapped_column(String(20))  # FWD, RWD, AWD, 4WD
    differential_type: Mapped[Optional[str]] = mapped_column(String(60))
    steering_type: Mapped[Optional[str]] = mapped_column(String(80))
    brake_front_type: Mapped[Optional[str]] = mapped_column(String(80))
    brake_rear_type: Mapped[Optional[str]] = mapped_column(String(80))
    abs: Mapped[Optional[bool]] = mapped_column(Boolean)
    stability_control: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Metadatos, origen y trazabilidad
    source_url: Mapped[Optional[str]] = mapped_column(String(1000))
    source_name: Mapped[Optional[str]] = mapped_column(String(200))
    data_confidence: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relaciones
    manufacturer: Mapped["Manufacturer"] = relationship(back_populates="vehicles")
    engine: Mapped[Optional["Engine"]] = relationship(
        back_populates="vehicle", uselist=False, cascade="all, delete-orphan"
    )
    gearbox: Mapped[Optional["Gearbox"]] = relationship(
        back_populates="vehicle", uselist=False, cascade="all, delete-orphan"
    )
    tires: Mapped[list["TireSetup"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    suspension: Mapped[Optional["Suspension"]] = relationship(
        back_populates="vehicle", uselist=False, cascade="all, delete-orphan"
    )
    aerodynamics: Mapped[Optional["Aerodynamics"]] = relationship(
        back_populates="vehicle", uselist=False, cascade="all, delete-orphan"
    )
    measured_results: Mapped[list["MeasuredResult"]] = relationship(back_populates="vehicle")
    simulations: Mapped[list["SimulationRun"]] = relationship(back_populates="vehicle")


class Engine(Base):
    __tablename__ = "engines"
    __table_args__ = (
        UniqueConstraint("vehicle_id", name="uq_engine_vehicle"),
        CheckConstraint("displacement_cc IS NULL OR displacement_cc > 0", name="ck_engine_disp_pos"),
        CheckConstraint("cylinders IS NULL OR cylinders > 0", name="ck_engine_cyl_pos"),
        CheckConstraint("max_rpm IS NULL OR max_rpm > 0", name="ck_engine_max_rpm_pos"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    engine_code: Mapped[Optional[str]] = mapped_column(String(80))
    fuel_type: Mapped[Optional[str]] = mapped_column(String(40))
    aspiration: Mapped[Optional[str]] = mapped_column(String(40))  # NA, turbo, supercharger
    layout: Mapped[Optional[str]] = mapped_column(String(40))  # inline, V, boxer...
    cylinders: Mapped[Optional[int]] = mapped_column(Integer)
    displacement_cc: Mapped[Optional[float]] = mapped_column(Float)
    compression_ratio: Mapped[Optional[float]] = mapped_column(Float)
    max_power_kw: Mapped[Optional[float]] = mapped_column(Float)
    max_power_rpm: Mapped[Optional[float]] = mapped_column(Float)
    max_torque_nm: Mapped[Optional[float]] = mapped_column(Float)
    max_torque_rpm: Mapped[Optional[float]] = mapped_column(Float)
    idle_rpm: Mapped[Optional[float]] = mapped_column(Float)
    max_rpm: Mapped[Optional[float]] = mapped_column(Float)
    bsfc_g_kwh: Mapped[Optional[float]] = mapped_column(Float)
    power_source: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="engine")
    curve_points: Mapped[list["EngineCurvePoint"]] = relationship(
        back_populates="engine", cascade="all, delete-orphan",
        order_by="EngineCurvePoint.rpm",
    )


class EngineCurvePoint(Base):
    __tablename__ = "engine_curve_points"
    __table_args__ = (
        UniqueConstraint("engine_id", "rpm", name="uq_engine_curve_rpm"),
        CheckConstraint("rpm >= 0", name="ck_engine_point_rpm_nonneg"),
        CheckConstraint("torque_nm IS NULL OR torque_nm >= 0", name="ck_engine_point_torque_nonneg"),
        CheckConstraint("power_kw IS NULL OR power_kw >= 0", name="ck_engine_point_power_nonneg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("engines.id", ondelete="CASCADE"), nullable=False
    )
    rpm: Mapped[float] = mapped_column(Float, nullable=False)
    torque_nm: Mapped[Optional[float]] = mapped_column(Float)
    power_kw: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String(200))

    engine: Mapped["Engine"] = relationship(back_populates="curve_points")


class Gearbox(Base):
    __tablename__ = "gearboxes"
    __table_args__ = (UniqueConstraint("vehicle_id", name="uq_gearbox_vehicle"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    transmission_type: Mapped[Optional[str]] = mapped_column(String(40))  # manual, auto, DCT...
    gear_count: Mapped[Optional[int]] = mapped_column(Integer)
    final_drive_ratio: Mapped[Optional[float]] = mapped_column(Float)
    efficiency: Mapped[Optional[float]] = mapped_column(Float)
    shift_time_s: Mapped[Optional[float]] = mapped_column(Float)
    drivetrain_inertia_kg_m2: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String(200))

    vehicle: Mapped["Vehicle"] = relationship(back_populates="gearbox")
    gears: Mapped[list["GearRatio"]] = relationship(
        back_populates="gearbox", cascade="all, delete-orphan",
        order_by="GearRatio.gear_number",
    )


class GearRatio(Base):
    __tablename__ = "gear_ratios"
    __table_args__ = (
        UniqueConstraint("gearbox_id", "gear_number", name="uq_gearbox_gear_number"),
        CheckConstraint("gear_number >= 0", name="ck_gear_number_nonneg"),
        CheckConstraint("ratio > 0", name="ck_gear_ratio_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gearbox_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gearboxes.id", ondelete="CASCADE"), nullable=False
    )
    gear_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 puede ser marcha atrás
    ratio: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(30))

    gearbox: Mapped["Gearbox"] = relationship(back_populates="gears")


class Suspension(Base):
    __tablename__ = "suspensions"
    __table_args__ = (UniqueConstraint("vehicle_id", name="uq_suspension_vehicle"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    front_type: Mapped[Optional[str]] = mapped_column(String(200))
    rear_type: Mapped[Optional[str]] = mapped_column(String(200))
    front_spring_rate_n_m: Mapped[Optional[float]] = mapped_column(Float)
    rear_spring_rate_n_m: Mapped[Optional[float]] = mapped_column(Float)
    front_antiroll_stiffness_nm_rad: Mapped[Optional[float]] = mapped_column(Float)
    rear_antiroll_stiffness_nm_rad: Mapped[Optional[float]] = mapped_column(Float)
    front_damper_data: Mapped[Optional[dict]] = mapped_column(JSON)
    rear_damper_data: Mapped[Optional[dict]] = mapped_column(JSON)
    front_travel_m: Mapped[Optional[float]] = mapped_column(Float)
    rear_travel_m: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="suspension")


class Aerodynamics(Base):
    __tablename__ = "aerodynamics"
    __table_args__ = (UniqueConstraint("vehicle_id", name="uq_aero_vehicle"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    drag_coefficient_cd: Mapped[Optional[float]] = mapped_column(Float)
    frontal_area_m2: Mapped[Optional[float]] = mapped_column(Float)
    lift_coefficient_cl: Mapped[Optional[float]] = mapped_column(Float)
    front_downforce_fraction: Mapped[Optional[float]] = mapped_column(Float)
    aero_reference_speed_m_s: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="aerodynamics")


class TireSetup(Base):
    __tablename__ = "tire_setups"
    __table_args__ = (
        CheckConstraint("cold_pressure_front_kpa IS NULL OR cold_pressure_front_kpa > 0", name="ck_tire_press_f_pos"),
        CheckConstraint("cold_pressure_rear_kpa IS NULL OR cold_pressure_rear_kpa > 0", name="ck_tire_press_r_pos"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    axle: Mapped[str] = mapped_column(String(10), nullable=False)  # FRONT, REAR, ALL
    tire_brand: Mapped[Optional[str]] = mapped_column(String(100))
    tire_model: Mapped[Optional[str]] = mapped_column(String(120))
    tire_category: Mapped[Optional[str]] = mapped_column(String(60))  # road, semi-slick, gravel...
    width_mm: Mapped[Optional[int]] = mapped_column(Integer)
    aspect_ratio: Mapped[Optional[int]] = mapped_column(Integer)
    rim_diameter_in: Mapped[Optional[float]] = mapped_column(Float)
    construction: Mapped[Optional[str]] = mapped_column(String(40))
    compound: Mapped[Optional[str]] = mapped_column(String(80))
    load_index: Mapped[Optional[str]] = mapped_column(String(10))
    speed_rating: Mapped[Optional[str]] = mapped_column(String(10))
    cold_pressure_front_kpa: Mapped[Optional[float]] = mapped_column(Float)
    cold_pressure_rear_kpa: Mapped[Optional[float]] = mapped_column(Float)
    nominal_radius_m: Mapped[Optional[float]] = mapped_column(Float)
    rolling_resistance_coefficient: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="tires")
    tire_curve_points: Mapped[list["TireCurvePoint"]] = relationship(
        back_populates="tire_setup", cascade="all, delete-orphan"
    )


class TireCurvePoint(Base):
    __tablename__ = "tire_curve_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tire_setup_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tire_setups.id", ondelete="CASCADE"), nullable=False
    )
    curve_type: Mapped[str] = mapped_column(String(60), nullable=False)
    slip_ratio: Mapped[Optional[float]] = mapped_column(Float)
    slip_angle_deg: Mapped[Optional[float]] = mapped_column(Float)
    vertical_load_n: Mapped[Optional[float]] = mapped_column(Float)
    temperature_c: Mapped[Optional[float]] = mapped_column(Float)
    pressure_kpa: Mapped[Optional[float]] = mapped_column(Float)
    longitudinal_force_n: Mapped[Optional[float]] = mapped_column(Float)
    lateral_force_n: Mapped[Optional[float]] = mapped_column(Float)
    aligning_moment_nm: Mapped[Optional[float]] = mapped_column(Float)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)
    source: Mapped[Optional[str]] = mapped_column(String(200))

    tire_setup: Mapped["TireSetup"] = relationship(back_populates="tire_curve_points")
