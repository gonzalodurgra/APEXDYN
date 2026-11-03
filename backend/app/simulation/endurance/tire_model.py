"""Modelo específico para neumáticos: desgaste y degradación de agarre."""

from __future__ import annotations
import math

def tire_wear_rate(lateral_g: float, longitudinal_g: float, temp_c: float, base_wear_rate: float = 0.0002) -> float:
    """Calcula la tasa de desgaste instantánea por segundo."""
    g_total = math.sqrt(lateral_g**2 + longitudinal_g**2)
    thermal_factor = 1.0
    if temp_c > 105.0:
        thermal_factor += ((temp_c - 105.0) / 25.0) ** 1.5
    elif temp_c < 70.0:
        thermal_factor += 0.2  # Grain / cold tearing
    return base_wear_rate * (1.0 + 1.8 * g_total) * thermal_factor

def tire_grip_factor(wear_fraction: float, temp_c: float, temp_optimal_c: float = 90.0) -> float:
    """Calcula el factor de agarre considerando desgaste y ventana térmica."""
    # Desgaste
    if wear_fraction < 0.60:
        w_grip = 1.0 - 0.05 * (wear_fraction / 0.60)
    elif wear_fraction < 0.85:
        w_grip = 0.95 - 0.20 * ((wear_fraction - 0.60) / 0.25)
    else:
        w_grip = max(0.40, 0.75 * math.exp(-3.5 * (wear_fraction - 0.85)))

    # Térmica
    d_temp = abs(temp_c - temp_optimal_c)
    if d_temp <= 15.0:
        t_grip = 1.0
    elif d_temp <= 35.0:
        t_grip = 1.0 - 0.15 * ((d_temp - 15.0) / 20.0)
    else:
        t_grip = max(0.50, 0.85 - 0.35 * min(1.0, (d_temp - 35.0) / 30.0))

    return round(w_grip * t_grip, 4)

