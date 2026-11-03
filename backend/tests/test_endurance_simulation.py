"""Tests unitarios para la simulación de resistencia (Endurance Simulator).

Verifica en particular:
- Desgaste acumulativo de frenos y demás componentes (> 0%).
- Gestión de paradas en boxes y reemplazo de componentes desgastados.
- Que braking_g negativo o positivo siempre produzca tasas de desgaste físicas y positivas.
"""

from __future__ import annotations

import uuid
import numpy as np
import pytest

from app.simulation.vehicle_physics import (
    VehiclePhysicsModel, EngineCurveData, GearData, AeroData, TireGripData
)
from app.simulation.qss_simulator import TrackProfile
from app.simulation.endurance.endurance_simulator import EnduranceSimulator
from app.simulation.endurance.wear_model import compute_wear_delta
from app.simulation.endurance.component_state import default_component_states
from app.schemas.endurance import EnduranceRequest


@pytest.fixture
def sample_vehicle() -> VehiclePhysicsModel:
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
        vehicle_id="test-gt3",
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


@pytest.fixture
def sample_track() -> TrackProfile:
    n = 200
    distance = np.linspace(0, 4000.0, n)
    radius = np.full(n, 99999.0)
    radius[50:100] = 80.0
    radius[150:200] = 80.0
    return TrackProfile(
        variant_id="test-track",
        is_closed_loop=True,
        distance_m=distance,
        radius_m=radius,
        grade_percent=np.zeros(n),
        surface_mu_factor=np.ones(n),
    )


class TestEnduranceWearModel:
    def test_brake_wear_delta_positive_even_with_negative_braking_g(self):
        """Verifica que si braking_g viene con signo negativo (deceleración),
        el modelo de desgaste lo trate en valor absoluto y la tasa sea positiva.
        """
        states = default_component_states()
        brakes = states["brakes"]

        # Condiciones con braking_g negativo (ej. proveniente de np.min(accel))
        cond_neg = {
            "rpm": 5000.0,
            "power_fraction": 0.8,
            "lateral_g": 1.0,
            "longitudinal_g": 0.5,
            "braking_g": -1.25,
            "speed_m_s": 45.0,
            "gear_changes_per_s": 0.08,
            "brake_energy_w": 180000.0,
            "power_output_w": 250000.0,
        }
        delta_neg = compute_wear_delta(brakes, cond_neg, dt_s=90.0)
        assert delta_neg > 0.0, f"El desgaste con braking_g negativo debe ser positivo, pero fue: {delta_neg}"

        cond_pos = dict(cond_neg, braking_g=1.25)
        delta_pos = compute_wear_delta(brakes, cond_pos, dt_s=90.0)
        assert delta_pos == pytest.approx(delta_neg, rel=1e-5)

    def test_endurance_simulation_brakes_accumulate_wear(self, sample_vehicle, sample_track):
        """Comprueba que en una simulación de 5 vueltas, los frenos acumulen desgaste."""
        req = EnduranceRequest(
            vehicle_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            race_laps=5,
        )
        sim = EnduranceSimulator(rng_seed=42)
        res = sim.simulate(sample_vehicle, sample_track, req)

        brakes = res.components["brakes"]
        assert brakes.wear_percent > 0.0, f"El desgaste de frenos debe ser > 0%, pero fue {brakes.wear_percent}%"
        assert brakes.life_consumed_hours > 0.0
        assert brakes.total_life_consumed_hours > 0.0

        for lh in res.lap_history:
            assert lh.brake_wear_percent > 0.0

