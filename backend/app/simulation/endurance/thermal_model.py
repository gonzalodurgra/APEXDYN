"""Modelo térmico simplificado por componente.

Implementa un modelo de capacidad térmica de primer orden (lumped-parameter):

    C · dT/dt = Q_gen - Q_diss

Donde:
    C      = capacidad calorífica efectiva (J/K)
    Q_gen  = calor generado por la carga mecánica (W)
    Q_diss = calor disipado (radiación, convección, refrigeración) (W)

Q_diss = (T - T_ambient) × [k_base + k_speed × (v / v_ref)]

El coeficiente de refrigeración aumenta con la velocidad del vehículo
(mayor flujo de aire por conductos y difusores).
"""

from __future__ import annotations

import math
from typing import Dict

from app.simulation.endurance.component_state import ComponentState


# Velocidad de referencia para el escalado de la refrigeración (m/s ≈ 150 km/h)
_V_REF_M_S = 41.67


# ---------------------------------------------------------------------------
# Función principal de actualización térmica
# ---------------------------------------------------------------------------

def update_temperature(
    state: ComponentState,
    load_factor: float,
    speed_m_s: float,
    dt_s: float,
) -> float:
    """Actualiza la temperatura del componente en un paso de tiempo.

    Usa integración Euler de primer orden sobre el modelo de capacidad
    térmica lumped-parameter.

    Args:
        state: Estado mutable del componente (temperature_c se modifica in-place).
        load_factor: Carga normalizada [0..1] (fracción de la carga máxima).
        speed_m_s: Velocidad del vehículo en m/s (afecta a la disipación).
        dt_s: Paso de tiempo en segundos.

    Returns:
        Nueva temperatura del componente en °C.
    """
    if state.thermal_mass_j_k <= 0.0:
        return state.temperature_c

    # Calor generado (proporcional a la carga^1.5 para modelos no lineales simples)
    # La potencia disipada dentro del componente no es perfectamente lineal con la carga
    q_gen = state.heat_gen_coeff * (load_factor ** 1.5)

    # Coeficiente de disipación: base + contribución de velocidad (flujo de aire)
    speed_factor = min(1.0, speed_m_s / _V_REF_M_S)
    effective_cooling = state.cooling_coeff_w_k * (0.4 + 0.6 * speed_factor)

    # Calor disipado
    delta_t = state.temperature_c - state.temp_ambient_c
    q_diss = effective_cooling * delta_t

    # dT/dt = (Q_gen - Q_diss) / C
    dT_dt = (q_gen - q_diss) / state.thermal_mass_j_k

    # Integración Euler (dt_s puede ser >1 para pasos de vuelta completa)
    # Para dt grandes, subdividir en sub-pasos de 10 s para estabilidad
    if dt_s > 20.0:
        sub_dt = 10.0
        n_sub = int(dt_s / sub_dt)
        remainder = dt_s - n_sub * sub_dt
        temp = state.temperature_c
        for _ in range(n_sub):
            delta_t_sub = temp - state.temp_ambient_c
            q_diss_sub = effective_cooling * delta_t_sub
            dT = (q_gen - q_diss_sub) / state.thermal_mass_j_k * sub_dt
            temp += dT
        # Paso restante
        if remainder > 0:
            delta_t_sub = temp - state.temp_ambient_c
            q_diss_sub = effective_cooling * delta_t_sub
            dT = (q_gen - q_diss_sub) / state.thermal_mass_j_k * remainder
            temp += dT
        state.temperature_c = temp
    else:
        state.temperature_c += dT_dt * dt_s

    return state.temperature_c


# ---------------------------------------------------------------------------
# Funciones de efecto de temperatura sobre rendimiento
# ---------------------------------------------------------------------------

def engine_power_factor(temp_c: float, temp_max_c: float, temp_critical_c: float) -> float:
    """Factor de reducción de potencia del motor por temperatura.

    Entre temp_max y temp_critical: reducción lineal de 1.0 a 0.5.
    Por encima de temp_critical: fallo (0.0).
    Por debajo de temp_max: sin penalización (1.0).

    Args:
        temp_c: Temperatura actual del motor en °C.
        temp_max_c: Temperatura máxima sin penalización en °C.
        temp_critical_c: Temperatura de fallo en °C.

    Returns:
        Factor multiplicador de potencia [0.0, 1.0].
    """
    if temp_c <= temp_max_c:
        return 1.0
    if temp_c >= temp_critical_c:
        return 0.0
    # Interpolación lineal: 1.0 en temp_max → 0.5 en temp_critical
    ratio = (temp_c - temp_max_c) / (temp_critical_c - temp_max_c)
    return max(0.0, 1.0 - 0.5 * ratio)


def brake_fade_factor(temp_c: float, temp_optimal_c: float, temp_max_c: float) -> float:
    """Factor de eficacia de frenada por temperatura (brake fade).

    Los frenos tienen un rango óptimo de temperatura. Por debajo del óptimo
    son menos eficaces (frenos fríos). Por encima del máximo también fallan.

    Args:
        temp_c: Temperatura actual de los frenos en °C.
        temp_optimal_c: Temperatura óptima de trabajo en °C.
        temp_max_c: Temperatura de inicio de fade en °C.

    Returns:
        Factor de eficacia [0.4, 1.0].
    """
    if temp_c < 100.0:
        # Frenos fríos: eficacia reducida
        ratio_cold = max(0.0, (temp_c - 25.0) / 75.0)
        return 0.5 + 0.5 * ratio_cold
    if temp_c <= temp_optimal_c:
        return 1.0
    if temp_c <= temp_max_c:
        # Rango de operación normal
        return 1.0
    # Por encima del máximo: fade
    excess = (temp_c - temp_max_c) / max(1.0, temp_optimal_c)
    return max(0.4, 1.0 - 0.6 * min(1.0, excess))


def tire_thermal_grip_factor(
    temp_c: float,
    temp_optimal_c: float,
    temp_max_c: float,
) -> float:
    """Factor de grip del neumático en función de la temperatura.

    Los neumáticos trabajan con una ventana térmica óptima. Fuera de ella
    el grip se reduce.

    Args:
        temp_c: Temperatura actual del neumático en °C.
        temp_optimal_c: Centro de la ventana óptima en °C.
        temp_max_c: Límite superior antes de degradación acelerada en °C.

    Returns:
        Factor de grip [0.5, 1.0].
    """
    opt_low = temp_optimal_c - 20.0
    opt_high = temp_optimal_c + 15.0

    if opt_low <= temp_c <= opt_high:
        return 1.0
    elif temp_c < opt_low:
        ratio = max(0.0, (temp_c - 20.0) / max(1.0, opt_low - 20.0))
        return 0.6 + 0.4 * ratio
    elif temp_c <= temp_max_c:
        ratio = (temp_c - opt_high) / max(1.0, temp_max_c - opt_high)
        return max(0.75, 1.0 - 0.25 * ratio)
    else:
        # Por encima del máximo
        ratio = min(1.0, (temp_c - temp_max_c) / 30.0)
        return max(0.5, 0.75 - 0.25 * ratio)

