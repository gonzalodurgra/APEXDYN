import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models.track import TrackVariant
from app.models.vehicle import Vehicle
from app.services.simulation_service import build_vehicle_physics_model, build_track_profile
from app.schemas.endurance import EnduranceRequest
from app.simulation.endurance.endurance_simulator import EnduranceSimulator
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with Session(engine) as s:
    v = s.execute(select(Vehicle).where(Vehicle.model.like('%911%'))).scalar_one_or_none()
    t = s.execute(select(TrackVariant).where(TrackVariant.name.like('%Completo%'))).scalar_one_or_none()
    v_model = build_vehicle_physics_model(s, v.id)
    t_profile = build_track_profile(s, t.id)
    from app.simulation.endurance.component_state import default_component_states
    req = EnduranceRequest(vehicle_id=v.id, variant_id=t.id, race_duration_hours=24.0)
    sim = EnduranceSimulator(rng_seed=42)
    res = sim.simulate(v_model, t_profile, req)
    print("res.components['brakes'] wear_percent:", res.components['brakes'].wear_percent)
    print("res.components['brakes'] life_consumed_hours:", res.components['brakes'].life_consumed_hours)
    for i in range(5):
        print(f"Lap {i+1} brake wear in history:", res.lap_history[i].brake_wear_percent)




