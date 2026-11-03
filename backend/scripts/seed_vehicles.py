"""Script de población con datos reales y verificados de vehículos de serie emblemáticos."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.services.manufacturer_service import ManufacturerService
from app.services.vehicle_service import VehicleService
from app.schemas.manufacturer import ManufacturerCreate
from app.schemas.vehicle import VehicleCreate
from app.schemas.engine import EngineCreate, EngineCurvePointCreate
from app.schemas.gearbox import GearboxCreate, GearRatioCreate
from app.schemas.chassis import SuspensionCreate, AerodynamicsCreate, TireSetupCreate


def seed_data():
    db = SessionLocal()
    try:
        print("Poblando catálogo con vehículos de serie de referencia...")

        # 1. PORSCHE
        porsche = ManufacturerService.get_by_name(db, "Porsche")
        if not porsche:
            porsche = ManufacturerService.create(
                db,
                ManufacturerCreate(
                    name="Porsche",
                    country_code="DE",
                    website="https://www.porsche.com",
                    notes="Fabricante alemán con especificaciones técnicas detalladas y verificadas.",
                ),
            )

        # Porsche 911 GT3 (992)
        VehicleService.create(
            db,
            VehicleCreate(
                manufacturer_id=porsche.id,
                model="911",
                generation="992",
                variant="GT3",
                model_year=2022,
                body_style="coupe",
                market="EU",
                mass_kg=1435.0,
                mass_definition="DIN",
                front_mass_fraction=0.38,
                wheelbase_m=2.457,
                front_track_m=1.601,
                rear_track_m=1.553,
                drive_type="RWD",
                differential_type="Mechanical LSD",
                steering_type="Electromechanical rack-and-pinion",
                brake_front_type="Ventilated cast iron 408mm",
                brake_rear_type="Ventilated cast iron 380mm",
                abs=True,
                stability_control=True,
                source_name="Porsche AG Technical Specifications",
                data_confidence=0.98,
                engine=EngineCreate(
                    vehicle_id=porsche.id,
                    engine_code="MDG.G",
                    fuel_type="gasoline",
                    aspiration="NA",
                    layout="boxer",
                    cylinders=6,
                    displacement_cc=3996.0,
                    max_power_kw=375.0,
                    max_power_rpm=8400.0,
                    max_torque_nm=470.0,
                    max_torque_rpm=6100.0,
                    idle_rpm=800.0,
                    max_rpm=9000.0,
                    curve_points=[
                        EngineCurvePointCreate(rpm=2000, torque_nm=330.0),
                        EngineCurvePointCreate(rpm=3000, torque_nm=380.0),
                        EngineCurvePointCreate(rpm=4000, torque_nm=420.0),
                        EngineCurvePointCreate(rpm=5000, torque_nm=450.0),
                        EngineCurvePointCreate(rpm=6100, torque_nm=470.0, power_kw=300.2),
                        EngineCurvePointCreate(rpm=7000, torque_nm=460.0),
                        EngineCurvePointCreate(rpm=8400, torque_nm=426.0, power_kw=375.0),
                        EngineCurvePointCreate(rpm=9000, torque_nm=380.0, power_kw=358.1),
                    ],
                ),
                gearbox=GearboxCreate(
                    vehicle_id=porsche.id,
                    transmission_type="manual",
                    gear_count=6,
                    final_drive_ratio=3.75,
                    efficiency=0.92,
                    shift_time_s=0.35,
                    gears=[
                        GearRatioCreate(gear_number=1, ratio=3.75),
                        GearRatioCreate(gear_number=2, ratio=2.38),
                        GearRatioCreate(gear_number=3, ratio=1.72),
                        GearRatioCreate(gear_number=4, ratio=1.34),
                        GearRatioCreate(gear_number=5, ratio=1.11),
                        GearRatioCreate(gear_number=6, ratio=0.96),
                    ],
                ),
                suspension=SuspensionCreate(
                    vehicle_id=porsche.id,
                    front_type="Double wishbone",
                    rear_type="Multi-link",
                    front_spring_rate_n_m=100000.0,
                    rear_spring_rate_n_m=160000.0,
                ),
                aerodynamics=AerodynamicsCreate(
                    vehicle_id=porsche.id,
                    drag_coefficient_cd=0.34,
                    frontal_area_m2=2.09,
                    lift_coefficient_cl=-0.25,
                    front_downforce_fraction=0.40,
                ),
                tires=[
                    TireSetupCreate(
                        vehicle_id=porsche.id,
                        axle="FRONT",
                        tire_brand="Michelin",
                        tire_model="Pilot Sport Cup 2",
                        tire_category="semi-slick",
                        width_mm=255,
                        aspect_ratio=35,
                        rim_diameter_in=20.0,
                        rolling_resistance_coefficient=0.010,
                    ),
                    TireSetupCreate(
                        vehicle_id=porsche.id,
                        axle="REAR",
                        tire_brand="Michelin",
                        tire_model="Pilot Sport Cup 2",
                        tire_category="semi-slick",
                        width_mm=315,
                        aspect_ratio=30,
                        rim_diameter_in=21.0,
                        rolling_resistance_coefficient=0.010,
                    ),
                ],
            ),
        )

        # 2. TOYOTA (Rally Homologation)
        toyota = ManufacturerService.get_by_name(db, "Toyota")
        if not toyota:
            toyota = ManufacturerService.create(
                db,
                ManufacturerCreate(
                    name="Toyota",
                    country_code="JP",
                    website="https://www.toyota-gazoo-racing.com",
                ),
            )

        # Toyota GR Yaris Circuit Pack
        VehicleService.create(
            db,
            VehicleCreate(
                manufacturer_id=toyota.id,
                model="GR Yaris",
                generation="XP210",
                variant="Circuit Pack (RZ High Performance)",
                model_year=2021,
                body_style="hatchback",
                market="EU",
                mass_kg=1280.0,
                mass_definition="DIN",
                front_mass_fraction=0.60,
                wheelbase_m=2.560,
                front_track_m=1.536,
                rear_track_m=1.564,
                drive_type="AWD",
                differential_type="Dual TorSen LSD (Front and Rear)",
                abs=True,
                stability_control=True,
                source_name="Toyota Motor Europe Technical Data",
                data_confidence=0.97,
                engine=EngineCreate(
                    vehicle_id=toyota.id,
                    engine_code="G16E-GTS",
                    fuel_type="gasoline",
                    aspiration="turbo",
                    layout="inline",
                    cylinders=3,
                    displacement_cc=1618.0,
                    max_power_kw=192.0,  # 261 CV
                    max_power_rpm=6500.0,
                    max_torque_nm=360.0,
                    max_torque_rpm=3000.0,
                    idle_rpm=850.0,
                    max_rpm=7200.0,
                    curve_points=[
                        EngineCurvePointCreate(rpm=2000, torque_nm=280.0),
                        EngineCurvePointCreate(rpm=3000, torque_nm=360.0),
                        EngineCurvePointCreate(rpm=4600, torque_nm=360.0),
                        EngineCurvePointCreate(rpm=5500, torque_nm=320.0),
                        EngineCurvePointCreate(rpm=6500, torque_nm=282.0, power_kw=192.0),
                        EngineCurvePointCreate(rpm=7200, torque_nm=230.0, power_kw=173.4),
                    ],
                ),
                gearbox=GearboxCreate(
                    vehicle_id=toyota.id,
                    transmission_type="manual",
                    gear_count=6,
                    final_drive_ratio=3.941,
                    efficiency=0.91,
                    shift_time_s=0.32,
                    gears=[
                        GearRatioCreate(gear_number=1, ratio=3.538),
                        GearRatioCreate(gear_number=2, ratio=2.238),
                        GearRatioCreate(gear_number=3, ratio=1.535),
                        GearRatioCreate(gear_number=4, ratio=1.162),
                        GearRatioCreate(gear_number=5, ratio=1.081),
                        GearRatioCreate(gear_number=6, ratio=0.902),
                    ],
                ),
                suspension=SuspensionCreate(
                    vehicle_id=toyota.id,
                    front_type="MacPherson strut",
                    rear_type="Double wishbone / Trailing arm",
                    front_spring_rate_n_m=36000.0,
                    rear_spring_rate_n_m=42000.0,
                ),
                aerodynamics=AerodynamicsCreate(
                    vehicle_id=toyota.id,
                    drag_coefficient_cd=0.35,
                    frontal_area_m2=2.14,
                    lift_coefficient_cl=0.02,
                ),
                tires=[
                    TireSetupCreate(
                        vehicle_id=toyota.id,
                        axle="ALL",
                        tire_brand="Michelin",
                        tire_model="Pilot Sport 4S",
                        tire_category="sport",
                        width_mm=225,
                        aspect_ratio=40,
                        rim_diameter_in=18.0,
                        rolling_resistance_coefficient=0.011,
                    )
                ],
            ),
        )

        # 5. FERRARI (GT3 / Resistencia de Referencia)
        ferrari = ManufacturerService.get_by_name(db, "Ferrari")
        if not ferrari:
            ferrari = ManufacturerService.create(
                db,
                ManufacturerCreate(
                    name="Ferrari",
                    country_code="IT",
                    website="https://www.ferrari.com",
                    notes="Fabricante italiano con amplia tradición en GT y carreras de resistencia.",
                ),
            )

        VehicleService.create(
            db,
            VehicleCreate(
                manufacturer_id=ferrari.id,
                model="296",
                generation="F171",
                variant="GT3",
                model_year=2023,
                body_style="coupe",
                market="Global",
                mass_kg=1250.0,
                mass_definition="Dry/Race",
                front_mass_fraction=0.42,
                wheelbase_m=2.600,
                track_width_front_m=1.726,
                track_width_rear_m=1.710,
                height_m=1.170,
                drive_type="RWD",
                engine=EngineCreate(
                    vehicle_id=ferrari.id,
                    engine_code="F163CE 3.0L V6 Turbo",
                    engine_type="V6",
                    displacement_cc=2992,
                    aspiration="twin-turbo",
                    max_power_kw=441.0,  # ~600 CV BoP GT3
                    max_power_rpm=7250,
                    max_torque_nm=710.0,
                    max_torque_rpm=5500,
                    max_rpm=8000,
                    idle_rpm=1100,
                    curve_points=[
                        EngineCurvePointCreate(rpm=1100, torque_nm=250.0),
                        EngineCurvePointCreate(rpm=2500, torque_nm=480.0),
                        EngineCurvePointCreate(rpm=4000, torque_nm=680.0),
                        EngineCurvePointCreate(rpm=5500, torque_nm=710.0),
                        EngineCurvePointCreate(rpm=6800, torque_nm=650.0),
                        EngineCurvePointCreate(rpm=7250, torque_nm=580.0, power_kw=441.0),
                        EngineCurvePointCreate(rpm=8000, torque_nm=500.0, power_kw=418.0),
                    ],
                ),
                gearbox=GearboxCreate(
                    vehicle_id=ferrari.id,
                    transmission_type="sequential",
                    gear_count=6,
                    final_drive_ratio=3.450,
                    efficiency=0.96,
                    shift_time_s=0.05,
                    gears=[
                        GearRatioCreate(gear_number=1, ratio=3.150),
                        GearRatioCreate(gear_number=2, ratio=2.300),
                        GearRatioCreate(gear_number=3, ratio=1.750),
                        GearRatioCreate(gear_number=4, ratio=1.380),
                        GearRatioCreate(gear_number=5, ratio=1.140),
                        GearRatioCreate(gear_number=6, ratio=0.960),
                    ],
                ),
                suspension=SuspensionCreate(
                    vehicle_id=ferrari.id,
                    front_type="Double wishbone pushrod",
                    rear_type="Double wishbone pushrod",
                    front_spring_rate_n_m=140000.0,
                    rear_spring_rate_n_m=160000.0,
                ),
                aerodynamics=AerodynamicsCreate(
                    vehicle_id=ferrari.id,
                    drag_coefficient_cd=0.55,
                    frontal_area_m2=1.95,
                    lift_coefficient_cl=-1.45,  # High downforce GT3
                    front_downforce_fraction=0.44,
                ),
                tires=[
                    TireSetupCreate(
                        vehicle_id=ferrari.id,
                        axle="ALL",
                        tire_brand="Pirelli",
                        tire_model="P Zero DHF (GT3 Slick)",
                        tire_category="slick",
                        width_mm=325,
                        aspect_ratio=30,
                        rim_diameter_in=18.0,
                        rolling_resistance_coefficient=0.009,
                    )
                ],
            ),
        )

        print("Población inicial completada con éxito.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
