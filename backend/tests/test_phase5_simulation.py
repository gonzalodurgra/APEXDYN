"""Tests de la Fase 5: Motor de Simulación Física QSS.

Incluye:
- Tests unitarios del módulo vehicle_physics.py (cálculos de fuerzas sin BD)
- Tests de integración del QSSSimulator con trazados sintéticos
- Test de sanidad del servicio de simulación con datos reales de la BD
"""

from __future__ import annotations

import math
import uuid
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Tests unitarios de vehicle_physics.py (sin BD)
# ---------------------------------------------------------------------------

class TestEngineCurveData:
    """Tests de interpolación de curvas de motor."""

    def _make_curve(self):
        from app.simulation.vehicle_physics import EngineCurveData
        return EngineCurveData(
            rpm_points=[1000, 2000, 3000, 4000, 5000, 6000, 7000],
            torque_nm=  [200,  280,  340,  380,  390,  375,  330],
            power_kw=   [0,    0,    0,    0,    0,    0,    0],   # Se auto-calcularán
        )

    def test_torque_at_known_rpm(self):
        curve = self._make_curve()
        assert curve.torque_at_rpm(4000) == pytest.approx(380.0, abs=1.0)

    def test_torque_interpolated(self):
        curve = self._make_curve()
        t_3500 = curve.torque_at_rpm(3500)
        assert 340 < t_3500 < 390, f"Torque interpolado fuera de rango: {t_3500}"

    def test_torque_at_idle_boundary(self):
        curve = self._make_curve()
        # Fuera del rango inferior → extrapolación plana al primer punto
        t_idle = curve.torque_at_rpm(500)
        assert t_idle == pytest.approx(200.0, abs=5.0)

    def test_power_auto_calculated(self):
        curve = self._make_curve()
        # P = T * omega = T * rpm * pi/30 / 1000
        p_4000 = curve.power_kw_at_rpm(4000)
        expected = 380 * 4000 * math.pi / 30 / 1000
        assert p_4000 == pytest.approx(expected, rel=0.05)


class TestGearData:
    """Tests de la caja de cambios."""

    def _make_gearbox(self):
        from app.simulation.vehicle_physics import GearData
        return GearData(
            gear_ratios=[3.80, 2.36, 1.69, 1.31, 1.03, 0.84],
            final_drive_ratio=3.73,
            efficiency=0.92,
            shift_time_s=0.28,
            tire_radius_m=0.318,
        )

    def test_engine_rpm_in_1st_at_low_speed(self):
        gb = self._make_gearbox()
        # 30 km/h = 8.33 m/s, primera marcha
        rpm = gb.engine_rpm(8.33, gear=1)
        assert 2000 < rpm < 6000, f"RPM en 1ª a 30 km/h fuera de rango: {rpm:.0f}"

    def test_engine_rpm_higher_in_lower_gear(self):
        gb = self._make_gearbox()
        v = 20.0  # m/s
        rpm_1 = gb.engine_rpm(v, gear=1)
        rpm_3 = gb.engine_rpm(v, gear=3)
        rpm_5 = gb.engine_rpm(v, gear=5)
        assert rpm_1 > rpm_3 > rpm_5

    def test_max_speed_in_gear_increases(self):
        gb = self._make_gearbox()
        max_rpm = 7200
        speeds = [gb.max_speed_in_gear(g, max_rpm) for g in range(1, 7)]
        for i in range(len(speeds) - 1):
            assert speeds[i] < speeds[i + 1], "Velocidad máxima no crece con las marchas"

    def test_drive_torque_at_wheel(self):
        gb = self._make_gearbox()
        engine_torque = 380.0  # Nm
        wheel_t_1 = gb.drive_torque_at_wheel(engine_torque, gear=1)
        wheel_t_6 = gb.drive_torque_at_wheel(engine_torque, gear=6)
        assert wheel_t_1 > wheel_t_6, "Torque en rueda debe ser mayor en 1ª marcha"
        # 1ª: 380 * 3.80 * 3.73 * 0.92 ≈ 4960 Nm
        assert wheel_t_1 == pytest.approx(380 * 3.80 * 3.73 * 0.92, rel=0.02)


