"""Módulo de simulación de fiabilidad y estrategia para carreras de resistencia.

Estructura:
  component_state   – Estado dinámico de cada componente durante la simulación
  thermal_model     – Modelos de balance térmico por componente
  wear_model        – Desgaste acumulativo dependiente de condiciones de operación
  failure_model     – Modelo probabilístico de fallos (distribuciones de Weibull)
  fuel_model        – Consumo de combustible y autonomía (basado en BSFC)
  tire_model        – Desgaste de neumáticos y efecto sobre el grip
  brake_model       – Desgaste de frenos y efecto sobre la eficacia de frenada
  strategy_engine   – Lógica de paradas en boxes y estrategia de carrera
  endurance_simulator – Simulador principal de resistencia
"""

from app.simulation.endurance.component_state import (
    ComponentState,
    default_component_states,
)
from app.simulation.endurance.endurance_simulator import EnduranceSimulator

__all__ = [
    "ComponentState",
    "default_component_states",
    "EnduranceSimulator",
]

