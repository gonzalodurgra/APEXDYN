"""Modelos de Pilotos, Telemetría, Mediciones Reales y Simulaciones."""

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
from geoalchemy2 import Geometry

from app.models.base import Base, uuid4

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle, TireSetup
    from app.models.track import TrackVariant, TrackCondition


class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_level: Mapped[str] = mapped_column(String(40), nullable=False)  # novice, intermediate, expert, theoretical_ideal
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
        Index("ix_telemetry_distance", "session_id", "distance_m"),
        Index("ix_telemetry_position", "position", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telemetry_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    distance_m: Mapped[Optional[float]] = mapped_column(Float)
    position = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False))
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
        CheckConstraint("elapsed_time_s > 0", name="ck_measured_time_pos"),
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


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        CheckConstraint("predicted_time_s IS NULL OR predicted_time_s > 0", name="ck_sim_time_pos"),
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
