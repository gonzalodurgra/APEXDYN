"""
Modelos SQLAlchemy 2.x para un simulador de tiempos de coches de serie.
Base de datos recomendada: PostgreSQL + PostGIS.

Dependencias:
    pip install "sqlalchemy>=2.0" "psycopg[binary]>=3.1" geoalchemy2

Variables de conexión:
    DATABASE_URL=postgresql+psycopg://usuario:password@localhost:5432/car_simulator

Notas:
- Los nombres de superficies, tipos y estados se guardan como texto para facilitar
  la ampliación del catálogo. Conviene validarlos con Enum de Python/Pydantic en la API.
- Las geometrías GPS se guardan en EPSG:4326. Para cálculos métricos, transforma
  las geometrías a un CRS proyectado apropiado o utiliza ST_Transform en PostGIS.
- Este archivo define el esquema; no crea tablas automáticamente al importarse.
  Para desarrollo puede usarse Base.metadata.create_all(engine); para producción,
  se recomienda gestionar cambios con Alembic.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from geoalchemy2 import Geography, Geometry


def uuid4() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# VEHÍCULOS
# ---------------------------------------------------------------------------

class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    website: Mapped[Optional[str]] = mapped_column(String(300))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="manufacturer")


class Vehicle(Base):
    """Una versión concreta de fábrica, no solo el nombre comercial del modelo."""

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

    # Masa y dimensiones: especificar siempre si la masa es en vacío o en orden de marcha.
    mass_kg: Mapped[float] = mapped_column(Float, nullable=False)
    mass_definition: Mapped[str] = mapped_column(
        String(40), default="kerb_weight", nullable=False
    )  # kerb_weight, curb_weight, DIN, EU, race_ready...
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

    drive_type: Mapped[Optional[str]] = mapped_column(String(20))  # FWD, RWD, AWD, 4WD
    differential_type: Mapped[Optional[str]] = mapped_column(String(60))
    steering_type: Mapped[Optional[str]] = mapped_column(String(80))
    brake_front_type: Mapped[Optional[str]] = mapped_column(String(80))
    brake_rear_type: Mapped[Optional[str]] = mapped_column(String(80))
    abs: Mapped[Optional[bool]] = mapped_column(Boolean)
    stability_control: Mapped[Optional[bool]] = mapped_column(Boolean)

    source_url: Mapped[Optional[str]] = mapped_column(String(1000))
    source_name: Mapped[Optional[str]] = mapped_column(String(200))
    data_confidence: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

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
        CheckConstraint("displacement_cc IS NULL OR displacement_cc > 0"),
        CheckConstraint("cylinders IS NULL OR cylinders > 0"),
        CheckConstraint("max_rpm IS NULL OR max_rpm > 0"),
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
        CheckConstraint("rpm >= 0"),
        CheckConstraint("torque_nm IS NULL OR torque_nm >= 0"),
        CheckConstraint("power_kw IS NULL OR power_kw >= 0"),
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
        CheckConstraint("gear_number >= 0"),
        CheckConstraint("ratio > 0"),
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
    front_type: Mapped[Optional[str]] = mapped_column(String(100))
    rear_type: Mapped[Optional[str]] = mapped_column(String(100))
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
        CheckConstraint("cold_pressure_front_kpa IS NULL OR cold_pressure_front_kpa > 0"),
        CheckConstraint("cold_pressure_rear_kpa IS NULL OR cold_pressure_rear_kpa > 0"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    axle: Mapped[str] = mapped_column(String(10), nullable=False)  # FRONT, REAR, ALL
    tire_brand: Mapped[Optional[str]] = mapped_column(String(100))
    tire_model: Mapped[Optional[str]] = mapped_column(String(120))
    tire_category: Mapped[Optional[str]] = mapped_column(String(60))  # road, semi-slick...
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
    """Punto de una curva experimental/modelada del neumático.

    Puede representar fuerza frente a slip ratio, slip angle, carga o temperatura.
    Los ejes concretos se describen con curve_type y metadata_json.
    """

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


# ---------------------------------------------------------------------------
# CIRCUITOS, TRAMOS Y GEOMETRÍA
# ---------------------------------------------------------------------------

class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        CheckConstraint("length_m IS NULL OR length_m > 0"),
        Index("ix_tracks_location", "location", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    track_type: Mapped[str] = mapped_column(String(30), nullable=False)  # CIRCUIT, RALLY_STAGE
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    region: Mapped[Optional[str]] = mapped_column(String(120))
    location = mapped_column(Geography(geometry_type="POINT", srid=4326))
    official_length_m: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(500))
    is_public_road: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    variants: Mapped[list["TrackVariant"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )


class TrackVariant(Base):
    __tablename__ = "track_variants"
    __table_args__ = (
        UniqueConstraint("track_id", "name", "direction", name="uq_track_variant_direction"),
        CheckConstraint("length_m IS NULL OR length_m > 0"),
        Index("ix_track_variant_centerline", "centerline", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    track_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), default="Principal", nullable=False)
    direction: Mapped[str] = mapped_column(String(30), default="forward", nullable=False)
    is_closed_loop: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    length_m: Mapped[Optional[float]] = mapped_column(Float)
    centerline = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))
    geometry_source: Mapped[Optional[str]] = mapped_column(String(200))
    geometry_accuracy_m: Mapped[Optional[float]] = mapped_column(Float)
    sampling_interval_m: Mapped[Optional[float]] = mapped_column(Float)
    processing_method: Mapped[Optional[str]] = mapped_column(Text)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(30), default="provisional", nullable=False)

    track: Mapped["Track"] = relationship(back_populates="variants")
    points: Mapped[list["TrackGeometryPoint"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan",
        order_by="TrackGeometryPoint.sequence",
    )
    elevation_profile: Mapped[list["ElevationPoint"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan",
        order_by="ElevationPoint.distance_m",
    )
    surface_segments: Mapped[list["SurfaceSegment"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    features: Mapped[list["TrackFeature"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    boundaries: Mapped[list["TrackBoundary"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    conditions: Mapped[list["TrackCondition"]] = relationship(back_populates="variant")
    telemetry_sessions: Mapped[list["TelemetrySession"]] = relationship(back_populates="variant")
    measured_results: Mapped[list["MeasuredResult"]] = relationship(back_populates="variant")
    simulations: Mapped[list["SimulationRun"]] = relationship(back_populates="variant")


class TrackGeometryPoint(Base):
    __tablename__ = "track_geometry_points"
    __table_args__ = (
        UniqueConstraint("variant_id", "sequence", name="uq_track_point_sequence"),
        UniqueConstraint("variant_id", "distance_m", name="uq_track_point_distance"),
        CheckConstraint("sequence >= 0"),
        CheckConstraint("distance_m >= 0"),
        Index("ix_track_points_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    x_m: Mapped[Optional[float]] = mapped_column(Float)  # coordenada local proyectada
    y_m: Mapped[Optional[float]] = mapped_column(Float)
    elevation_m: Mapped[Optional[float]] = mapped_column(Float)
    horizontal_accuracy_m: Mapped[Optional[float]] = mapped_column(Float)
    vertical_accuracy_m: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String(200))

    variant: Mapped["TrackVariant"] = relationship(back_populates="points")


class ElevationPoint(Base):
    __tablename__ = "elevation_points"
    __table_args__ = (
        UniqueConstraint("variant_id", "distance_m", name="uq_elevation_distance"),
        CheckConstraint("distance_m >= 0"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_m: Mapped[float] = mapped_column(Float, nullable=False)
    grade_percent: Mapped[Optional[float]] = mapped_column(Float)
    cross_slope_percent: Mapped[Optional[float]] = mapped_column(Float)
    vertical_accuracy_m: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String(200))

    variant: Mapped["TrackVariant"] = relationship(back_populates="elevation_profile")


class SurfaceSegment(Base):
    __tablename__ = "surface_segments"
    __table_args__ = (
        CheckConstraint("start_distance_m >= 0"),
        CheckConstraint("end_distance_m > start_distance_m"),
        Index("ix_surface_segment_range", "variant_id", "start_distance_m", "end_distance_m"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    start_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    end_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    surface_type: Mapped[str] = mapped_column(String(60), nullable=False)
    roughness_index: Mapped[Optional[float]] = mapped_column(Float)
    loose_gravel_depth_mm: Mapped[Optional[float]] = mapped_column(Float)
    wetness: Mapped[Optional[float]] = mapped_column(Float)
    friction_model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("friction_models.id", ondelete="SET NULL")
    )
    source: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["TrackVariant"] = relationship(back_populates="surface_segments")
    friction_model: Mapped[Optional["FrictionModel"]] = relationship(back_populates="surface_segments")


class FrictionModel(Base):
    __tablename__ = "friction_models"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_type: Mapped[str] = mapped_column(String(60), nullable=False)  # constant, lookup, Pacejka...
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[Optional[str]] = mapped_column(String(200))
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    surface_segments: Mapped[list["SurfaceSegment"]] = relationship(back_populates="friction_model")


class TrackFeature(Base):
    __tablename__ = "track_features"
    __table_args__ = (
        CheckConstraint("start_distance_m >= 0"),
        CheckConstraint("end_distance_m IS NULL OR end_distance_m >= start_distance_m"),
        Index("ix_track_features_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    feature_type: Mapped[str] = mapped_column(String(60), nullable=False)
    start_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    end_distance_m: Mapped[Optional[float]] = mapped_column(Float)
    lateral_position_m: Mapped[Optional[float]] = mapped_column(Float)
    severity: Mapped[Optional[float]] = mapped_column(Float)
    height_m: Mapped[Optional[float]] = mapped_column(Float)
    width_m: Mapped[Optional[float]] = mapped_column(Float)
    geom = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)
    source: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["TrackVariant"] = relationship(back_populates="features")


class TrackBoundary(Base):
    __tablename__ = "track_boundaries"
    __table_args__ = (
        Index("ix_track_boundary_left", "left_boundary", postgresql_using="gist"),
        Index("ix_track_boundary_right", "right_boundary", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    boundary_type: Mapped[str] = mapped_column(String(50), nullable=False)
    left_boundary = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))
    right_boundary = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))
    usable_width_m: Mapped[Optional[float]] = mapped_column(Float)
    penalty_type: Mapped[Optional[str]] = mapped_column(String(60))
    source: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["TrackVariant"] = relationship(back_populates="boundaries")


class TrackCondition(Base):
    __tablename__ = "track_conditions"
    __table_args__ = (
        CheckConstraint("air_temperature_c IS NULL OR air_temperature_c > -100"),
        CheckConstraint("surface_temperature_c IS NULL OR surface_temperature_c > -100"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    air_temperature_c: Mapped[Optional[float]] = mapped_column(Float)
    surface_temperature_c: Mapped[Optional[float]] = mapped_column(Float)
    wetness: Mapped[Optional[float]] = mapped_column(Float)
    rainfall_mm_h: Mapped[Optional[float]] = mapped_column(Float)
    wind_speed_m_s: Mapped[Optional[float]] = mapped_column(Float)
    wind_direction_deg: Mapped[Optional[float]] = mapped_column(Float)
    surface_condition: Mapped[Optional[str]] = mapped_column(String(60))
    condition_data: Mapped[Optional[dict]] = mapped_column(JSON)
    source: Mapped[Optional[str]] = mapped_column(String(200))

    variant: Mapped["TrackVariant"] = relationship(back_populates="conditions")


# ---------------------------------------------------------------------------
# PILOTOS, TELEMETRÍA Y RESULTADOS MEDIDOS
# ---------------------------------------------------------------------------

class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_level: Mapped[str] = mapped_column(String(40), nullable=False)  # novice, amateur, expert
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    calibration_source: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class TelemetrySession(Base):
    __tablename__ = "telemetry_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="RESTRICT"), nullable=False
    )
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("driver_profiles.id", ondelete="SET NULL")
    )
    tire_setup_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("tire_setups.id", ondelete="SET NULL")
    )
    condition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("track_conditions.id", ondelete="SET NULL")
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sampling_rate_hz: Mapped[Optional[float]] = mapped_column(Float)
    time_reference: Mapped[Optional[str]] = mapped_column(String(60))
    data_source: Mapped[Optional[str]] = mapped_column(String(200))
    source_file_uri: Mapped[Optional[str]] = mapped_column(String(1000))
    quality_status: Mapped[str] = mapped_column(String(30), default="unreviewed", nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicle: Mapped["Vehicle"] = relationship()
    variant: Mapped["TrackVariant"] = relationship(back_populates="telemetry_sessions")
    driver: Mapped[Optional["DriverProfile"]] = relationship()
    samples: Mapped[list["TelemetrySample"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        order_by="TelemetrySample.sample_index",
    )


class TelemetrySample(Base):
    __tablename__ = "telemetry_samples"
    __table_args__ = (
        UniqueConstraint("session_id", "sample_index", name="uq_telemetry_sample_index"),
        Index("ix_telemetry_timestamp", "session_id", "timestamp"),
        Index("ix_telemetry_position", "position", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telemetry_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    distance_m: Mapped[Optional[float]] = mapped_column(Float)
    position = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    speed_m_s: Mapped[Optional[float]] = mapped_column(Float)
    longitudinal_acceleration_m_s2: Mapped[Optional[float]] = mapped_column(Float)
    lateral_acceleration_m_s2: Mapped[Optional[float]] = mapped_column(Float)
    heading_deg: Mapped[Optional[float]] = mapped_column(Float)
    steering_angle_deg: Mapped[Optional[float]] = mapped_column(Float)
    throttle_percent: Mapped[Optional[float]] = mapped_column(Float)
    brake_percent: Mapped[Optional[float]] = mapped_column(Float)
    brake_pressure_bar: Mapped[Optional[float]] = mapped_column(Float)
    engine_rpm: Mapped[Optional[float]] = mapped_column(Float)
    gear: Mapped[Optional[int]] = mapped_column(Integer)
    yaw_rate_deg_s: Mapped[Optional[float]] = mapped_column(Float)
    wheel_speeds_m_s: Mapped[Optional[dict]] = mapped_column(JSON)
    tire_temperatures_c: Mapped[Optional[dict]] = mapped_column(JSON)
    extra_channels: Mapped[Optional[dict]] = mapped_column(JSON)

    session: Mapped["TelemetrySession"] = relationship(back_populates="samples")


class MeasuredResult(Base):
    __tablename__ = "measured_results"
    __table_args__ = (
        CheckConstraint("elapsed_time_s > 0"),
        Index("ix_measured_result_track_vehicle", "variant_id", "vehicle_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="RESTRICT"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("driver_profiles.id", ondelete="SET NULL")
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("telemetry_sessions.id", ondelete="SET NULL")
    )
    condition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("track_conditions.id", ondelete="SET NULL")
    )
    result_type: Mapped[str] = mapped_column(String(30), nullable=False)  # lap, sector, stage
    elapsed_time_s: Mapped[float] = mapped_column(Float, nullable=False)
    sector_number: Mapped[Optional[int]] = mapped_column(Integer)
    date_recorded: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    tire_description: Mapped[Optional[str]] = mapped_column(String(200))
    source_name: Mapped[Optional[str]] = mapped_column(String(200))
    source_url: Mapped[Optional[str]] = mapped_column(String(1000))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    comparability_notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="measured_results")
    variant: Mapped["TrackVariant"] = relationship(back_populates="measured_results")
    driver: Mapped[Optional["DriverProfile"]] = relationship()


# ---------------------------------------------------------------------------
# SIMULACIONES Y REPRODUCIBILIDAD
# ---------------------------------------------------------------------------

class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        CheckConstraint("predicted_time_s IS NULL OR predicted_time_s > 0"),
        Index("ix_simulation_track_vehicle", "variant_id", "vehicle_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="RESTRICT"), nullable=False
    )
    driver_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("driver_profiles.id", ondelete="SET NULL")
    )
    condition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("track_conditions.id", ondelete="SET NULL")
    )
    geometry_version_number: Mapped[Optional[int]] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    simulation_mode: Mapped[str] = mapped_column(String(40), nullable=False)  # vehicle_limit, human_driver
    predicted_time_s: Mapped[Optional[float]] = mapped_column(Float)
    lower_prediction_s: Mapped[Optional[float]] = mapped_column(Float)
    upper_prediction_s: Mapped[Optional[float]] = mapped_column(Float)
    confidence_or_prediction_level: Mapped[Optional[float]] = mapped_column(Float)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="simulations")
    variant: Mapped["TrackVariant"] = relationship(back_populates="simulations")
    driver_profile: Mapped[Optional["DriverProfile"]] = relationship()


# ---------------------------------------------------------------------------
# CONEXIÓN Y CREACIÓN DE TABLAS (opcional para desarrollo)
# ---------------------------------------------------------------------------

def create_schema(database_url: str, *, echo: bool = False) -> None:
    """Crea las tablas. Asegúrate de que PostGIS está instalado en PostgreSQL."""
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url, echo=echo)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(engine)
    engine.dispose()


if __name__ == "__main__":
    import os

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "Define DATABASE_URL, por ejemplo "
            "'postgresql+psycopg://usuario:password@localhost:5432/car_simulator'"
        )
    create_schema(database_url, echo=True)
    print("Esquema creado correctamente.")
