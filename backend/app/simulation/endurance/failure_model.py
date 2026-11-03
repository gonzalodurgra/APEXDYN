"""Modelo probabilístico de fallos mediante distribuciones de Weibull.

La distribución de Weibull es el modelo estándar en fiabilidad de ingeniería
para modelar el tiempo hasta el fallo de componentes mecánicos.

CDF: F(t) = 1 - exp[-(t/η)^β]
Tasa de riesgo: h(t) = (β/η) × (t/η)^(β-1)

Donde:
    t = vida consumida acumulada (horas)
    η = escala (vida característica en horas)
    β = forma (β<1: fallos tempranos, β=1: fallo aleatorio, β>1: desgaste)

Estrategia de muestreo (evitar tiradas independientes por paso):
    En cada vuelta se calcula la tasa de riesgo instantánea h(t) y la probabilidad
    de fallo en el intervalo Δt:

        P_fail = 1 - exp(-h(t) × Δt)

    Luego se compara con una muestra U ~ Uniform(0,1) del generador seeded.
    Esto es equivalente a la discretización correcta del proceso de Poisson
    no homogéneo, y permite reproducir resultados con la misma semilla.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np

from app.simulation.endurance.component_state import ComponentState


# ---------------------------------------------------------------------------
# Funciones básicas de Weibull
# ---------------------------------------------------------------------------

def hazard_rate(life_consumed: float, eta: float, beta: float) -> float:
    """Tasa de riesgo instantánea de Weibull h(t) en [1/hora].

    Args:
        life_consumed: Vida consumida acumulada t (en horas).
        eta: Escala Weibull η (en horas).
        beta: Forma Weibull β.

    Returns:
        Tasa de riesgo h(t) = (β/η) × (t/η)^(β-1)  [1/hora].
        Retorna 0.0 si life_consumed ≤ 0 o eta ≤ 0.
    """
    if life_consumed <= 0.0 or eta <= 0.0 or beta <= 0.0:
        return 0.0
    t_norm = life_consumed / eta
    return (beta / eta) * (t_norm ** (beta - 1.0))


def survival_probability(life_consumed: float, eta: float, beta: float) -> float:
    """Probabilidad de supervivencia S(t) = 1 - F(t) = exp[-(t/η)^β].

    Args:
        life_consumed: Vida consumida acumulada t (en horas).
        eta: Escala Weibull η.
        beta: Forma Weibull β.

    Returns:
        Probabilidad de supervivencia ∈ [0, 1].
    """
    if life_consumed <= 0.0 or eta <= 0.0 or beta <= 0.0:
        return 1.0
    t_norm = life_consumed / eta
    return math.exp(-(t_norm ** beta))


# ---------------------------------------------------------------------------
# Muestreo de fallo (reproducible con semilla)
# ---------------------------------------------------------------------------

def sample_failure(
    state: ComponentState,
    rng: np.random.Generator,
    dt_h: float,
) -> bool:
    """Determina si el componente falla en este intervalo de tiempo.

    Usa la tasa de riesgo de Weibull para calcular la probabilidad de fallo
    en el intervalo Δt y la compara con una muestra del generador seeded.

    NO realiza tiradas aleatorias independientes — usa la tasa de riesgo
    acumulada para mantener coherencia probabilística con la vida total.

    Args:
        state: Estado actual del componente (se lee life_consumed, life_eta, life_beta).
        rng: Generador de números aleatorios numpy con semilla fija (reproducible).
        dt_h: Duración del intervalo en horas.

    Returns:
        True si el componente falla en este intervalo, False si sobrevive.
    """
    if state.failed:
        return True

    h = hazard_rate(state.life_consumed, state.life_eta, state.life_beta)
    if h <= 0.0:
        return False

    # Probabilidad de fallo en el intervalo: P = 1 - exp(-h × Δt)
    # Uso de la fórmula exacta para evitar problemas con dt grandes
    p_fail = 1.0 - math.exp(-h * dt_h)

    # Clampear por seguridad numérica
    p_fail = max(0.0, min(1.0, p_fail))

    u = rng.random()
    return u < p_fail


def degradation_check(state: ComponentState) -> bool:
    """Determina si el componente entra en estado degradado.

    Un componente se considera degradado cuando ha consumido el 70% de su
    vida estimada (wear_fraction ≥ 0.70). En este estado su rendimiento
    se reduce pero sigue funcionando.

    Args:
        state: Estado actual del componente.

    Returns:
        True si el componente debe marcarse como degradado.
    """
    return state.wear_fraction >= 0.70 and not state.failed


def compute_power_effect(state: ComponentState) -> float:
    """Calcula el factor de potencia basado en el desgaste y temperatura.

    - Desgaste < 70%: sin penalización (1.0)
    - Desgaste 70-100%: reducción lineal de 0% a 20%
    - Temperatura excesiva: reducción adicional (ver thermal_model)

    Returns:
        Factor multiplicador de potencia [0.6, 1.0].
    """
    if state.failed:
        return 0.0

    wear_penalty = 0.0
    if state.wear_fraction > 0.70:
        wear_penalty = 0.20 * min(1.0, (state.wear_fraction - 0.70) / 0.30)

    # Reducción por temperatura
    temp_penalty = 0.0
    if state.temperature_c > state.temp_max_c:
        excess = (state.temperature_c - state.temp_max_c) / max(1.0, state.temp_critical_c - state.temp_max_c)
        temp_penalty = 0.40 * min(1.0, excess)

    return max(0.0, 1.0 - wear_penalty - temp_penalty)


def compute_grip_effect(state: ComponentState) -> float:
    """Calcula el factor de grip basado en el desgaste de neumáticos/frenos.

    Solo aplicable a componentes 'tyres' y 'brakes'.
    Para el resto devuelve 1.0.

    Returns:
        Factor multiplicador de grip [0.5, 1.0].
    """
    if state.failed:
        return 0.5 if state.name in ("tyres", "brakes") else 1.0

    if state.name == "tyres":
        w = state.wear_fraction
        if w < 0.60:
            return 1.0
        elif w < 0.85:
            return 1.0 - 0.25 * (w - 0.60) / 0.25
        else:
            # Exponencial tras el 85%
            return max(0.5, 0.75 * math.exp(-3.0 * (w - 0.85)))

    elif state.name == "brakes":
        w = state.wear_fraction
        if w < 0.75:
            return 1.0
        return max(0.6, 1.0 - 0.40 * (w - 0.75) / 0.25)

    return 1.0

