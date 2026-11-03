"""Debug script to trace brakes wear in endurance simulation."""
import sys
sys.path.insert(0, '.')

from app.simulation.endurance.component_state import default_component_states
from app.simulation.endurance.wear_model import compute_wear_delta

states = default_component_states(ambient_temp_c=25.0)
st = states['brakes']
print('brakes state initial:', st.name, 'temp=', st.temperature_c, 'life_consumed=', st.life_consumed, 'wear_fraction=', st.wear_fraction)

conditions = {
    'rpm': 5000.0,
    'power_fraction': 0.8,
    'lateral_g': 1.0,
    'longitudinal_g': 0.5,
    'braking_g': 1.1,
    'speed_m_s': 50.0,
    'gear_changes_per_s': 0.08,
    'brake_energy_w': 180000.0,
    'power_output_w': 300000.0,
}

d = compute_wear_delta(st, conditions, 120.0)
print(f'compute_wear_delta = {d:.6f} h per lap (120s)')
print(f'wear_fraction increment per lap = {d / st.life_eta:.6f}')
print(f'after 720 laps (24h): life_consumed={d*720:.2f}h, wear_fraction={min(1.0, d*720/st.life_eta)*100:.1f}%')

# Now simulate the loop updating state in-place like endurance_simulator.py does
print("\n--- Simulating 10 laps in-place ---")
life_before = st.life_consumed
for lap in range(1, 11):
    d_life = compute_wear_delta(st, conditions, 120.0)
    st.life_consumed = max(0.0, st.life_consumed + d_life)
    st.wear_fraction = max(0.0, min(1.0, st.life_consumed / st.life_eta)) if st.life_eta > 0 else 1.0
    print(f"  Lap {lap}: d_life={d_life:.5f}, life_consumed={st.life_consumed:.5f}, wear_fraction={st.wear_fraction*100:.2f}%")

# Verify states dict reference
print("\n--- Dict reference test ---")
states2 = default_component_states(ambient_temp_c=25.0)
for c_name, s in states2.items():
    if c_name == 'brakes':
        d_life = compute_wear_delta(s, conditions, 120.0)
        s.life_consumed = max(0.0, s.life_consumed + d_life)
        s.wear_fraction = max(0.0, min(1.0, s.life_consumed / s.life_eta))
        print(f"  After dict-loop update: states2['brakes'].life_consumed={states2['brakes'].life_consumed:.5f}, wear_fraction={states2['brakes'].wear_fraction*100:.2f}%")

