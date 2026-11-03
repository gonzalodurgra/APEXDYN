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

    Usa la solución analítica exacta de la ecuación diferencial de 1er orden:
        C · dT/dt = Q_gen - k_cooling · (T - T_ambient)

    Solución exacta entre t0 y t0 + dt:
        T_inf = T_ambient + Q_gen / k_cooling
        T(t0 + dt) = T_inf + (T(t0) - T_inf) · exp(- (k_cooling / C) · dt)

    Esto es incondicionalmente estable para cualquier tamaño de paso dt_s (> 0),
    evitando oscilaciones y divergencias numéricas en frenos y componentes rápidos.
    """
    if state.thermal_mass_j_k <= 0.0 or dt_s <= 0.0:
        return state.temperature_c

    # Calor generado W
    q_gen = state.heat_gen_coeff * (max(0.0, load_factor) ** 1.5)

    # Coeficiente efectivo de disipación W/K
    speed_factor = min(1.0, max(0.0, speed_m_s) / _V_REF_M_S)
    effective_cooling = state.cooling_coeff_w_k * (0.4 + 0.6 * speed_factor)

    if effective_cooling <= 1e-6:
        # Sin disipación: calentamiento puro
        state.temperature_c += (q_gen / state.thermal_mass_j_k) * dt_s
    else:
        # Temperatura de equilibrio asintótico
        t_equilibrium = state.temp_ambient_c + (q_gen / effective_cooling)
        # Factor de decaimiento exponencial
        tau = state.thermal_mass_j_k / effective_cooling
        decay = math.exp(-min(50.0, dt_s / tau))
        state.temperature_c = t_equilibrium + (state.temperature_c - t_equilibrium) * decay

    # Clamping físico de seguridad (nunca menor que ambiente ni mayor que 1500°C)
    state.temperature_c = max(state.temp_ambient_c, min(1500.0, state.temperature_c))

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

