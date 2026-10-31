"""Modelos de Circuitos, Tramos de Rally, Geometría PostGIS, Superficies y Condiciones."""

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
from geoalchemy2 import Geography, Geometry

from app.models.base import Base, uuid4

if TYPE_CHECKING:
    from app.models.simulation import (
        TelemetrySession,
        MeasuredResult,
        SimulationRun,
    )


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        CheckConstraint("official_length_m IS NULL OR official_length_m > 0", name="ck_track_length_pos"),
        Index("ix_tracks_location", "location", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    track_type: Mapped[str] = mapped_column(String(30), nullable=False)  # CIRCUIT, RALLY_STAGE, HILLCLIMB
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    region: Mapped[Optional[str]] = mapped_column(String(120))
    location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False))
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
        CheckConstraint("length_m IS NULL OR length_m > 0", name="ck_track_variant_length_pos"),
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
    centerline = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False))
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
    conditions: Mapped[list["TrackCondition"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    telemetry_sessions: Mapped[list["TelemetrySession"]] = relationship(back_populates="variant")
    measured_results: Mapped[list["MeasuredResult"]] = relationship(back_populates="variant")
    simulations: Mapped[list["SimulationRun"]] = relationship(back_populates="variant")


class TrackGeometryPoint(Base):
    __tablename__ = "track_geometry_points"
    __table_args__ = (
        UniqueConstraint("variant_id", "sequence", name="uq_track_point_sequence"),
        UniqueConstraint("variant_id", "distance_m", name="uq_track_point_distance"),
        CheckConstraint("sequence >= 0", name="ck_track_point_seq_nonneg"),
        CheckConstraint("distance_m >= 0", name="ck_track_point_dist_nonneg"),
        Index("ix_track_points_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    x_m: Mapped[Optional[float]] = mapped_column(Float)  # Coordenada local proyectada métrica
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
        CheckConstraint("distance_m >= 0", name="ck_elevation_dist_nonneg"),
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


class SurfaceSegment(Base):
    __tablename__ = "surface_segments"
    __table_args__ = (
        CheckConstraint("start_distance_m >= 0", name="ck_surf_start_dist_nonneg"),
        CheckConstraint("end_distance_m > start_distance_m", name="ck_surf_end_gt_start"),
        Index("ix_surface_segment_range", "variant_id", "start_distance_m", "end_distance_m"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    start_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    end_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    surface_type: Mapped[str] = mapped_column(String(60), nullable=False)  # asphalt, gravel, snow, wet...
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


class TrackFeature(Base):
    __tablename__ = "track_features"
    __table_args__ = (
        CheckConstraint("start_distance_m >= 0", name="ck_feat_start_dist_nonneg"),
        CheckConstraint("end_distance_m IS NULL OR end_distance_m >= start_distance_m", name="ck_feat_end_gte_start"),
        Index("ix_track_features_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("track_variants.id", ondelete="CASCADE"), nullable=False
    )
    feature_type: Mapped[str] = mapped_column(String(60), nullable=False)  # apex, chicane, jump, bump...
    start_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    end_distance_m: Mapped[Optional[float]] = mapped_column(Float)
    lateral_position_m: Mapped[Optional[float]] = mapped_column(Float)
    severity: Mapped[Optional[float]] = mapped_column(Float)
    height_m: Mapped[Optional[float]] = mapped_column(Float)
    width_m: Mapped[Optional[float]] = mapped_column(Float)
    geom = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False))
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
    left_boundary = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False))
    right_boundary = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False))
    usable_width_m: Mapped[Optional[float]] = mapped_column(Float)
    penalty_type: Mapped[Optional[str]] = mapped_column(String(60))
    source: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["TrackVariant"] = relationship(back_populates="boundaries")


class TrackCondition(Base):
    __tablename__ = "track_conditions"
    __table_args__ = (
        CheckConstraint("air_temperature_c IS NULL OR air_temperature_c > -100", name="ck_cond_air_temp"),
        CheckConstraint("surface_temperature_c IS NULL OR surface_temperature_c > -100", name="ck_cond_surf_temp"),
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