class TestAeroData:
    """Tests de fuerzas aerodinámicas."""

    def _make_aero(self):
        from app.simulation.vehicle_physics import AeroData
        return AeroData(cd=0.34, frontal_area_m2=2.09, cl=-0.25, front_downforce_fraction=0.40)

    def test_drag_zero_at_rest(self):
        aero = self._make_aero()
        assert aero.drag_force_n(0.0) == pytest.approx(0.0)

    def test_drag_quadratic(self):
        aero = self._make_aero()
        d1 = aero.drag_force_n(10.0)
        d2 = aero.drag_force_n(20.0)
        # Drag es cuadrático: d2 ≈ 4 * d1
        assert d2 == pytest.approx(4 * d1, rel=0.01)

    def test_downforce_positive(self):
        """CL negativo → downforce positivo (hacia el suelo)."""
        aero = self._make_aero()
        df = aero.downforce_n(50.0)
        assert df > 0, "Downforce debe ser positivo con CL negativo"

    def test_drag_at_200kph(self):
        aero = self._make_aero()
        v = 200 / 3.6  # m/s (55.56 m/s)
        drag = aero.drag_force_n(v)
        # 0.5 * 1.225 * 0.34 * 2.09 * (200/3.6)² ≈ 1343 N
        assert 1100 < drag < 1600, f"Drag a 200 km/h fuera de rango razonable: {drag:.0f} N"


class TestVehiclePhysicsModel:
    """Tests del modelo físico completo del vehículo."""

    def _make_vehicle(self):
        from app.simulation.vehicle_physics import (
            VehiclePhysicsModel, EngineCurveData, GearData, AeroData, TireGripData
        )
        curve = EngineCurveData(
            rpm_points=[1000, 3000, 5000, 7000, 9000],
            torque_nm=  [300,  400,  450,  430,  380],
            power_kw=   [0,    0,    0,    0,    0],
        )
        gear = GearData(
            gear_ratios=[3.75, 2.38, 1.72, 1.34, 1.11, 0.96],
            final_drive_ratio=3.75,
            efficiency=0.92,
            tire_radius_m=0.320,
        )
        aero = AeroData(cd=0.34, frontal_area_m2=2.09, cl=-0.25)
        grip = TireGripData(mu_peak_longitudinal=1.25, mu_peak_lateral=1.20)

        return VehiclePhysicsModel(
            vehicle_id="test-vehicle",
            mass_kg=1435.0,
            wheelbase_m=2.457,
            front_mass_fraction=0.38,
            cg_height_m=0.45,
            drive_type="RWD",
            engine_idle_rpm=800.0,
            engine_max_rpm=9000.0,
            engine_curve=curve,
            gearbox=gear,
            aero=aero,
            tire_grip=grip,
        )

    def test_effective_mass_larger_than_mass(self):
        v = self._make_vehicle()
        assert v.effective_mass_kg > v.mass_kg

    def test_weight_correct(self):
        v = self._make_vehicle()
        assert v.weight_n == pytest.approx(1435 * 9.81, rel=0.001)

    def test_rolling_resistance_positive(self):
        v = self._make_vehicle()
        rr = v.rolling_resistance_n(30.0)
        assert rr > 0

    def test_drive_force_positive_in_valid_gear(self):
        v = self._make_vehicle()
        f = v.drive_force_n(20.0, gear=3)
        assert f > 0, "Fuerza de tracción debe ser positiva en marcha válida"

    def test_max_drive_force_selects_best_gear(self):
        v = self._make_vehicle()
        f_max, g_best = v.max_drive_force_n(10.0)  # Baja velocidad → marcha baja
        assert g_best in (1, 2)
        assert f_max > 0

        f_max_hi, g_hi = v.max_drive_force_n(50.0)  # Alta velocidad → marcha alta
        assert g_hi > g_best  # Marcha más alta a mayor velocidad

    def test_max_corner_speed_increases_with_radius(self):
        v = self._make_vehicle()
        v_r50 = v.max_corner_speed_m_s(50.0)
        v_r100 = v.max_corner_speed_m_s(100.0)
        v_r200 = v.max_corner_speed_m_s(200.0)
        assert v_r50 < v_r100 < v_r200

    def test_max_brake_force_positive(self):
        v = self._make_vehicle()
        f_brake = v.max_brake_force_n(30.0)
        assert f_brake > 0

    def test_total_resistance_increases_with_speed(self):
        v = self._make_vehicle()
        r1 = v.total_resistance_n(10.0)
        r2 = v.total_resistance_n(50.0)
        r3 = v.total_resistance_n(100.0)
        assert r1 < r2 < r3


