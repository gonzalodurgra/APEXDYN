import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models.track import TrackVariant, Track
from app.models.vehicle import Vehicle
from app.services.simulation_service import build_vehicle_physics_model, build_track_profile
from app.schemas.endurance import EnduranceRequest
from app.simulation.endurance.endurance_simulator import EnduranceSimulator
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with Session(engine) as s:
    v = s.execute(select(Vehicle).where(Vehicle.model.like('%911%'))).scalar_one_or_none()
    print("Found vehicle:", v.model if v else "None")
    variants = s.execute(select(TrackVariant)).scalars().all()
    for var in variants:
        print(f"Variant: {var.name} (length={var.length_m})")
    
    # Run simulation on all variants with 911 GT3 for 3 laps
    for var in variants:
        print(f"\n--- Running on {var.name} ---")
        v_model = build_vehicle_physics_model(s, v.id)
        t_profile = build_track_profile(s, var.id)
        req = EnduranceRequest(vehicle_id=v.id, variant_id=var.id, race_laps=3)
        sim = EnduranceSimulator(rng_seed=42)
        res = sim.simulate(v_model, t_profile, req)
        print("Status:", res.status, "DNF Reason:", res.reason_dnf)
        print(f"Completed: {res.total_laps_completed} laps. Fuel per lap: {res.fuel_consumption_per_lap_l} L")
        for lh in res.lap_history:
            print(f"  Lap {lh.lap}: fuel={lh.fuel_remaining_l}L, time={lh.lap_time_s}s, brakes_temp={lh.brakes_temp_c}C")

