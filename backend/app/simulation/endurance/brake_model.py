"""Modelo específico de frenos: desgaste, disipación y fatiga térmica (fade)."""

from __future__ import annotations
import math

def brake_wear_rate(brake_power_w: float, temp_c: float, base_wear_rate: float = 0.0001) -> float:
    """Calcula el incremento de desgaste de pastillas/discos por segundo."""
    energy_factor = min(2.0, brake_power_w / 150000.0)
    thermal_factor = 1.0
    if temp_c > 650.0:
        thermal_factor += ((temp_c - 650.0) / 150.0) ** 1.8
    return base_wear_rate * (0.2 + 0.8 * energy_factor) * thermal_factor

def brake_effectiveness(wear_fraction: float, temp_c: float, temp_optimal_c: float = 380.0, temp_max_c: float = 750.0) -> float:
    """Calcula la eficacia de frenada instantánea [0..1]."""
    if wear_fraction > 0.80:
        w_factor = max(0.5, 1.0 - 0.5 * ((wear_fraction - 0.80) / 0.20))
    else:
        w_factor = 1.0

    if temp_c < 120.0:
        t_factor = 0.6 + 0.4 * (temp_c / 120.0)
    elif temp_c <= temp_max_c:
        t_factor = 1.0
    else:
        # Fade térmico severo
        excess = (temp_c - temp_max_c) / 200.0
        t_factor = max(0.35, 1.0 - 0.65 * min(1.0, excess))

    return round(w_factor * t_factor, 4)

