"""Standalone test for the endurance simulator brakes wear bug."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DOCS_API_KEY', 'test')
os.environ.setdefault('JWT_SECRET_KEY', 'test')
os.environ.setdefault('JWT_ALGORITHM', 'HS256')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')

# Minimal VehiclePhysicsModel stub
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import numpy as np

# We import the actual model
from app.simulation.endurance.component_state import default_component_states
from app.simulation.endurance.wear_model import compute_wear_delta
from app.simulation.endurance.thermal_model import update_temperature
from app.simulation.endurance.strategy_engine import PitStopStrategy, should_pit, execute_pit_stop

@dataclass
class _FakeQSS:
    total_time_s: float = 220.0
    avg_speed_m_s: float = 62.0
    max_lateral_g: float = 1.5
    max_longitudinal_accel_g: float = 0.9
    max_braking_g: float = 1.3
    engine_rpm_profile: list = field(default_factory=lambda: [5500.0])

# Simulate just the wear loop as in endurance_simulator.py
ambient = 20.0
states = default_component_states(ambient_temp_c=ambient)

strategy = PitStopStrategy(
    tank_capacity_l=90.0,
    tire_wear_threshold=0.80,
    brake_wear_threshold=0.80,
)

base_lap_time = 220.0
avg_speed_m_s = 62.0
max_lat_g = 1.5
max_long_g = 0.9
max_brake_g = 1.3
avg_rpm = 5500.0
power_factor = 0.9
aggression = 1.0
tire_grip = 0.95
brake_eff = 0.95
fuel_remaining_l = 90.0
est_lap_fuel = 5.2

race_time_s = 0.0
target_laps = 10

for lap in range(1, target_laps + 1):
    lap_time_s = base_lap_time
    lap_speed = avg_speed_m_s

    conditions = {
        "rpm": avg_rpm * power_factor,
        "power_fraction": power_factor,
        "lateral_g": max_lat_g * tire_grip * aggression,
        "longitudinal_g": max_long_g * tire_grip,
        "braking_g": max_brake_g * brake_eff * aggression,
        "speed_m_s": lap_speed,
        "gear_changes_per_s": 0.08,
        "brake_energy_w": 180000.0 * aggression,
        "power_output_w": 200000.0,
    }

    # C. Thermal
    update_temperature(states["brakes"], load_factor=aggression * 0.85, speed_m_s=lap_speed, dt_s=lap_time_s)

    # D. Wear loop
    for c_name, st in states.items():
        if st.failed:
            continue
        d_life_consumed = compute_wear_delta(st, conditions, lap_time_s)
        st.life_consumed = max(0.0, st.life_consumed + d_life_consumed)
        st.wear_fraction = max(0.0, min(1.0, st.life_consumed / st.life_eta)) if st.life_eta > 0 else 1.0
        if c_name == 'brakes':
            print(f"  In-loop: id(st)={id(st)}, id(states['brakes'])={id(states['brakes'])}, same={st is states['brakes']}")
            print(f"  Lap {lap}: d_life={d_life_consumed:.5f}, life_consumed={st.life_consumed:.5f}, wear={st.wear_fraction*100:.2f}%")

    # E. Pit stop
    need_pit, reason = should_pit(lap, states, fuel_remaining_l, est_lap_fuel, strategy)
    if need_pit:
        print(f"  PIT LAP {lap}: reason={reason}, brakes_before={states['brakes'].life_consumed:.5f}")
        states, fuel_remaining_l, pit_dur, record = execute_pit_stop(
            lap=lap, race_time_s=race_time_s, states=states,
            fuel_remaining_l=fuel_remaining_l, strategy=strategy, reason=reason
        )
        print(f"  PIT after: brakes life_consumed={states['brakes'].life_consumed:.5f}")

    # Check id consistency
    race_time_s += lap_time_s
    print(f"  End lap {lap}: states['brakes'].life_consumed={states['brakes'].life_consumed:.5f}, wear={states['brakes'].wear_fraction*100:.2f}%")

print(f"\n=== FINAL: brakes wear={states['brakes'].wear_fraction*100:.2f}%, life_consumed={states['brakes'].life_consumed:.4f}h ===")