# ---------------------------------------------------------------------------
# Tests de integración del QSS Simulator con trazados sintéticos
# ---------------------------------------------------------------------------

class TestQSSSimulator:
    """Tests del simulador QSS con trazados sintéticos controlados."""

    def _make_vehicle(self):
        from app.simulation.vehicle_physics import (
            VehiclePhysicsModel, EngineCurveData, GearData, AeroData, TireGripData
        )
        curve = EngineCurveData(
            rpm_points=[800, 2000, 4000, 6000, 8000, 9000],
            torque_nm=  [250, 350,  440,  460,  430,  370],
            power_kw=   [0,   0,    0,    0,    0,    0],
        )
        gear = GearData(
            gear_ratios=[3.75, 2.38, 1.72, 1.34, 1.11, 0.96],
            final_drive_ratio=3.75,
            efficiency=0.92,
            tire_radius_m=0.318,
        )
        return VehiclePhysicsModel(
            vehicle_id="test-porsche-gt3",
            mass_kg=1435.0,
            wheelbase_m=2.457,
            front_mass_fraction=0.38,
            cg_height_m=0.44,
            drive_type="RWD",
            engine_idle_rpm=800.0,
            engine_max_rpm=9000.0,
            engine_curve=curve,
            gearbox=gear,
            aero=AeroData(cd=0.34, frontal_area_m2=2.09, cl=-0.25),
            tire_grip=TireGripData(mu_peak_longitudinal=1.25, mu_peak_lateral=1.20),
        )

    def _make_oval_profile(self, lap_length_m: float = 2000.0) -> "TrackProfile":
        from app.simulation.qss_simulator import TrackProfile
        n = 200
        distance = np.linspace(0, lap_length_m, n)
        # Óvalo: rectas (R >> 999) en 0-25%, 50-75%; curvas (R=80m) en 25-50%, 75-100%
        radius = np.full(n, 99999.0)
        radius[50:100] = 80.0  # Curva 1
        radius[150:200] = 80.0  # Curva 2
        grade = np.zeros(n)
        mu = np.ones(n)
        return TrackProfile(
            variant_id="test-oval",
            is_closed_loop=True,
            distance_m=distance,
            radius_m=radius,
            grade_percent=grade,
            surface_mu_factor=mu,
        )

    def _make_hillclimb_profile(self, length_m: float = 5000.0) -> "TrackProfile":
        from app.simulation.qss_simulator import TrackProfile
        n = 300
        distance = np.linspace(0, length_m, n)
        # Tramo de montaña: curvas alternadas con subida continua
        radius = np.full(n, 99999.0)
        for i in range(0, n, 30):
            end = min(i + 15, n)
            r = np.random.choice([60.0, 90.0, 120.0, 200.0])
            radius[i:end] = r
        grade = np.linspace(3.0, 8.0, n)  # Subida progresiva
        mu = np.ones(n)
        return TrackProfile(
            variant_id="test-hillclimb",
            is_closed_loop=False,
            distance_m=distance,
            radius_m=radius,
            grade_percent=grade,
            surface_mu_factor=mu,
        )

    def test_simulation_runs_without_error(self):
        from app.simulation.qss_simulator import QSSSimulator
        vehicle = self._make_vehicle()
        sim = QSSSimulator(vehicle, v_max_cap_m_s=100.0)
        profile = self._make_oval_profile()
        result = sim.simulate(profile)
        assert result.total_time_s > 0

    def test_total_time_positive_and_finite(self):
        from app.simulation.qss_simulator import QSSSimulator
        vehicle = self._make_vehicle()
        sim = QSSSimulator(vehicle)
        profile = self._make_oval_profile(2000)
        result = sim.simulate(profile)
        assert math.isfinite(result.total_time_s)
        assert result.total_time_s > 0

    def test_avg_speed_consistent_with_time_and_distance(self):
        from app.simulation.qss_simulator import QSSSimulator
        vehicle = self._make_vehicle()
        sim = QSSSimulator(vehicle)
        profile = self._make_oval_profile(2000)
        result = sim.simulate(profile)
        # avg_speed = distance / time → debe ser coherente
        expected_avg = 2000 / result.total_time_s
        assert result.avg_speed_m_s == pytest.approx(expected_avg, rel=0.01)

    def test_max_speed_above_min_speed(self):
        from app.simulation.qss_simulator import QSSSimulator
        vehicle = self._make_vehicle()
        sim = QSSSimulator(vehicle)
        profile = self._make_oval_profile()
        result = sim.simulate(profile)
        assert result.max_speed_m_s > result.min_speed_m_s

    def test_heavier_vehicle_is_slower(self):
        """Un vehículo más pesado en el mismo trazado debe ser más lento."""
        from app.simulation.qss_simulator import QSSSimulator
        import copy
        vehicle_light = self._make_vehicle()
        vehicle_heavy = copy.deepcopy(vehicle_light)
        vehicle_heavy.mass_kg = 1800.0

        profile = self._make_oval_profile(2000)

        sim_light = QSSSimulator(vehicle_light)
        sim_heavy = QSSSimulator(vehicle_heavy)

        t_light = sim_light.simulate(profile).total_time_s
        t_heavy = sim_heavy.simulate(profile).total_time_s

        assert t_light < t_heavy, f"Vehículo ligero ({t_light:.2f}s) debe ser más rápido que pesado ({t_heavy:.2f}s)"

    def test_open_stage_does_not_require_periodicity(self):
        """Un tramo abierto (is_closed_loop=False) debe simularse correctamente."""
        from app.simulation.qss_simulator import QSSSimulator
        vehicle = self._make_vehicle()
        sim = QSSSimulator(vehicle)
        profile = self._make_hillclimb_profile(5000)
        result = sim.simulate(profile)
        assert result.total_time_s > 0
        assert result.avg_speed_m_s < 80.0  # Subida → velocidad media menor

    def test_sector_times_sum_to_total(self):
        from app.simulation.qss_simulator import QSSSimulator
        vehicle = self._make_vehicle()
        sim = QSSSimulator(vehicle)
        profile = self._make_oval_profile(2000)
        result = sim.simulate(profile, num_sectors=3)
        sector_sum = sum(result.sector_times_s)
        assert sector_sum == pytest.approx(result.total_time_s, rel=0.05)

    def test_wet_surface_makes_slower(self):
        """Superficie mojada (μ reducido) debe generar tiempos más lentos."""
        from app.simulation.qss_simulator import QSSSimulator
        import copy
        vehicle = self._make_vehicle()

        profile_dry = self._make_oval_profile(2000)
        profile_wet = copy.deepcopy(profile_dry)
        profile_wet.surface_mu_factor = np.full(len(profile_dry.distance_m), 0.65)

        sim = QSSSimulator(vehicle)
        t_dry = sim.simulate(profile_dry).total_time_s
        t_wet = sim.simulate(profile_wet).total_time_s

        assert t_wet > t_dry, f"Mojado ({t_wet:.2f}s) debe ser más lento que seco ({t_dry:.2f}s)"


