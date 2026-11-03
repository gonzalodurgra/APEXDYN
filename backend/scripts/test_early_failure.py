"""Test early brakes failure hypothesis."""
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('DOCS_API_KEY', 'test')
os.environ.setdefault('JWT_SECRET_KEY', 'test')
os.environ.setdefault('JWT_ALGORITHM', 'HS256')

import math
import numpy as np
from app.simulation.endurance.component_state import default_component_states
from app.simulation.endurance.failure_model import sample_failure, hazard_rate

states = default_component_states(25.0)
st = states['brakes']
rng = np.random.default_rng(42)
dt_h = 120.0 / 3600.0

print(f'Brakes: life_eta={st.life_eta}, life_beta={st.life_beta}')
print(f'Note: sample_failure is called with st.life_consumed AFTER wear is added')
print()

# Simulate first 5 laps
# In real sim, failure is checked AFTER wear has been added (line 241 uses updated life_consumed)
for lap in range(1, 10):
    # Add wear first (like the real sim does)
    d = 0.098  # approximate per-lap delta
    st.life_consumed = max(0.0, st.life_consumed + d)
    st.wear_fraction = min(1.0, st.life_consumed / st.life_eta)

    h = hazard_rate(st.life_consumed, st.life_eta, st.life_beta)
    p_fail = 1.0 - math.exp(-h * dt_h)
    
    # sample_failure draws a random number each call
    u_before = rng.random()  # simulate what rng draws
    rng2 = np.random.default_rng(42 + lap)  # fresh rng for display
    
    print(f'Lap {lap}: life_consumed={st.life_consumed:.4f}h, h={h:.6f}, p_fail={p_fail*100:.4f}%')

print()
print("Now simulating multiple seeds to see how often brakes fail in first 3 laps:")
early_failures = 0
total_sims = 10000
for seed in range(total_sims):
    rng_s = np.random.default_rng(seed)
    s = default_component_states(25.0)['brakes']
    failed_early = False
    for lap in range(1, 4):
        d = 0.098
        s.life_consumed += d
        s.wear_fraction = min(1.0, s.life_consumed / s.life_eta)
        # ALL other components also draw from rng, so we need to simulate that
        # For simplicity, approximate: 10 components x 1 draw each = 10 draws per lap
        for _ in range(9):  # 9 other components
            rng_s.random()
        if sample_failure(s, rng_s, dt_h):
            early_failures += 1
            failed_early = True
            break

print(f"Brakes failed in first 3 laps: {early_failures}/{total_sims} = {early_failures/total_sims*100:.2f}%")
print()
print("Also checking: if failed at lap 1, does wear stay 0?")
s2 = default_component_states(25.0)['brakes']
s2.failed = True
s2.life_consumed = 0.098  # just added
s2.wear_fraction = 0.098 / 12.0

# Next lap: the loop checks st.failed first
print(f"Before lap 2: failed={s2.failed}, life_consumed={s2.life_consumed:.4f}, wear%={s2.wear_fraction*100:.2f}%")
if s2.failed:
    print("-> 'continue' is executed - wear NOT accumulated in lap 2")
    print("-> wear stays at 0.82% after lap 1, even though displayed as last lap value")

