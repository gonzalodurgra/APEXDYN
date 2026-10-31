"""Módulo de Física del Vehículo.

Proporciona cálculos puros de dinámica vehicular (sin dependencia de BD):
  - Interpolación de curvas de motor (torque, potencia) por RPM
  - Fuerza de tracción a la rueda por marcha y velocidad
  - Selección automática de marcha óptima
  - Fuerza de frenada máxima (presión de frenos + transferencia de carga)
  - Resistencias: aerodinámica (drag), rodadura (rolling resistance)
  - Envolvente de aceleración lateral máxima (límite de grip del neumático)
  - Combinación longitudinal-lateral mediante círculo de fricción (Kamm circle)

Todos los valores están en unidades del Sistema Internacional (SI):
  kg, m, s, N, W, J, m/s, m/s², rad/s, rad.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.interpolate import interp1d


# ---------------------------------------------------------------------------
# Constantes físicas
# ---------------------------------------------------------------------------
G_GRAVITY: float = 9.81          # m/s² (aceleración gravitacional)
RHO_AIR: float = 1.225            # kg/m³ (densidad del aire a 15°C, nivel del mar)


# ---------------------------------------------------------------------------
# Estructuras de datos de entrada (deserializadas desde la BD)
# ---------------------------------------------------------------------------

@dataclass
class EngineCurveData:
    """Curva de motor interpolable (RPM → Torque Nm, Potencia kW)."""
    rpm_points: List[float]
    torque_nm: List[float]
    power_kw: List[float]

    # Interpoladores (inicializados post-init)
    _torque_interp: Optional[interp1d] = field(default=None, repr=False, compare=False)
    _power_interp: Optional[interp1d] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        rpms = np.array(self.rpm_points, dtype=np.float64)
        torques = np.array(self.torque_nm, dtype=np.float64)
        powers = np.array(self.power_kw, dtype=np.float64)

        # Si no hay curva de potencia, derivarla del torque
        if np.all(powers == 0):
            powers = torques * rpms * (math.pi / 30) / 1000.0

        self._torque_interp = interp1d(
            rpms, torques,
            kind="linear", bounds_error=False,
            fill_value=(torques[0], torques[-1]),
        )
        self._power_interp = interp1d(
            rpms, powers,
            kind="linear", bounds_error=False,
            fill_value=(powers[0], powers[-1]),
        )

    def torque_at_rpm(self, rpm: float) -> float:
        """Torque en Nm para las RPM dadas (con extrapolación plana en los extremos)."""
        return float(self._torque_interp(max(0.0, rpm)))

    def power_kw_at_rpm(self, rpm: float) -> float:
        """Potencia en kW para las RPM dadas."""
        return float(self._power_interp(max(0.0, rpm)))


@dataclass
class GearData:
    """Datos de transmisión completos."""
    gear_ratios: List[float]         # [ratio_1a, ratio_2a, ..., ratio_Na]
    final_drive_ratio: float
    efficiency: float = 0.90         # Rendimiento mecánico total (0 < η ≤ 1)
    shift_time_s: float = 0.30       # Tiempo perdido en cada cambio de marcha
    tire_radius_m: float = 0.320     # Radio de rodadura efectivo en metros

    @property
    def num_gears(self) -> int:
        return len(self.gear_ratios)

    def wheel_rpm_from_speed(self, speed_m_s: float) -> float:
        """RPM de la rueda a partir de la velocidad del vehículo."""
        if self.tire_radius_m <= 0:
            return 0.0
        return (speed_m_s / (2 * math.pi * self.tire_radius_m)) * 60.0

    def engine_rpm(self, speed_m_s: float, gear: int) -> float:
        """RPM del motor para una velocidad y marcha dadas (gear: 1-indexed)."""
        if gear < 1 or gear > self.num_gears:
            return 0.0
        wheel_rpm = self.wheel_rpm_from_speed(speed_m_s)
        ratio = self.gear_ratios[gear - 1] * self.final_drive_ratio
        return wheel_rpm * ratio

    def max_speed_in_gear(self, gear: int, max_rpm: float) -> float:
        """Velocidad máxima teórica (m/s) en una marcha dada al máximo de RPM."""
        if gear < 1 or gear > self.num_gears:
            return 0.0
        ratio = self.gear_ratios[gear - 1] * self.final_drive_ratio
        wheel_rpm_max = max_rpm / ratio
        return wheel_rpm_max * (2 * math.pi * self.tire_radius_m) / 60.0

    def drive_torque_at_wheel(
        self,
        engine_torque_nm: float,
        gear: int,
    ) -> float:
        """Torque en las ruedas motrices (Nm) dado el torque del motor y la marcha."""
        if gear < 1 or gear > self.num_gears:
            return 0.0
        ratio = self.gear_ratios[gear - 1] * self.final_drive_ratio
        return engine_torque_nm * ratio * self.efficiency


@dataclass
class AeroData:
    """Datos aerodinámicos del vehículo."""
    cd: float = 0.35          # Coeficiente de resistencia aerodinámica
    frontal_area_m2: float = 2.10   # Área frontal en m²
    cl: float = 0.0           # Coeficiente de sustentación (negativo = downforce)
    front_downforce_fraction: float = 0.50

    def drag_force_n(self, speed_m_s: float, rho: float = RHO_AIR) -> float:
        """Fuerza de arrastre aerodinámica (N)."""
        return 0.5 * rho * self.cd * self.frontal_area_m2 * speed_m_s ** 2

    def downforce_n(self, speed_m_s: float, rho: float = RHO_AIR) -> float:
        """Fuerza de carga aerodinámica total (N). Positivo = hacia el suelo."""
        return -0.5 * rho * self.cl * self.frontal_area_m2 * speed_m_s ** 2


@dataclass
class TireGripData:
    """Modelo de grip simplificado del neumático."""
    mu_peak_longitudinal: float = 1.10    # Coeficiente de tracción/frenada
    mu_peak_lateral: float = 1.05         # Coeficiente lateral (cornering)
    mu_road_factor: float = 1.0           # Factor de reducción por estado de la pista [0..1]
    # Factores de carga vertical (load sensitivity): a mayor carga, menor μ efectivo
    load_sensitivity: float = 0.04        # Reducción de μ por kN adicional de carga


    def lateral_mu(self, normal_load_n: float) -> float:
        """μ lateral efectivo con sensibilidad de carga."""
        load_kn = normal_load_n / 1000.0
        mu = self.mu_peak_lateral * (1.0 - self.load_sensitivity * max(0.0, load_kn - 3.0))
        return max(0.1, mu) * self.mu_road_factor

    def longitudinal_mu(self, normal_load_n: float) -> float:
        """μ longitudinal efectivo con sensibilidad de carga."""
        load_kn = normal_load_n / 1000.0
        mu = self.mu_peak_longitudinal * (1.0 - self.load_sensitivity * max(0.0, load_kn - 3.0))
        return max(0.1, mu) * self.mu_road_factor


@dataclass
class VehiclePhysicsModel:
    """Modelo físico completo de un vehículo para la simulación QSS."""

    # Identificación (de la BD)
    vehicle_id: str
    label: str = ""

    # Masa y geometría
    mass_kg: float = 1200.0
    wheelbase_m: float = 2.50
    front_mass_fraction: float = 0.50  # Reparto de masa estático (eje delantero)
    cg_height_m: float = 0.45          # Altura del centro de gravedad (estimada si no disponible)

    # Tracción
    drive_type: str = "RWD"            # FWD, RWD, AWD
    engine_idle_rpm: float = 800.0
    engine_max_rpm: float = 7000.0
    engine_curve: Optional[EngineCurveData] = None
    gearbox: Optional[GearData] = None

    # Aerodinámica
    aero: AeroData = field(default_factory=AeroData)

    # Neumáticos / grip
    tire_grip: TireGripData = field(default_factory=TireGripData)

    # Resistencia a la rodadura
    rolling_resistance_coeff: float = 0.013   # CRR típico para neumático de turismo

    # Inercia rotacional equivalente (ruedas + motor) como fracción de masa total
    rotational_inertia_fraction: float = 0.05  # ~5% incremento efectivo de masa

    @property
    def effective_mass_kg(self) -> float:
        """Masa efectiva incluyendo inercia rotacional."""
        return self.mass_kg * (1.0 + self.rotational_inertia_fraction)

    @property
    def weight_n(self) -> float:
        """Peso estático total (N)."""
        return self.mass_kg * G_GRAVITY

    @property
    def front_axle_load_static_n(self) -> float:
        return self.weight_n * self.front_mass_fraction

    @property
    def rear_axle_load_static_n(self) -> float:
        return self.weight_n * (1.0 - self.front_mass_fraction)

    # -------------------------------------------------------------------
    # Fuerzas de resistencia
    # -------------------------------------------------------------------
    def rolling_resistance_n(self, speed_m_s: float) -> float:
        """Resistencia a la rodadura total (N). Pequeño efecto de velocidad incluido."""
        # CRR ligeramente dependiente de velocidad (SAE J1594 aproximado)
        crr = self.rolling_resistance_coeff * (1.0 + 0.0085 * speed_m_s)
        return crr * self.weight_n

    def total_resistance_n(self, speed_m_s: float, grade: float = 0.0) -> float:
        """Fuerza resistiva total (N): arrastre aero + rodadura + pendiente.

        grade: pendiente en % (positivo = subida).
        """
        drag = self.aero.drag_force_n(speed_m_s)
        rolling = self.rolling_resistance_n(speed_m_s)
        grade_force = self.mass_kg * G_GRAVITY * math.sin(math.atan(grade / 100.0))
        return drag + rolling + grade_force

    # -------------------------------------------------------------------
    # Fuerzas de tracción
    # -------------------------------------------------------------------
    def drive_force_n(
        self,
        speed_m_s: float,
        gear: int,
    ) -> float:
        """Fuerza de tracción disponible (N) en las ruedas, para una marcha y velocidad."""
        if self.engine_curve is None or self.gearbox is None:
            return 0.0

        rpm = self.gearbox.engine_rpm(speed_m_s, gear)
        rpm = max(self.engine_idle_rpm, min(rpm, self.engine_max_rpm))

        torque = self.engine_curve.torque_at_rpm(rpm)
        wheel_torque = self.gearbox.drive_torque_at_wheel(torque, gear)
        tire_r = self.gearbox.tire_radius_m
        if tire_r <= 0:
            return 0.0
        return wheel_torque / tire_r

    def max_drive_force_n(self, speed_m_s: float) -> Tuple[float, int]:
        """Fuerza máxima de tracción (N) eligiendo la mejor marcha, limitada por grip.

        Returns: (force_N, optimal_gear)
        """
        if self.gearbox is None or self.engine_curve is None:
            return 0.0, 1

        best_force = 0.0
        best_gear = 1

        # Carga en ruedas motrices (transferencia de carga dinámica al acelerar estimada)
        # Usamos carga estática como primera aproximación (será refinada por QSS)
        if self.drive_type == "RWD":
            driven_axle_load_n = self.rear_axle_load_static_n + self.aero.downforce_n(speed_m_s) * (1.0 - self.aero.front_downforce_fraction)
        elif self.drive_type == "FWD":
            driven_axle_load_n = self.front_axle_load_static_n + self.aero.downforce_n(speed_m_s) * self.aero.front_downforce_fraction
        else:  # AWD
            driven_axle_load_n = self.weight_n + self.aero.downforce_n(speed_m_s)

        grip_limit_n = self.tire_grip.longitudinal_mu(driven_axle_load_n) * driven_axle_load_n

        for g in range(1, self.gearbox.num_gears + 1):
            rpm = self.gearbox.engine_rpm(speed_m_s, g)
            # A velocidades casi nulas o muy bajas (arranque desde parado), se permite
            # patinamiento de embrague/convertidor de par manteniendo el motor en ralentí (idle)
            if rpm > self.engine_max_rpm * 1.02:
                continue
            if rpm < self.engine_idle_rpm * 0.5 and g > 1:
                continue
            f = self.drive_force_n(speed_m_s, g)
            f = min(f, grip_limit_n)  # Limitado por grip
            if f > best_force:
                best_force = f
                best_gear = g

        return best_force, best_gear

    def optimal_gear_at_speed(self, speed_m_s: float) -> int:
        """Devuelve la marcha óptima para la velocidad dada."""
        _, g = self.max_drive_force_n(speed_m_s)
        return g

    # -------------------------------------------------------------------
    # Frenada
    # -------------------------------------------------------------------
    def max_brake_force_n(
        self,
        speed_m_s: float,
        grade: float = 0.0,
        brake_bias_front: float = 0.65,
    ) -> float:
        """Fuerza de frenada máxima disponible (N), limitada por grip de neumáticos."""
        downforce = self.aero.downforce_n(speed_m_s)

        # Transferencia de carga longitudinal durante la frenada (estimación)
        # Ax_max ≈ mu * g  (0.9g aproximado como punto de partida)
        mu_approx = self.tire_grip.longitudinal_mu(self.weight_n / 2)
        ax_transfer_factor = mu_approx * self.cg_height_m / self.wheelbase_m

        front_load_n = (self.front_mass_fraction + ax_transfer_factor) * self.weight_n + downforce * self.aero.front_downforce_fraction
        rear_load_n = (1.0 - self.front_mass_fraction - ax_transfer_factor) * self.weight_n + downforce * (1.0 - self.aero.front_downforce_fraction)

        front_brake_n = self.tire_grip.longitudinal_mu(max(0, front_load_n)) * max(0, front_load_n)
        rear_brake_n = self.tire_grip.longitudinal_mu(max(0, rear_load_n)) * max(0, rear_load_n)

        # Freno de motor aproximado (~0.03g a velocidad moderada)
        engine_brake_n = 0.03 * G_GRAVITY * self.mass_kg * min(1.0, speed_m_s / 15.0)

        return front_brake_n + rear_brake_n + engine_brake_n

    # -------------------------------------------------------------------
    # Grip lateral
    # -------------------------------------------------------------------
    def max_lateral_accel_m_s2(
        self,
        speed_m_s: float,
        grade: float = 0.0,
    ) -> float:
        """Aceleración lateral máxima (m/s²) limitada por el grip del neumático."""
        downforce = self.aero.downforce_n(speed_m_s)
        total_load_n = self.weight_n + downforce
        mu_lat = self.tire_grip.lateral_mu(total_load_n / 2.0)  # por eje
        return mu_lat * G_GRAVITY
    
        # ---------------------------------------------------------------------------
    #  Top‑speed estimation (vehicle‑specific cap)
    # ---------------------------------------------------------------------------

    def _solve_power_limit(self, v_low: float, v_high: float, power_w: float) -> float:
        """Binary‑search speed where engine power just matches total resistance."""
        for _ in range(30):                     # sufficient for sub‑mm/s precision
            v_mid = (v_low + v_high) / 2.0
            drag_plus_roll = self.total_resistance_n(v_mid)   # N
            power_needed = v_mid * drag_plus_roll              # W
            if power_needed > power_w:
                v_high = v_mid
            else:
                v_low = v_mid
        return v_low

    def estimate_max_speed_m_s(self) -> float:
        """Return a realistic max‑speed bound (m/s) derived from vehicle data."""
        # ---- Gearbox‑limited speed -------------------------------------------------
        if self.gearbox is None or self.engine_max_rpm <= 0:
            v_gear = 300.0                     # generous fallback
        else:
            highest_gear = self.gearbox.num_gears
            v_gear = self.gearbox.max_speed_in_gear(highest_gear,
                                                    self.engine_max_rpm)

        # ---- Power‑limited speed ---------------------------------------------------
        max_power_w = (self.engine_curve.power_kw_at_rpm(self.engine_max_rpm)
                       if self.engine_curve else 0.0) * 1000.0
        if max_power_w <= 0:
            v_power = 300.0                     # ignore if no power data
        else:
            # Search up to the gearbox limit (or a very high number)
            v_power = self._solve_power_limit(0.0, min(v_gear, 200.0), max_power_w)

        # ---- Simple tire‑speed sanity check ----------------------------------------
        # Velocidad límite estándar para neumáticos homologados de altas prestaciones (índice W/Y/ZR >= 270-360 km/h)
        v_tire = 100.0                          # ~360 km/h

        # ---- Final cap -------------------------------------------------------------
        return min(v_gear, v_power, v_tire)


    def max_corner_speed_m_s(
        self,
        radius_m: float,
        grade: float = 0.0,
    ) -> float:
        """Velocidad máxima en curva (m/s) dado el radio y la pendiente."""
        if radius_m <= 0.5 or radius_m > 90_000:
            return 300.0  # Recta prácticamente
        ay_max = self.max_lateral_accel_m_s2(0.0, grade)  # primera aproximación
        # Iteramos para convergencia (downforce depende de v)
        v = math.sqrt(ay_max * radius_m)
        for _ in range(5):
            ay_max = self.max_lateral_accel_m_s2(v, grade)
            v_new = math.sqrt(ay_max * radius_m)
            if abs(v_new - v) < 0.01:
                break
            v = v_new
        return v

    # -------------------------------------------------------------------
    # Círculo de Kamm: combinación longitudinal + lateral
    # -------------------------------------------------------------------
    def longitudinal_accel_in_corner(
        self,
        speed_m_s: float,
        radius_m: float,
        grade: float = 0.0,
        braking: bool = False,
    ) -> float:
        """Aceleración longitudinal disponible (m/s²) mientras se curva.

        Usa la aproximación del círculo de Kamm:
            (ax/ax_max)² + (ay/ay_max)² = 1
        """
        ay_max = self.max_lateral_accel_m_s2(speed_m_s, grade)
        if radius_m > 90_000:  # Recta
            ay_used = 0.0
        else:
            v_corner_max = self.max_corner_speed_m_s(radius_m, grade)
            # Aceleración lateral requerida para mantener la curva a la velocidad actual
            ay_required = speed_m_s ** 2 / radius_m if radius_m > 0 else 0.0
            ay_used = min(ay_required, ay_max)

        ay_ratio_sq = (ay_used / ay_max) ** 2 if ay_max > 0 else 0.0
        remaining_fraction = max(0.0, 1.0 - ay_ratio_sq)

        if braking:
            ax_max = self.max_brake_force_n(speed_m_s, grade) / self.effective_mass_kg
        else:
            f_drive, _ = self.max_drive_force_n(speed_m_s)
            f_resist = self.total_resistance_n(speed_m_s, grade)
            ax_max = (f_drive - f_resist) / self.effective_mass_kg

        return ax_max * math.sqrt(remaining_fraction)
