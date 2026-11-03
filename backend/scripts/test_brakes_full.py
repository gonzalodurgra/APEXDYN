"""Debug script to trace brakes wear in a FULL endurance simulation."""
import sys
sys.path.insert(0, '.')
import os
os.environ.setdefault('DOCS_API_KEY', 'test')
os.environ.setdefault('JWT_SECRET_KEY', 'test')
os.environ.setdefault('JWT_ALGORITHM', 'HS256')

# Monkey-patch compute_wear_delta to track brakes calls
import app.simulation.endurance.wear_model as wm_mod
original_compute = wm_mod.compute_wear_delta

call_count = [0]
def traced_compute(state, conditions, dt_s):
    result = original_compute(state, conditions, dt_s)
    if state.name == 'brakes':
        call_count[0] += 1
        if call_count[0] <= 5 or call_count[0] % 100 == 0:
            print(f"  [wear] brakes call#{call_count[0]}: before life_consumed={state.life_consumed:.5f}, d_life={result:.5f}")
    return result

wm_mod.compute_wear_delta = traced_compute

# Also patch the simulator module's reference
import app.simulation.endurance.endurance_simulator as sim_mod
sim_mod.compute_wear_delta = traced_compute

# Now run a short simulation (10 laps of Le Mans-ish track)
from app.simulation.vehicle_physics import VehiclePhysicsModel, EngineModel, AeroModel, TyreModel, ChassisModel
from app.simulation.qss_simulator import TrackProfile
from app.simulation.endurance.endurance_simulator import EnduranceSimulator
from app.schemas.endurance import EnduranceRequest, EnduranceStrategyInput

# Simple test vehicle
engine = EngineModel(
    displacement_cc=3996, cylinders=6, aspiration='na',
    max_power_kw=375.0, max_torque_nm=430.0,
    peak_power_rpm=8500, peak_torque_rpm=6100,
    power_curve={1000: 50, 3000: 200, 5000: 320, 7000: 375, 8500: 360},
    idle_rpm=750, redline_rpm=9000,
)
vehicle = VehiclePhysicsModel(
    vehicle_id='test-911',
    make='Porsche', model='911 GT3',
    year=2022, mass_kg=1418.0,
    engine=engine,
    aero=AeroModel(cd=0.31, frontal_area_m2=1.98, cl=0.4, downforce_factor=1.0),
    tyres=TyreModel(width_mm=265, aspect_ratio=35, rim_in=20, compound='slick', mu_static=1.4, mu_dynamic=1.25),
    chassis=ChassisModel(wheelbase_m=2.457, track_width_m=1.532, cg_height_m=0.42, weight_dist_front=0.38, drag_coeff=0.31),
    drivetrain_type='rwd', drivetrain_efficiency=0.92,
    gears=[3.15, 2.29, 1.72, 1.31, 1.08, 0.88],
    final_drive=3.44,
    fuel_capacity_l=90.0,
)

track = TrackProfile(
    name='Le Mans', variant_id='le-mans',
    total_length_m=13626.0,
    sectors=[{'name': 'S1', 'length_m': 4500, 'max_speed_kmh': 320, 'avg_curvature': 0.015, 'inclination_deg': 0.1},
             {'name': 'S2', 'length_m': 4500, 'max_speed_kmh': 290, 'avg_curvature': 0.04, 'inclination_deg': -0.2},
             {'name': 'S3', 'length_m': 4626, 'max_speed_kmh': 330, 'avg_curvature': 0.01, 'inclination_deg': 0.1}],
    altitude_m=50.0,
)

strategy_input = EnduranceStrategyInput(
    tank_capacity_l=90.0,
    tire_wear_threshold=0.80,
    brake_wear_threshold=0.80,
)

request = EnduranceRequest(
    vehicle_id='test-911',
    track_variant_id='le-mans',
    race_laps=10,
    ambient_temp_c=20.0,
    driver_aggression=1.0,
    power_mode=1.0,
    bsfc_g_kwh=270.0,
    initial_fuel_l=90.0,
    strategy=strategy_input,
    weibull_seed=42,
)

sim = EnduranceSimulator(rng_seed=42)
result = sim.simulate(vehicle, track, request)

brakes_status = result.components.get('brakes')
print(f"\n=== RESULT: brakes wear = {brakes_status.wear_percent}%, life_consumed = {brakes_status.life_consumed_hours}h ===")
print(f"Total laps: {result.total_laps_completed}, Status: {result.status}")
print(f"Lap 1 brake_wear_percent: {result.lap_history[0].brake_wear_percent}%")
if len(result.lap_history) > 1:
    print(f"Lap 2 brake_wear_percent: {result.lap_history[1].brake_wear_percent}%")
if len(result.lap_history) >= 5:
    print(f"Lap 5 brake_wear_percent: {result.lap_history[4].brake_wear_percent}%")
print(f"Total brakes wear calls: {call_count[0]}")

