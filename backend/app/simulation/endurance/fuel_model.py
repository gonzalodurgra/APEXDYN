"""Modelo de consumo de combustible basado en BSFC (Brake-Specific Fuel Consumption).

BSFC (Consumo Específico de Combustible al Freno) es el parámetro estándar
para cuantificar la eficiencia del motor en condiciones de carga variables.

    consumo [g/s] = BSFC [g/(kW·h)] × P_freno [kW] / 3600

A partir del consumo másico se obtiene el volumétrico usando la densidad del combustible.

Valores típicos de BSFC:
    - Motor NA gasolina: 260–290 g/(kW·h)
    - Motor turbo gasolina: 240–270 g/(kW·h)
    - Motor diésel: 195–230 g/(kW·h)
    - Motor optimizado en mapa de rendimiento: 220–250 g/(kW·h)
"""

from __future__ import annotations


# Densidad de referencia del combustible [kg/L]
GASOLINE_DENSITY_KG_L = 0.745
DIESEL_DENSITY_KG_L   = 0.835
E85_DENSITY_KG_L      = 0.786


# ---------------------------------------------------------------------------
# Funciones principales
# ---------------------------------------------------------------------------

def fuel_consumption_rate_l_s(
    power_w: float,
    bsfc_g_kwh: float,
    fuel_density_kg_l: float = GASOLINE_DENSITY_KG_L,
) -> float:
    """Calcula la tasa de consumo de combustible en litros por segundo.

    Args:
        power_w: Potencia al freno en vatios [W].
        bsfc_g_kwh: Consumo específico de combustible [g/(kW·h)].
        fuel_density_kg_l: Densidad del combustible en [kg/L].

    Returns:
        Tasa de consumo en [L/s].
    """
    if power_w <= 0.0 or bsfc_g_kwh <= 0.0:
        return 0.0

    # Conversión de unidades
    power_kw = power_w / 1000.0
    consumption_g_s = bsfc_g_kwh * power_kw / 3600.0
    consumption_l_s = consumption_g_s / (fuel_density_kg_l * 1000.0)

    return max(0.0, consumption_l_s)


def update_fuel(
    fuel_remaining_l: float,
    consumption_rate_l_s: float,
    dt_s: float,
) -> float:
    """Actualiza el combustible restante descontando el consumo.

    Args:
        fuel_remaining_l: Combustible disponible en litros.
        consumption_rate_l_s: Tasa de consumo en litros/segundo.
        dt_s: Paso de tiempo en segundos.

    Returns:
        Combustible restante en litros (nunca negativo).
    """
    consumed = consumption_rate_l_s * dt_s
    return max(0.0, fuel_remaining_l - consumed)


def laps_until_empty(
    fuel_l: float,
    consumption_l_lap: float,
) -> float:
    """Estima el número de vueltas restantes con el combustible disponible.

    Args:
        fuel_l: Combustible disponible en litros.
        consumption_l_lap: Consumo estimado por vuelta en litros.

    Returns:
        Número estimado de vueltas restantes (puede ser fraccionario).
    """
    if consumption_l_lap <= 0.0:
        return float("inf")
    return fuel_l / consumption_l_lap


def fuel_mass_effect_on_lap_time(
    fuel_l: float,
    fuel_density_kg_l: float,
    vehicle_mass_kg: float,
    lap_time_base_s: float,
    sensitivity_s_per_kg: float = 0.04,
) -> float:
    """Calcula el ajuste en el tiempo de vuelta por la masa del combustible.

    La masa del combustible cargado aumenta el tiempo de vuelta. Un valor
    típico en competición es 0.03–0.05 s por kg adicional.

    Args:
        fuel_l: Combustible actual en litros.
        fuel_density_kg_l: Densidad del combustible [kg/L].
        vehicle_mass_kg: Masa base del vehículo sin combustible [kg].
        lap_time_base_s: Tiempo de vuelta de referencia (con carga base) [s].
        sensitivity_s_per_kg: Sensibilidad en s/kg de combustible extra.

    Returns:
        Tiempo de vuelta ajustado en segundos.
    """
    fuel_mass_kg = fuel_l * fuel_density_kg_l
    # Masa de referencia: vehículo con combustible lleno (estimada como 0.3×masa vehículo)
    ref_fuel_mass_kg = 0.30 * vehicle_mass_kg
    delta_mass_kg = fuel_mass_kg - ref_fuel_mass_kg
    adjustment_s = delta_mass_kg * sensitivity_s_per_kg
    return max(lap_time_base_s, lap_time_base_s + adjustment_s)

