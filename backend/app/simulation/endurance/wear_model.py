"""Modelo de desgaste acumulativo dependiente de las condiciones de operación.

Cada componente tiene su propia ley de desgaste basada en los factores físicos
relevantes (carga mecánica, temperatura, RPM, ciclos de trabajo, etc.).

La tasa de desgaste se expresa en fracción de vida útil por segundo [s⁻¹],
de forma que integrada en el tiempo produce wear_fraction ∈ [0, 1].

También acumula life_consumed en horas (para la función de riesgo Weibull),
ya que η está calibrado en horas de carrera a ritmo sostenido.
"""

from __future__ import annotations

import math
from typing import Dict, Any

from app.simulation.endurance.component_state import ComponentState


# ---------------------------------------------------------------------------
# Condiciones de operación (dict tipado)
# ---------------------------------------------------------------------------

def compute_wear_delta(
    state: ComponentState,
    conditions: Dict[str, float],
    dt_s: float,
) -> float:
    """Calcula el incremento de life_consumed en este paso de tiempo.

    Args:
        state: Estado del componente (no se modifica aquí; solo se lee).
        conditions: Diccionario con las condiciones de operación:
            - rpm: RPM del motor
            - power_fraction: Fracción de potencia solicitada [0..1]
            - lateral_g: Aceleración lateral [g]
            - longitudinal_g: Aceleración longitudinal [g] (positiva = aceleración)
            - braking_g: Aceleración de frenada [g] (positiva = frenando)
            - speed_m_s: Velocidad del vehículo [m/s]
            - gear_changes_per_s: Cambios de marcha por segundo
            - brake_energy_w: Potencia disipada en frenos [W]
            - power_output_w: Potencia entregada en ruedas [W]
            - temperature_c: Temperatura del componente (desde state)
        dt_s: Paso de tiempo en segundos.

    Returns:
        Incremento de life_consumed en horas. Acumular en state.life_consumed.
    """
    name = state.name
    T = state.temperature_c

    rpm           = conditions.get("rpm", 3000.0)
    power_frac    = max(0.0, conditions.get("power_fraction", 0.5))
    lat_g         = abs(conditions.get("lateral_g", 0.5))
    long_g        = abs(conditions.get("longitudinal_g", 0.3))
    braking_g     = abs(conditions.get("braking_g", 0.3))
    speed_m_s     = max(0.0, conditions.get("speed_m_s", 30.0))
    gear_ch_s     = max(0.0, conditions.get("gear_changes_per_s", 0.05))
    brake_energy  = max(0.0, conditions.get("brake_energy_w", 50000.0))
    power_w       = max(0.0, conditions.get("power_output_w", 200000.0))

    # Factor de temperatura: acelera el desgaste al superar la temperatura máxima
    # Basado en la ley de Arrhenius simplificada: cada 30°C multiplica por e
    t_excess = max(0.0, T - state.temp_max_c)
    thermal_accel = math.exp(min(5.0, t_excess / 30.0))  # Tope físico para evitar overflow (máx ~148x)

    # Tasa de desgaste base en vida_consumida/segundo → convertir a horas
    dt_h = dt_s / 3600.0

    # ---- Fórmula por componente ----
    if name == "engine":
        # Desgaste por RPM elevadas + carga
        rpm_factor = max(0.0, (rpm - 2000.0) / 6000.0) ** 1.5
        wear_rate = (0.5 + 0.5 * power_frac) * (1.0 + rpm_factor) * thermal_accel

    elif name == "turbo":
        # Alta temperatura + RPM del compresor (proporcional a RPM motor en turbo)
        rpm_factor = (rpm / 7000.0) ** 2.0
        wear_rate = (0.4 + 0.6 * power_frac) * (1.0 + 2.0 * rpm_factor) * thermal_accel

    elif name == "gearbox":
        # Ciclos de cambio + par transmitido
        shift_factor = 1.0 + 10.0 * gear_ch_s   # cada cambio acelera desgaste
        torque_factor = 0.3 + 0.7 * power_frac
        wear_rate = shift_factor * torque_factor * thermal_accel

    elif name == "clutch":
        # Principalmente deslizamiento: más cambios = más desgaste
        slip_factor = 1.0 + 15.0 * gear_ch_s
        wear_rate = slip_factor * (0.5 + 0.5 * power_frac) * thermal_accel

    elif name == "transmission":
        # Par lateral (AWD/RWD) + velocidad
        lat_factor = 1.0 + 0.5 * lat_g
        wear_rate = (0.4 + 0.6 * power_frac) * lat_factor * thermal_accel

    elif name == "cooling":
        # Temperatura del motor + carga continuada
        temp_ratio = max(0.0, (T - state.temp_optimal_c) / max(1.0, state.temp_max_c - state.temp_optimal_c))
        wear_rate = (0.3 + 0.7 * temp_ratio ** 2) * thermal_accel

    elif name == "lubrication":
        # Degradación del aceite: temperatura + RPM + tiempo
        rpm_factor = (rpm / 6000.0) ** 1.2
        wear_rate = (0.4 + 0.6 * rpm_factor) * thermal_accel

    elif name == "brakes":
        # Energía de frenada + temperatura
        energy_factor = min(1.0, brake_energy / 200000.0)  # normalizado a 200 kW ref
        wear_rate = (0.2 + 0.8 * energy_factor) * (1.0 + 2.0 * braking_g) * thermal_accel

    elif name == "suspension":
        # Cargas laterales y longitudinales en superficies rugosas
        g_total = math.sqrt(lat_g ** 2 + long_g ** 2 + braking_g ** 2)
        wear_rate = (0.2 + 0.8 * min(1.0, g_total / 3.0)) * thermal_accel

    elif name == "tyres":
        # Deslizamiento lateral y longitudinal: el desgaste de neumático se controla
        # también desde tire_model, pero aquí usamos la misma lógica para life_consumed
        g_total = math.sqrt(lat_g ** 2 + long_g ** 2 + braking_g ** 2)
        wear_rate = (0.3 + 0.7 * min(1.0, g_total / 2.5)) * thermal_accel

    elif name == "electrical":
        # Relativamente constante; picos a alta velocidad por vibraciones
        speed_factor = 0.5 + 0.5 * min(1.0, speed_m_s / 60.0)
        wear_rate = speed_factor * thermal_accel

    else:
        # Genérico
        wear_rate = (0.5 + 0.5 * power_frac) * thermal_accel

    # life_consumed_delta en horas = wear_rate (adimensional ×) × dt_h
    # wear_rate está calibrado para que wear_rate=1.0 consume ~1 vida en η horas
    return max(0.0, wear_rate * dt_h)

