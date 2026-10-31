"""Pruebas automatizadas de la Fase 1: Conexión a Base de Datos, PostGIS y Modelos ORM."""

import pytest
import uuid
from sqlalchemy import text, select
from app.core.database import SessionLocal, engine
from app.models import (
    Base,
    Manufacturer,
    Vehicle,
    Engine,
    EngineCurvePoint,
    Gearbox,
    GearRatio,
    Track,
    TrackVariant,
    TrackGeometryPoint,
    DriverProfile,
)


def test_postgresql_connection_and_postgis():
    """Comprobar que PostgreSQL 18 y PostGIS 3.6 están activos y responden."""
    with engine.connect() as conn:
        res = conn.execute(text("SELECT postgis_version();")).scalar()
        assert res is not None
        assert "3.6" in str(res)


def test_create_and_query_vehicle_hierarchy():
    """Comprobar inserción y consulta en cascada de Fabricante, Vehículo, Motor y Transmisión."""
    db = SessionLocal()
    try:
        # Fabricante único para el test
        test_mfg_name = f"Porsche Test {uuid.uuid4().hex[:6]}"
        mfg = Manufacturer(
            name=test_mfg_name,
            country_code="DE",
            website="https://www.porsche.com",
        )
        db.add(mfg)
        db.flush()

        # Vehículo de serie: 911 GT3 (992)
        vehicle = Vehicle(
            manufacturer_id=mfg.id,
            model="911",
            generation="992",
            variant="GT3",
            model_year=2022,
            mass_kg=1435.0,
            mass_definition="DIN",
            front_mass_fraction=0.38,
            wheelbase_m=2.457,
            front_track_m=1.601,
            rear_track_m=1.553,
            drive_type="RWD",
            differential_type="Mechanical LSD",
            is_stock_specification=True,
        )
        db.add(vehicle)
        db.flush()

        # Motor atmosférico 4.0 B6
        engine_obj = Engine(
            vehicle_id=vehicle.id,
            engine_code="MDG.G",
            fuel_type="gasoline",
            aspiration="NA",
            layout="boxer",
            cylinders=6,
            displacement_cc=3996.0,
            max_power_kw=375.0,  # 510 CV
            max_power_rpm=8400.0,
            max_torque_nm=470.0,
            max_torque_rpm=6100.0,
            idle_rpm=800.0,
            max_rpm=9000.0,
        )
        db.add(engine_obj)
        db.flush()

        # Curva de potencia (muestra representativa)
        curve_points = [
            EngineCurvePoint(engine_id=engine_obj.id, rpm=2000, torque_nm=330.0, power_kw=69.1),
            EngineCurvePoint(engine_id=engine_obj.id, rpm=4000, torque_nm=420.0, power_kw=175.9),
            EngineCurvePoint(engine_id=engine_obj.id, rpm=6100, torque_nm=470.0, power_kw=300.2),
            EngineCurvePoint(engine_id=engine_obj.id, rpm=8400, torque_nm=426.0, power_kw=375.0),
            EngineCurvePoint(engine_id=engine_obj.id, rpm=9000, torque_nm=380.0, power_kw=358.1),
        ]
        db.add_all(curve_points)

        # Transmisión manual 6 vel
        gearbox = Gearbox(
            vehicle_id=vehicle.id,
            transmission_type="manual",
            gear_count=6,
            final_drive_ratio=3.75,
            efficiency=0.92,
            shift_time_s=0.35,
        )
        db.add(gearbox)
        db.flush()

        gears = [
            GearRatio(gearbox_id=gearbox.id, gear_number=1, ratio=3.75),
            GearRatio(gearbox_id=gearbox.id, gear_number=2, ratio=2.38),
            GearRatio(gearbox_id=gearbox.id, gear_number=3, ratio=1.72),
            GearRatio(gearbox_id=gearbox.id, gear_number=4, ratio=1.34),
            GearRatio(gearbox_id=gearbox.id, gear_number=5, ratio=1.11),
            GearRatio(gearbox_id=gearbox.id, gear_number=6, ratio=0.96),
        ]
        db.add_all(gears)

        db.commit()

        # Consultas de verificación
        v_queried = db.execute(
            select(Vehicle).where(Vehicle.id == vehicle.id)
        ).scalar_one()

        assert v_queried.model == "911"
        assert v_queried.manufacturer.name == test_mfg_name
        assert v_queried.engine.max_power_kw == 375.0
        assert len(v_queried.engine.curve_points) == 5
        assert v_queried.gearbox.gear_count == 6
        assert len(v_queried.gearbox.gears) == 6

        # Limpiar datos de prueba
        db.delete(mfg)
        db.commit()
    finally:
        db.close()


def test_postgis_track_and_geometry():
    """Comprobar almacenamiento y consulta con PostGIS de trazados y geometrías espaciales."""
    db = SessionLocal()
    try:
        # Trazado de prueba
        track = Track(
            name="Circuito de Ensayo",
            track_type="CIRCUIT",
            country_code="ES",
            location="SRID=4326;POINT(-3.688344 40.453054)",
            official_length_m=3800.0,
        )
        db.add(track)
        db.flush()

        variant = TrackVariant(
            track_id=track.id,
            name="Configuración GP",
            direction="clockwise",
            is_closed_loop=True,
            length_m=3800.0,
            centerline="SRID=4326;LINESTRING(-3.688 40.453, -3.687 40.454, -3.686 40.453)",
        )
        db.add(variant)
        db.flush()

        point1 = TrackGeometryPoint(
            variant_id=variant.id,
            sequence=1,
            distance_m=0.0,
            geom="SRID=4326;POINT(-3.688 40.453)",
            x_m=0.0,
            y_m=0.0,
            elevation_m=650.0,
        )
        point2 = TrackGeometryPoint(
            variant_id=variant.id,
            sequence=2,
            distance_m=120.5,
            geom="SRID=4326;POINT(-3.687 40.454)",
            x_m=85.2,
            y_m=110.4,
            elevation_m=652.3,
        )
        db.add_all([point1, point2])
        db.commit()

        # Verificar consulta espacial y relaciones
        queried_track = db.execute(select(Track).where(Track.id == track.id)).scalar_one()
        assert queried_track.name == "Circuito de Ensayo"
        assert len(queried_track.variants) == 1
        assert len(queried_track.variants[0].points) == 2
        assert queried_track.variants[0].points[1].distance_m == 120.5

        # Limpiar
        db.delete(track)
        db.commit()
    finally:
        db.close()
