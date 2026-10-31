"""Motor de Simulación QSS (Quasi-Steady-State) punto-masa.

Implementa el algoritmo de simulación de tiempos por vuelta y por tramo
más clásico en ingeniería de competición: el método de velocidad límite
+ integración numérica forward/backward (min-time).

Algoritmo (3 pasadas):
  1. Velocidad límite en curva (corner speed profile):
       v_max[i] = min(v_corner_limit, v_top_speed)
       v_corner_limit[i] = sqrt(ay_max * R[i])  con corrección por Kamm circle
  2. Pasada forward (aceleración):
       Desde cada mínimo de velocidad, propaga hacia adelante con
       ax = (F_drive - F_resist) / m_eff limitado por Kamm circle
  3. Pasada backward (frenada):
       Desde cada mínimo de velocidad, propaga hacia atrás con
       ax_brake = F_brake / m_eff limitado por Kamm circle
  4. Velocidad final = min(forward, backward, corner_limit)
  5. Tiempo por sector: dt = ds / v_medio

Referencias:
  - Beckman (1991), Theory of Racing Line
  - Milliken & Milliken, Race Car Vehicle Dynamics, ch. 21
  - Siegler et al. (2000), Lap Time Simulation
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.simulation.vehicle_physics import (
    VehiclePhysicsModel,
    EngineCurveData,
    GearData,
    AeroData,
    TireGripData,
    G_GRAVITY,
)


# ---------------------------------------------------------------------------
# Perfil de trazado de entrada para el simulador
# ---------------------------------------------------------------------------

@dataclass
class TrackProfile:
    """Perfil geométrico discretizado de un trazado para simulación QSS."""
    variant_id: str
    is_closed_loop: bool = True

    # Arrays de igual longitud N (un elemento por punto del trazado)
    distance_m: np.ndarray = field(default_factory=lambda: np.array([]))
    radius_m: np.ndarray = field(default_factory=lambda: np.array([]))   # radio de curva (m); >>9999 = recta
    grade_percent: np.ndarray = field(default_factory=lambda: np.array([]))  # pendiente %
    surface_mu_factor: np.ndarray = field(default_factory=lambda: np.array([]))  # factor de μ por superficie [0..1]

    @property
    def num_points(self) -> int:
        return len(self.distance_m)

    @property
    def total_length_m(self) -> float:
        return float(self.distance_m[-1]) if self.num_points > 0 else 0.0

    def segment_lengths(self) -> np.ndarray:
        """Longitud de cada segmento entre puntos consecutivos (N-1 elementos)."""
        return np.diff(self.distance_m)


# ---------------------------------------------------------------------------
# Resultado de la simulación
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """Resultado completo de una simulación QSS sobre un trazado."""
    vehicle_id: str
    variant_id: str
    model_version: str = "QSS-v1.0"

    # Tiempo total
    total_time_s: float = 0.0

    # Perfiles a lo largo del trazado (N elementos)
    speed_m_s: np.ndarray = field(default_factory=lambda: np.array([]))
    gear_profile: np.ndarray = field(default_factory=lambda: np.array([]))
    accel_m_s2: np.ndarray = field(default_factory=lambda: np.array([]))
    engine_rpm_profile: np.ndarray = field(default_factory=lambda: np.array([]))

    # Métricas derivadas
    max_speed_m_s: float = 0.0
    min_speed_m_s: float = 0.0
    avg_speed_m_s: float = 0.0
    max_lateral_g: float = 0.0
    max_longitudinal_accel_g: float = 0.0
    max_braking_g: float = 0.0

    # Sectores (si se calculan)
    sector_times_s: List[float] = field(default_factory=list)

    # Parámetros de la corrida
    parameters: Dict = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "vehicle_id": self.vehicle_id,
            "variant_id": self.variant_id,
            "model_version": self.model_version,
            "total_time_s": round(self.total_time_s, 3),
            "max_speed_m_s": round(self.max_speed_m_s, 2),
            "max_speed_kph": round(self.max_speed_m_s * 3.6, 1),
            "min_speed_m_s": round(self.min_speed_m_s, 2),
            "min_speed_kph": round(self.min_speed_m_s * 3.6, 1),
            "avg_speed_m_s": round(self.avg_speed_m_s, 2),
            "avg_speed_kph": round(self.avg_speed_m_s * 3.6, 1),
            "max_lateral_g": round(self.max_lateral_g, 3),
            "max_longitudinal_accel_g": round(self.max_longitudinal_accel_g, 3),
            "max_braking_g": round(self.max_braking_g, 3),
            "sector_times_s": [round(t, 3) for t in self.sector_times_s],
            "parameters": self.parameters,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Motor de simulación QSS
# ---------------------------------------------------------------------------

class QSSSimulator:
    """Simulador quasi-steady-state (punto-masa) de tiempos por vuelta y tramo.

    Implementa el método clásico de velocidad límite + pasadas forward/backward.
    """

    MODEL_VERSION = "QSS-v1.0"

    def __init__(
        self,
        vehicle: VehiclePhysicsModel,
        # Límites físicos adicionales del simulador
        v_max_cap_m_s: float = 90.0,    # Velocidad máxima absoluta (límite de seguridad) realistic for GT3 RS
        min_radius_threshold_m: float = 5.0,   # Radio mínimo considerado curva real
        straight_radius_m: float = 99999.0,    # Radio por encima del cual = recta
    ):
        self.vehicle = vehicle
        self.v_max_cap = v_max_cap_m_s
        self.min_radius = min_radius_threshold_m
        self.straight_radius = straight_radius_m

    # -------------------------------------------------------------------
    # Paso 1: Perfil de velocidad en curva (Corner Speed Profile)
    # -------------------------------------------------------------------
    def _corner_speed_profile(
        self,
        profile: TrackProfile,
    ) -> np.ndarray:
        """Calcula el perfil de velocidad máxima sostenida en curva para cada punto."""
        n = profile.num_points
        v_corner = np.full(n, self.v_max_cap)

        for i in range(n):
            r = float(profile.radius_m[i])
            grade = float(profile.grade_percent[i])
            mu_factor = float(profile.surface_mu_factor[i]) if len(profile.surface_mu_factor) == n else 1.0

            # Aplicar factor de superficie al grip del neumático temporalmente
            orig_mu = self.vehicle.tire_grip.mu_road_factor
            self.vehicle.tire_grip.mu_road_factor = mu_factor

            if r >= self.straight_radius or r <= 0:
                v_corner[i] = self.v_max_cap
            else:
                effective_r = max(r, self.min_radius)
                v_corner[i] = min(
                    self.vehicle.max_corner_speed_m_s(effective_r, grade),
                    self.v_max_cap,
                )

            self.vehicle.tire_grip.mu_road_factor = orig_mu  # Restaurar

        return v_corner

    # -------------------------------------------------------------------
    # Paso 2 + 3: Pasada forward (aceleración) y backward (frenada)
    # -------------------------------------------------------------------
    def _forward_pass(
        self,
        profile: TrackProfile,
        v_corner: np.ndarray,
    ) -> np.ndarray:
        """Pasada forward: propaga velocidades con la aceleración máxima disponible."""
        n = profile.num_points
        v = v_corner.copy()
        ds = profile.segment_lengths()  # N-1 valores

        for i in range(n - 1):
            v_i = v[i]
            grade = float(profile.grade_percent[i])
            r = float(profile.radius_m[i])

            # Aceleración longitudinal disponible con la curva actual (Kamm circle)
            f_drive, _ = self.vehicle.max_drive_force_n(v_i)
            f_resist = self.vehicle.total_resistance_n(v_i, grade)
            net_force = f_drive - f_resist

            ax_long = net_force / self.vehicle.effective_mass_kg

            # Reducir aceleración disponible si estamos en curva (Kamm circle)
            if r < self.straight_radius and r > 0:
                ay_max = self.vehicle.max_lateral_accel_m_s2(v_i, grade)
                ay_req = v_i ** 2 / r if r > 0 else 0.0
                ay_req = min(ay_req, ay_max)
                remaining = max(0.0, 1.0 - (ay_req / ay_max) ** 2) if ay_max > 0 else 0.0
                ax_long = ax_long * math.sqrt(remaining)

            # Velocidad al final del segmento: v² = v_i² + 2·ax·ds
            seg_len = float(ds[i])
            if ax_long > 0:
                v_next = math.sqrt(v_i ** 2 + 2.0 * ax_long * seg_len)
            else:
                v_next = v_i  # sin aceleración neta, mantener velocidad

            v[i + 1] = min(v[i + 1], v_next, self.v_max_cap)

        return v

    def _backward_pass(
        self,
        profile: TrackProfile,
        v_corner: np.ndarray,
    ) -> np.ndarray:
        """Pasada backward: propaga velocidades hacia atrás con frenada máxima."""
        n = profile.num_points
        v = v_corner.copy()
        ds = profile.segment_lengths()  # N-1 valores

        for i in range(n - 2, -1, -1):
            v_next = v[i + 1]
            grade = float(profile.grade_percent[i])
            r = float(profile.radius_m[i])

            f_brake = self.vehicle.max_brake_force_n(v_next, grade)
            f_resist = self.vehicle.total_resistance_n(v_next, grade)
            # En frenada, la resistencia aerodinámica y de rodadura ayudan a frenar
            net_brake = f_brake + abs(f_resist)

            ax_brake = net_brake / self.vehicle.effective_mass_kg

            # Kamm circle: frenada en curva
            if r < self.straight_radius and r > 0:
                ay_max = self.vehicle.max_lateral_accel_m_s2(v_next, grade)
                ay_req = v_next ** 2 / r if r > 0 else 0.0
                ay_req = min(ay_req, ay_max)
                remaining = max(0.0, 1.0 - (ay_req / ay_max) ** 2) if ay_max > 0 else 0.0
                ax_brake = ax_brake * math.sqrt(remaining)

            seg_len = float(ds[i])
            if ax_brake > 0:
                v_braking = math.sqrt(v_next ** 2 + 2.0 * ax_brake * seg_len)
            else:
                v_braking = v_next

            v[i] = min(v[i], v_braking, self.v_max_cap)

        return v

    # -------------------------------------------------------------------
    # Integración temporal y perfiles derivados
    # -------------------------------------------------------------------
    def _integrate_time(self, profile: TrackProfile, v_final: np.ndarray) -> float:
        """Calcula el tiempo total integrando dt = ds / v_medio."""
        ds = profile.segment_lengths()
        total_time = 0.0
        n = len(ds)

        for i in range(n):
            v_mean = 0.5 * (float(v_final[i]) + float(v_final[i + 1]))
            if v_mean > 0.01:
                total_time += float(ds[i]) / v_mean
            else:
                total_time += float(ds[i]) / 0.01  # Fallback seguridad

        return total_time

    def _compute_gear_profile(
        self, v_profile: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Calcula la marcha óptima y las RPM del motor para cada punto del perfil de velocidad."""
        gears = np.ones(len(v_profile), dtype=int)
        rpms = np.zeros(len(v_profile))

        if self.vehicle.gearbox is None or self.vehicle.engine_curve is None:
            return gears, rpms

        for i, v in enumerate(v_profile):
            g = self.vehicle.optimal_gear_at_speed(float(v))
            gears[i] = g
            rpm = self.vehicle.gearbox.engine_rpm(float(v), g)
            rpms[i] = min(rpm, self.vehicle.engine_max_rpm)

        return gears, rpms

    def _compute_accel_profile(
        self, v_profile: np.ndarray, profile: TrackProfile
    ) -> np.ndarray:
        """Calcula el perfil de aceleración longitudinal (m/s²)."""
        n = len(v_profile)
        accel = np.zeros(n)
        ds = profile.segment_lengths()
        for i in range(n - 1):
            dv = float(v_profile[i + 1]) - float(v_profile[i])
            v_mean = 0.5 * (float(v_profile[i]) + float(v_profile[i + 1]))
            dt = float(ds[i]) / max(v_mean, 0.01)
            accel[i] = dv / dt if dt > 0 else 0.0
        accel[-1] = accel[-2]
        return accel

    def _sector_times(
        self,
        profile: TrackProfile,
        v_final: np.ndarray,
        num_sectors: int = 3,
    ) -> List[float]:
        """Divide el trazado en sectores iguales y calcula el tiempo de cada uno."""
        total_len = profile.total_length_m
        sector_len = total_len / num_sectors
        ds = profile.segment_lengths()

        times = [0.0] * num_sectors
        current_sector = 0
        sector_end = sector_len

        for i, d in enumerate(ds):
            v_mean = 0.5 * (float(v_final[i]) + float(v_final[i + 1]))
            dt = d / max(v_mean, 0.01)
            dist_end = float(profile.distance_m[i + 1])

            if current_sector < num_sectors - 1 and dist_end >= sector_end:
                times[current_sector] += dt
                current_sector += 1
                sector_end += sector_len
            else:
                times[current_sector] += dt

        return times

    # -------------------------------------------------------------------
    # Método principal de simulación
    # -------------------------------------------------------------------
    def simulate(
        self,
        profile: TrackProfile,
        num_sectors: int = 3,
        num_warmup_laps: int = 2,
        initial_speed_m_s: Optional[float] = None,
    ) -> SimulationResult:
        """Ejecuta la simulación QSS completa sobre el trazado dado.

        Args:
            profile: Perfil geométrico del trazado (distancias, radios, pendientes).
            num_sectors: Número de sectores para desgloses de tiempo.
            num_warmup_laps: Para circuitos cerrados, número de iteraciones de
                             convergencia de la condición de periodicidad.
            initial_speed_m_s: Velocidad inicial opcional en m/s (para salida parada o lanzada).

        Returns:
            SimulationResult con tiempos, velocidades, marchas, RPM y métricas.
        """
        n = profile.num_points
        if n < 2:
            raise ValueError("El trazado necesita al menos 2 puntos para simular.")

        # Inicializar surface mu factor si no está definido
        if len(profile.surface_mu_factor) != n:
            profile.surface_mu_factor = np.ones(n)

        # --- Paso 1: Perfil de velocidad en curva ---
        v_corner = self._corner_speed_profile(profile)

        # --- Pasos 2+3: Forward + backward passes (con convergencia para circuito cerrado) ---
        iters = num_warmup_laps if (profile.is_closed_loop and initial_speed_m_s is None) else 1
        v_result = v_corner.copy()

        # Si se especifica velocidad inicial explícita (p. ej. 0 para salida desde parado)
        if initial_speed_m_s is not None:
            v_init = max(0.0, min(float(initial_speed_m_s), self.v_max_cap))
            v_result[0] = min(v_result[0], v_init)

        for _ in range(iters):
            v_result = self._forward_pass(profile, v_result)
            v_result = self._backward_pass(profile, v_result)
            # En circuito cerrado sin velocidad inicial forzada, aplicar periodicidad
            if profile.is_closed_loop and initial_speed_m_s is None:
                v_result[0] = min(v_result[0], v_result[-1])
                v_result[-1] = v_result[0]

        # --- Paso 4: Integración temporal ---
        total_time = self._integrate_time(profile, v_result)

        # --- Perfiles derivados ---
        gears, rpms = self._compute_gear_profile(v_result)
        accel = self._compute_accel_profile(v_result, profile)
        sector_times = self._sector_times(profile, v_result, num_sectors)

        # --- Métricas ---
        v_safe = np.where(profile.radius_m > 0, v_result, v_result)
        ay = np.where(
            profile.radius_m < 90_000,
            np.minimum(v_result ** 2 / np.maximum(profile.radius_m, 1.0), 30.0),
            0.0,
        )

        result = SimulationResult(
            vehicle_id=self.vehicle.vehicle_id,
            variant_id=profile.variant_id,
            model_version=self.MODEL_VERSION,
            total_time_s=total_time,
            speed_m_s=v_result,
            gear_profile=gears,
            accel_m_s2=accel,
            engine_rpm_profile=rpms,
            max_speed_m_s=float(np.max(v_result)),
            min_speed_m_s=float(np.min(v_result)),
            avg_speed_m_s=float(profile.total_length_m / total_time) if total_time > 0 else 0.0,
            max_lateral_g=float(np.max(ay) / G_GRAVITY),
            max_longitudinal_accel_g=float(np.max(accel) / G_GRAVITY),
            max_braking_g=float(np.min(accel) / G_GRAVITY),
            sector_times_s=sector_times,
            parameters={
                "vehicle_mass_kg": self.vehicle.mass_kg,
                "drive_type": self.vehicle.drive_type,
                "num_points": n,
                "track_length_m": profile.total_length_m,
                "num_sectors": num_sectors,
                "closed_loop": profile.is_closed_loop,
            },
        )

        return result