# ---------------------------------------------------------------------------
# Tests de sanidad del servicio de simulación (requiere BD activa)
# ---------------------------------------------------------------------------

class TestSimulationServiceSanity:
    """Tests que requieren conexión a la BD. Se marcan como integración."""

    @pytest.mark.integration
    def test_build_vehicle_physics_model_from_db(self, db_session):
        """Verifica que se puede construir el modelo físico de un vehículo de la BD."""
        from sqlalchemy import select
        from app.models.vehicle import Vehicle
        from app.services.simulation_service import build_vehicle_physics_model

        vehicle = db_session.execute(select(Vehicle).limit(1)).scalar_one_or_none()
        if vehicle is None:
            pytest.skip("No hay vehículos en la BD de test.")

        model = build_vehicle_physics_model(db_session, vehicle.id)
        assert model.mass_kg == pytest.approx(vehicle.mass_kg, rel=0.001)
        assert model.vehicle_id == str(vehicle.id)

    @pytest.mark.integration
    def test_build_track_profile_requires_geometry(self, db_session):
        """Verifica que sin puntos de geometría se lanza ValueError."""
        from sqlalchemy import select
        from app.models.track import TrackVariant
        from app.services.simulation_service import build_track_profile

        # Buscar una variante sin puntos
        variant = db_session.execute(
            select(TrackVariant).limit(1)
        ).scalar_one_or_none()

        if variant is None:
            pytest.skip("No hay variantes en la BD de test.")

        if len(variant.points) == 0:
            with pytest.raises(ValueError, match="geometría procesada"):
                build_track_profile(db_session, variant.id)
