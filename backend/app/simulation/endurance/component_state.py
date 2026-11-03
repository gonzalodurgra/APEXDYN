"""Estado dinámico de cada componente durante una simulación de resistencia.

Mantiene separados los parámetros técnicos originales del vehículo (VehiclePhysicsModel)
del estado mutable de cada unidad durante la simulación (ComponentState).

Los parámetros de Weibull por defecto están calibrados para un vehículo GT de competición
en un escenario de referencia de 24 horas con conducción a ritmo sostenido.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


# ---------------------------------------------------------------------------
# Dataclass principal
# ---------------------------------------------------------------------------

@dataclass
class ComponentState:
    """Estado dinámico de un componente durante una simulación de resistencia.

    Attributes:
        name: Identificador del componente (p. ej. 'engine', 'tyres').
        wear_fraction: Fracción de desgaste acumulado [0.0 = nuevo, 1.0 = límite de vida].
        temperature_c: Temperatura actual del componente en °C.
        temp_ambient_c: Temperatura ambiente de referencia en °C.
        temp_optimal_c: Temperatura óptima de funcionamiento en °C.
        temp_max_c: Temperatura máxima tolerada antes de degradar rendimiento en °C.
        temp_critical_c: Temperatura de fallo inmediato en °C.
        life_eta: Escala de vida Weibull η (en la unidad de life_consumed).
        life_beta: Factor de forma Weibull β (β<1 fallos tempranos, β=1 aleatorio, β>1 desgaste).
        life_consumed: Vida consumida acumulada (misma unidad que life_eta).
        failed: True si el componente ha fallado de forma definitiva.
        degraded: True si el rendimiento está reducido pero el componente sigue funcionando.
        repair_time_s: Tiempo de reparación en boxes (segundos); 0 si no es reparable.
        replacement_time_s: Tiempo de sustitución completa en boxes (segundos).
        power_effect_factor: Multiplicador sobre la potencia del vehículo [0..1].
        grip_effect_factor: Multiplicador sobre el grip del vehículo [0..1].
        heat_gen_coeff: Calor generado por unidad de carga (W / unidad de carga normalizada).
        thermal_mass_j_k: Capacidad calorífica efectiva (J/K).
        cooling_coeff_w_k: Coeficiente de disipación térmica en función de velocidad (W/K).
    """

    name: str

    # --- Desgaste ---
    wear_fraction: float = 0.0        # [0, 1]; 1.0 = al límite de vida
    life_eta: float = 1.0             # Escala Weibull (horas o km según componente)
    life_beta: float = 2.0            # Forma Weibull
    life_consumed: float = 0.0        # Vida consumida acumulada (misma unidad que life_eta)

    # --- Temperatura ---
    temperature_c: float = 80.0       # Temperatura inicial típica (se corrige por componente)
    temp_ambient_c: float = 25.0
    temp_optimal_c: float = 90.0
    temp_max_c: float = 110.0
    temp_critical_c: float = 130.0

    # --- Estado de salud ---
    failed: bool = False
    degraded: bool = False

    # --- Tiempos de intervención en boxes (s) ---
    repair_time_s: float = 0.0        # 0 = no reparable en boxes (sustitución o abandono)
    replacement_time_s: float = 300.0

    # --- Efectos sobre el vehículo ---
    power_effect_factor: float = 1.0  # Multiplicador de potencia [0..1]
    grip_effect_factor: float = 1.0   # Multiplicador de grip [0..1]

    # --- Modelo térmico ---
    heat_gen_coeff: float = 1000.0    # W por unidad de carga normalizada
    thermal_mass_j_k: float = 5000.0  # Capacidad calorífica (J/K)
    cooling_coeff_w_k: float = 100.0  # Disipación pasiva + activa (W/K)


# ---------------------------------------------------------------------------
# Fábrica de estados por defecto
# ---------------------------------------------------------------------------

def default_component_states(ambient_temp_c: float = 25.0) -> Dict[str, ComponentState]:
    """Crea el conjunto de componentes con parámetros Weibull por defecto.

    Los valores de η (escala) y β (forma) están expresados en horas de carrera
    a ritmo sostenido, calibrados para un GT de competición de referencia.

    Parámetros de Weibull por componente:
    ─────────────────────────────────────────────────────────────────────────
    Componente         │ η (h)  │ β     │ Justificación
    ───────────────────┼────────┼───────┼─────────────────────────────────
    Motor              │ 48     │ 2.5   │ Desgaste por ciclos térmicos
    Turbo/admisión     │ 36     │ 2.0   │ Alta temperatura, cojinetes
    Caja de cambios    │ 60     │ 2.8   │ Desgaste por ciclos de cambio
    Embrague           │ 20     │ 1.8   │ Deslizamiento acumulado
    Transmisión        │ 72     │ 3.0   │ Esfuerzo mecánico constante
    Refrigeración      │ 40     │ 1.5   │ Fallo temprano frecuente (juntas)
    Lubricación        │ 50     │ 2.2   │ Degradación del aceite
    Frenos             │ 12     │ 1.6   │ Vida útil por disco relativamente corta
    Suspensión         │ 80     │ 3.5   │ Alta β: vida predecible y larga
    Neumáticos         │ 6      │ 2.0   │ Desgaste en pocas horas de carrera
    Sistema eléctrico  │ 90     │ 1.2   │ Fallos tempranos (rodamientos, cableado)
    ─────────────────────────────────────────────────────────────────────────

    Returns:
        Diccionario {nombre_componente: ComponentState} con valores por defecto.
    """

    def _state(**kwargs) -> ComponentState:
        return ComponentState(temp_ambient_c=ambient_temp_c, **kwargs)

    return {
        "engine": _state(
            name="engine",
            temperature_c=ambient_temp_c + 20,
            temp_optimal_c=90.0,
            temp_max_c=115.0,
            temp_critical_c=140.0,
            life_eta=48.0,
            life_beta=2.5,
            repair_time_s=0.0,           # No reparable en boxes → DNF
            replacement_time_s=3600.0,
            heat_gen_coeff=8000.0,
            thermal_mass_j_k=15000.0,
            cooling_coeff_w_k=600.0,
        ),
        "turbo": _state(
            name="turbo",
            temperature_c=ambient_temp_c + 40,
            temp_optimal_c=120.0,
            temp_max_c=180.0,
            temp_critical_c=250.0,
            life_eta=36.0,
            life_beta=2.0,
            repair_time_s=0.0,
            replacement_time_s=1800.0,
            heat_gen_coeff=3000.0,
            thermal_mass_j_k=3000.0,
            cooling_coeff_w_k=150.0,
        ),
        "gearbox": _state(
            name="gearbox",
            temperature_c=ambient_temp_c + 15,
            temp_optimal_c=80.0,
            temp_max_c=110.0,
            temp_critical_c=135.0,
            life_eta=60.0,
            life_beta=2.8,
            repair_time_s=600.0,         # Cambio de relaciones en boxes
            replacement_time_s=2400.0,
            heat_gen_coeff=1500.0,
            thermal_mass_j_k=8000.0,
            cooling_coeff_w_k=120.0,
        ),
        "clutch": _state(
            name="clutch",
            temperature_c=ambient_temp_c + 10,
            temp_optimal_c=100.0,
            temp_max_c=200.0,
            temp_critical_c=350.0,
            life_eta=20.0,
            life_beta=1.8,
            repair_time_s=900.0,
            replacement_time_s=1800.0,
            heat_gen_coeff=2000.0,
            thermal_mass_j_k=2000.0,
            cooling_coeff_w_k=80.0,
        ),
        "transmission": _state(
            name="transmission",
            temperature_c=ambient_temp_c + 10,
            temp_optimal_c=75.0,
            temp_max_c=105.0,
            temp_critical_c=130.0,
            life_eta=72.0,
            life_beta=3.0,
            repair_time_s=0.0,
            replacement_time_s=3000.0,
            heat_gen_coeff=800.0,
            thermal_mass_j_k=6000.0,
            cooling_coeff_w_k=100.0,
        ),
        "cooling": _state(
            name="cooling",
            temperature_c=ambient_temp_c + 5,
            temp_optimal_c=90.0,         # Temp. del líquido refrigerante
            temp_max_c=100.0,
            temp_critical_c=110.0,
            life_eta=40.0,
            life_beta=1.5,
            repair_time_s=300.0,
            replacement_time_s=900.0,
            heat_gen_coeff=500.0,
            thermal_mass_j_k=4000.0,
            cooling_coeff_w_k=400.0,
        ),
        "lubrication": _state(
            name="lubrication",
            temperature_c=ambient_temp_c + 20,
            temp_optimal_c=95.0,
            temp_max_c=130.0,
            temp_critical_c=160.0,
            life_eta=50.0,
            life_beta=2.2,
            repair_time_s=120.0,         # Cambio de aceite rápido
            replacement_time_s=240.0,
            heat_gen_coeff=2000.0,
            thermal_mass_j_k=5000.0,
            cooling_coeff_w_k=200.0,
        ),
        "brakes": _state(
            name="brakes",
            temperature_c=ambient_temp_c,
            temp_optimal_c=350.0,
            temp_max_c=700.0,
            temp_critical_c=900.0,
            life_eta=12.0,
            life_beta=1.6,
            repair_time_s=180.0,         # Cambio de pastillas
            replacement_time_s=600.0,    # Cambio de disco
            heat_gen_coeff=20000.0,      # Muy alta generación en frenadas
            thermal_mass_j_k=3000.0,
            cooling_coeff_w_k=800.0,     # Gran disipación con corriente de aire
        ),
        "suspension": _state(
            name="suspension",
            temperature_c=ambient_temp_c,
            temp_optimal_c=30.0,
            temp_max_c=60.0,
            temp_critical_c=80.0,
            life_eta=80.0,
            life_beta=3.5,
            repair_time_s=600.0,
            replacement_time_s=1800.0,
            heat_gen_coeff=100.0,
            thermal_mass_j_k=2000.0,
            cooling_coeff_w_k=50.0,
        ),
        "tyres": _state(
            name="tyres",
            temperature_c=ambient_temp_c,
            temp_optimal_c=85.0,
            temp_max_c=120.0,
            temp_critical_c=150.0,
            life_eta=6.0,                # ~6 horas hasta límite de desgaste en slicks GT
            life_beta=2.0,
            repair_time_s=0.0,
            replacement_time_s=60.0,     # Cambio de 4 neumáticos en boxes GT
            heat_gen_coeff=3000.0,
            thermal_mass_j_k=4000.0,
            cooling_coeff_w_k=300.0,
        ),
        "electrical": _state(
            name="electrical",
            temperature_c=ambient_temp_c + 5,
            temp_optimal_c=50.0,
            temp_max_c=80.0,
            temp_critical_c=100.0,
            life_eta=90.0,
            life_beta=1.2,               # β<2 → mayor riesgo de fallos tempranos
            repair_time_s=120.0,
            replacement_time_s=600.0,
            heat_gen_coeff=200.0,
            thermal_mass_j_k=2000.0,
            cooling_coeff_w_k=30.0,
        ),
    }

