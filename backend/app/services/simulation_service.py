"""Capa de servicio que conecta la BD con el Motor de Simulación QSS.

Responsabilidades:
  - Leer el vehículo y sus subsistemas de la BD → construir VehiclePhysicsModel
  - Leer la geometría de la variante de trazado → construir TrackProfile
  - Ejecutar la simulación con QSSSimulator
  - Persistir el SimulationRun en la BD
  - Construir el resultado enriquecido para la API
"""

from __future__ import annotations

import uuid
import math
from typing import Optional, Dict, Any, List

import numpy as np
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.models.vehicle import Vehicle, Engine, EngineCurvePoint, Gearbox, GearRatio, TireSetup
from app.models.track import TrackVariant, TrackGeometryPoint, SurfaceSegment
from app.models.simulation import SimulationRun, DriverProfile

from app.simulation.vehicle_physics import (
    VehiclePhysicsModel,
    EngineCurveData,
    GearData,
    AeroData,
    TireGripData,
)
from app.simulation.qss_simulator import QSSSimulator, TrackProfile, SimulationResult
from app.simulation.track_processing import calculate_track_derivatives


# ---------------------------------------------------------------------------
# Constructor: BD → VehiclePhysicsModel
# ---------------------------------------------------------------------------

def build_vehicle_physics_model(
    db: Session,
    vehicle_id: uuid.UUID,
    tire_mu_override: Optional[float] = None,
) -> VehiclePhysicsModel:
    """Carga un vehículo de la BD y construye un VehiclePhysicsModel para la simulación.

    Args:
        db: Sesión de SQLAlchemy.
        vehicle_id: UUID del vehículo.
        tire_mu_override: Si se proporciona, sobreescribe el μ de los neumáticos
                          (útil para simular superficie mojada, nieve, etc.).

    Returns:
        VehiclePhysicsModel listo para usar con QSSSimulator.

    Raises:
        ValueError: Si el vehículo no existe.
    """
    vehicle: Optional[Vehicle] = db.execute(
        select(Vehicle)
        .where(Vehicle.id == vehicle_id)
        .options(
            selectinload(Vehicle.engine).selectinload(Engine.curve_points),
            selectinload(Vehicle.gearbox).selectinload(Gearbox.gears),
            selectinload(Vehicle.aerodynamics),
            selectinload(Vehicle.tires),
            selectinload(Vehicle.suspension),
        )
    ).scalar_one_or_none()

    if vehicle is None:
        raise ValueError(f"Vehículo {vehicle_id} no encontrado en la base de datos.")

    # --- Modelo de motor ---
    engine_curve: Optional[EngineCurveData] = None
    engine_idle_rpm = 800.0
    engine_max_rpm = 7000.0

    if vehicle.engine is not None:
        eng = vehicle.engine
        engine_idle_rpm = eng.idle_rpm or 800.0
        engine_max_rpm = eng.max_rpm or (eng.max_power_rpm or 7000.0)

        if eng.curve_points:
            sorted_pts = sorted(eng.curve_points, key=lambda p: p.rpm)
            rpms = [p.rpm for p in sorted_pts]
            torques = [p.torque_nm or 0.0 for p in sorted_pts]
            powers = [p.power_kw or 0.0 for p in sorted_pts]

            # Si no hay datos de curva, generar curva trapezoidal estimada
            if len(rpms) < 2:
                rpms, torques, powers = _estimate_engine_curve(eng)

            engine_curve = EngineCurveData(
                rpm_points=rpms,
                torque_nm=torques,
                power_kw=powers,
            )
        else:
            # Generar curva estimada a partir de máximos tabulados
            rpms, torques, powers = _estimate_engine_curve(eng)
            engine_curve = EngineCurveData(
                rpm_points=rpms,
                torque_nm=torques,
                power_kw=powers,
            )

    # --- Caja de cambios ---
    gearbox_data: Optional[GearData] = None
    if vehicle.gearbox is not None:
        gb = vehicle.gearbox
        if gb.gears:
            sorted_gears = sorted(gb.gears, key=lambda g: g.gear_number)
            ratios = [g.ratio for g in sorted_gears if g.gear_number >= 1]
        else:
            ratios = [3.5, 2.2, 1.6, 1.2, 1.0, 0.85]  # Estimación genérica

        # Determinar radio de neumático (frente o trasero según tracción)
        tire_radius = _estimate_tire_radius(vehicle)

        gearbox_data = GearData(
            gear_ratios=ratios,
            final_drive_ratio=gb.final_drive_ratio or 3.7,
            efficiency=gb.efficiency or 0.90,
            shift_time_s=gb.shift_time_s or 0.30,
            tire_radius_m=tire_radius,
        )

    # --- Aerodinámica ---
    aero_data = AeroData()
    if vehicle.aerodynamics is not None:
        aero = vehicle.aerodynamics
        aero_data = AeroData(
            cd=aero.drag_coefficient_cd or 0.35,
            frontal_area_m2=aero.frontal_area_m2 or 2.10,
            cl=aero.lift_coefficient_cl or 0.0,
            front_downforce_fraction=aero.front_downforce_fraction or 0.50,
        )

    # --- Grip de neumáticos ---
    tire_grip = _estimate_tire_grip(vehicle, tire_mu_override)

    # --- Coeficiente de rodadura ---
    crr = 0.013
    if vehicle.tires:
        primary_tire = vehicle.tires[0]
        if primary_tire.rolling_resistance_coefficient:
            crr = primary_tire.rolling_resistance_coefficient

    # --- Altura del CG (estimada) ---
    cg_height = _estimate_cg_height(vehicle)

    label = f"{vehicle.model} {vehicle.variant or ''} {vehicle.model_year or ''}".strip()

    return VehiclePhysicsModel(
        vehicle_id=str(vehicle_id),
        label=label,
        mass_kg=vehicle.mass_kg,
        wheelbase_m=vehicle.wheelbase_m,
        front_mass_fraction=vehicle.front_mass_fraction or 0.50,
        cg_height_m=cg_height,
        drive_type=vehicle.drive_type or "RWD",
        engine_idle_rpm=engine_idle_rpm,
        engine_max_rpm=engine_max_rpm,
        engine_curve=engine_curve,
        gearbox=gearbox_data,
        aero=aero_data,
        tire_grip=tire_grip,
        rolling_resistance_coeff=crr,
    )


# ---------------------------------------------------------------------------
# Constructor: BD → TrackProfile
# ---------------------------------------------------------------------------

def build_track_profile(
    db: Session,
    variant_id: uuid.UUID,
    surface_wetness_override: Optional[float] = None,
) -> TrackProfile:
    """Carga la geometría de una variante de trazado de la BD y construye un TrackProfile.

    Args:
        db: Sesión de SQLAlchemy.
        variant_id: UUID de la variante del trazado.
        surface_wetness_override: Si se proporciona, fuerza un nivel de humedad [0..1]
                                  para todas las superficies (0=seco, 1=encharcado).

    Returns:
        TrackProfile listo para QSSSimulator.

    Raises:
        ValueError: Si la variante no existe o no tiene puntos de geometría.
    """
    variant: Optional[TrackVariant] = db.execute(
        select(TrackVariant)
        .where(TrackVariant.id == variant_id)
        .options(
            selectinload(TrackVariant.points),
            selectinload(TrackVariant.elevation_profile),
            selectinload(TrackVariant.surface_segments),
        )
    ).scalar_one_or_none()

    if variant is None:
        raise ValueError(f"Variante de trazado {variant_id} no encontrada.")

    points = sorted(variant.points, key=lambda p: p.sequence)

    if len(points) < 2:
        raise ValueError(
            f"La variante {variant_id} no tiene geometría procesada. "
            "Importa primero los puntos GPS mediante el endpoint import-geometry."
        )

    # --- Construir arrays de distancia, curvatura, pendiente ---
    dist_arr = np.array([p.distance_m for p in points], dtype=np.float64)

    # Recalcular curvaturas a partir de coordenadas métricas si disponibles
    has_xy = all(p.x_m is not None and p.y_m is not None for p in points)
    has_elevation = all(p.elevation_m is not None for p in points)

    if has_xy:
        x_arr = np.array([p.x_m for p in points], dtype=np.float64)
        y_arr = np.array([p.y_m for p in points], dtype=np.float64)
        z_arr = np.array([p.elevation_m or 0.0 for p in points], dtype=np.float64) if has_elevation else np.zeros(len(points))
        xyz = np.column_stack([x_arr, y_arr, z_arr])
        derivatives = calculate_track_derivatives(xyz, is_closed_loop=variant.is_closed_loop)
        curvature = np.abs(derivatives["curvature_1_m"])
        grade = derivatives["grade_percent"]
    else:
        # Fallback: sin coordenadas métricas, usar distancias solamente
        curvature = np.zeros(len(points))
        grade = np.zeros(len(points))

    # Radio de curvatura R = 1 / |κ| (limitar a un máximo razonable para rectas)
    radius_arr = np.where(curvature > 1e-5, 1.0 / curvature, 99999.0)
    radius_arr = np.clip(radius_arr, 1.0, 99999.0)

    # --- Factor de μ por superficie ---
    mu_factor_arr = np.ones(len(points))
    if variant.surface_segments:
        for seg in variant.surface_segments:
            # Determinar μ de la superficie
            wetness = surface_wetness_override if surface_wetness_override is not None else (seg.wetness or 0.0)
            mu_seg = _surface_mu_factor(seg.surface_type, wetness)

            # Asignar factor a los puntos que caen en este segmento
            mask = (dist_arr >= seg.start_distance_m) & (dist_arr <= seg.end_distance_m)
            mu_factor_arr[mask] = mu_seg

    return TrackProfile(
        variant_id=str(variant_id),
        is_closed_loop=variant.is_closed_loop,
        distance_m=dist_arr,
        radius_m=radius_arr,
        grade_percent=grade,
        surface_mu_factor=mu_factor_arr,
    )


# ---------------------------------------------------------------------------
# Servicio principal de simulación
# ---------------------------------------------------------------------------

class SimulationService:
    """Servicio de alto nivel para ejecutar simulaciones y persistir resultados."""

    @staticmethod
    def run(
        db: Session,
        vehicle_id: uuid.UUID,
        variant_id: uuid.UUID,
        driver_profile_id: Optional[uuid.UUID] = None,
        condition_id: Optional[uuid.UUID] = None,
        simulation_mode: str = "vehicle_limit",
        surface_wetness: Optional[float] = None,
        tire_mu_override: Optional[float] = None,
        num_sectors: int = 3,
        initial_speed_kmh: Optional[float] = None,
        v_max_cap_kph: Optional[float] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """Ejecuta una simulación QSS completa y opcionalmente la persiste en la BD.

        Args:
            db: Sesión SQLAlchemy.
            vehicle_id: UUID del vehículo a simular.
            variant_id: UUID de la variante de trazado.
            driver_profile_id: UUID del perfil de piloto (opcional).
            condition_id: UUID de las condiciones de pista (opcional).
            simulation_mode: 'vehicle_limit' (límite físico del vehículo) o 'human_driver'.
            surface_wetness: Fuerza un nivel de humedad global [0..1].
            tire_mu_override: Factor de μ global para los neumáticos.
            num_sectors: Número de sectores de tiempo.
            initial_speed_kmh: Velocidad inicial en km/h.
            v_max_cap_kph: Velocidad máxima absoluta del simulador en km/h.
            persist: Si True, guarda el SimulationRun en la BD.

        Returns:
            Diccionario con el resultado de la simulación y metadatos.

        Raises:
            ValueError: Si el vehículo o la variante no existen, o carecen de datos.
        """
        # 1. Construir modelo físico del vehículo
        vehicle_model = build_vehicle_physics_model(db, vehicle_id, tire_mu_override)

        # 2. Construir perfil de trazado
        track_profile = build_track_profile(db, variant_id, surface_wetness)

                # 3. Crear simulador y ejecutar
        if v_max_cap_kph is not None:
            # User supplied explicit cap → use it
            simulator = QSSSimulator(
                vehicle=vehicle_model,
                v_max_cap_m_s=v_max_cap_kph / 3.6,
            )
        else:
            # No explicit cap → compute a realistic vehicle‑specific cap
            cap_m_s = vehicle_model.estimate_max_speed_m_s()
            simulator = QSSSimulator(
                vehicle=vehicle_model,
                v_max_cap_m_s=cap_m_s,
            )

        init_speed_m_s = (initial_speed_kmh / 3.6) if initial_speed_kmh is not None else None
        result: SimulationResult = simulator.simulate(
            track_profile,
            num_sectors=num_sectors,
            initial_speed_m_s=init_speed_m_s,
        )

        # 4. Persistir en BD
        sim_run_id = None
        if persist:
            sim_run_id = SimulationService._persist(
                db=db,
                result=result,
                vehicle_id=vehicle_id,
                variant_id=variant_id,
                driver_profile_id=driver_profile_id,
                condition_id=condition_id,
                simulation_mode=simulation_mode,
            )

        # 5. Construir respuesta enriquecida
        response = result.to_dict()
        response["simulation_run_id"] = str(sim_run_id) if sim_run_id else None
        response["vehicle_label"] = vehicle_model.label

        # Añadir perfil de velocidad para visualización (muestreado)
        response["speed_profile"] = _downsample_profile(
            track_profile.distance_m,
            result.speed_m_s * 3.6,  # km/h para la API
            max_points=500,
        )
        response["gear_profile"] = _downsample_profile(
            track_profile.distance_m,
            result.gear_profile.astype(float),
            max_points=500,
        )
        response["rpm_profile"] = _downsample_profile(
            track_profile.distance_m,
            result.engine_rpm_profile,
            max_points=500,
        )
        response["accel_profile"] = _downsample_profile(
            track_profile.distance_m,
            result.accel_m_s2 / 9.81,  # en g
            max_points=500,
        )
        response["radius_profile"] = _downsample_profile(
            track_profile.distance_m,
            np.minimum(track_profile.radius_m, 500.0),  # Cap para visualización
            max_points=500,
        )

        return response

    @staticmethod
    def _persist(
        db: Session,
        result: SimulationResult,
        vehicle_id: uuid.UUID,
        variant_id: uuid.UUID,
        driver_profile_id: Optional[uuid.UUID],
        condition_id: Optional[uuid.UUID],
        simulation_mode: str,
    ) -> uuid.UUID:
        """Persiste un SimulationRun en la BD y retorna su UUID."""
        sim_run = SimulationRun(
            vehicle_id=vehicle_id,
            variant_id=variant_id,
            driver_profile_id=driver_profile_id,
            condition_id=condition_id,
            model_version=result.model_version,
            simulation_mode=simulation_mode,
            predicted_time_s=result.total_time_s,
            parameters=result.parameters,
            metrics={
                "max_speed_kph": round(result.max_speed_m_s * 3.6, 1),
                "min_speed_kph": round(result.min_speed_m_s * 3.6, 1),
                "avg_speed_kph": round(result.avg_speed_m_s * 3.6, 1),
                "max_lateral_g": round(result.max_lateral_g, 3),
                "max_accel_g": round(result.max_longitudinal_accel_g, 3),
                "max_braking_g": round(result.max_braking_g, 3),
                "sector_times_s": [round(t, 3) for t in result.sector_times_s],
            },
            status="completed",
        )
        db.add(sim_run)
        db.commit()
        db.refresh(sim_run)
        return sim_run.id

    @staticmethod
    def compare(
        db: Session,
        vehicle_ids: list[uuid.UUID],
        variant_id: uuid.UUID,
        surface_wetness: Optional[float],
        num_sectors: int,
        v_max_cap_kph: Optional[float],
    ) -> List[Dict[str, Any]]:
        """Ejecuta la simulación para múltiples vehículos en el mismo trazado y devuelve
        una lista de resultados ordenados por tiempo ascendente."""
        results = []
        for vid in vehicle_ids:
            try:
                res = SimulationService.run(
                    db=db,
                    vehicle_id=vid,
                    variant_id=variant_id,
                    surface_wetness=surface_wetness,
                    num_sectors=num_sectors,
                    v_max_cap_kph=v_max_cap_kph,
                    initial_speed_kmh=0,
                    persist=False,
                )
                results.append(res)
            except ValueError as e:
                results.append({"vehicle_id": str(vid), "error": str(e)})

        # Ordenar por tiempo total (los que tengan error quedan al final)
        results.sort(key=lambda r: r.get("total_time_s", float("inf")))
        return results


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _estimate_engine_curve(eng) -> tuple[list, list, list]:
    """Genera una curva de motor trapezoidal aproximada a partir de los máximos tabulados."""
    p_kw = eng.max_power_kw or 100.0
    t_nm = eng.max_torque_nm or 200.0
    rpm_p = eng.max_power_rpm or 6000.0
    rpm_t = eng.max_torque_rpm or 4000.0
    idle = eng.idle_rpm or 800.0
    max_r = eng.max_rpm or rpm_p

    # Curva trapezoidal: idle → rpm_t (subida de torque) → rpm_p (meseta) → max_rpm (caída)
    rpms = [idle, idle * 1.5, rpm_t * 0.7, rpm_t, rpm_p * 0.9, rpm_p, max_r]
    torques = [t_nm * 0.6, t_nm * 0.85, t_nm, t_nm, t_nm, p_kw * 1000 / (rpm_p * math.pi / 30), p_kw * 1000 / (max_r * math.pi / 30)]
    powers = [0.0] * len(rpms)

    return rpms, torques, powers


def _estimate_tire_radius(vehicle: Vehicle) -> float:
    """Estima el radio de rodadura efectivo a partir de la especificación del neumático."""
    drive = vehicle.drive_type or "RWD"
    for tire in (vehicle.tires or []):
        # Seleccionar el neumático del eje motor
        axle_match = (
            (drive == "FWD" and tire.axle in ("FRONT", "ALL")) or
            (drive in ("RWD", "AWD", "4WD") and tire.axle in ("REAR", "ALL"))
        )
        if not axle_match:
            continue
        if tire.nominal_radius_m:
            return tire.nominal_radius_m
        # Calcular a partir de dimensiones (width/aspect/rim)
        if tire.width_mm and tire.aspect_ratio and tire.rim_diameter_in:
            sidewall_m = (tire.width_mm * tire.aspect_ratio / 100) / 1000.0
            rim_radius_m = tire.rim_diameter_in * 0.0254 / 2.0
            return rim_radius_m + sidewall_m
    return 0.320  # Valor genérico por defecto


def _estimate_cg_height(vehicle: Vehicle) -> float:
    """Estima la altura del centro de gravedad."""
    if vehicle.height_m:
        # CG típicamente a ~45% de la altura del vehículo
        return vehicle.height_m * 0.45
    if vehicle.body_style:
        style = vehicle.body_style.lower()
        if "suv" in style or "pickup" in style:
            return 0.62
        elif "roadster" in style or "coupe" in style:
            return 0.40
    return 0.46


def _estimate_tire_grip(
    vehicle: Vehicle,
    tire_mu_override: Optional[float],
) -> TireGripData:
    """Estima el grip del neumático a partir de la categoría y posibles overrides."""
    # Valores base por categoría
    mu_long = 1.05
    mu_lat = 1.00

    for tire in (vehicle.tires or []):
        cat = (tire.tire_category or "").lower()
        if "slick" in cat:
            mu_long, mu_lat = 1.45, 1.40
        elif "semi-slick" in cat or "cup" in cat:
            mu_long, mu_lat = 1.25, 1.20
        elif "sport" in cat or "performance" in cat:
            mu_long, mu_lat = 1.10, 1.05
        elif "touring" in cat or "road" in cat:
            mu_long, mu_lat = 0.95, 0.90
        break  # Usar el primer neumático encontrado

    if tire_mu_override is not None:
        mu_long = tire_mu_override
        mu_lat = tire_mu_override * (mu_lat / mu_long)

    return TireGripData(
        mu_peak_longitudinal=mu_long,
        mu_peak_lateral=mu_lat,
    )


def _surface_mu_factor(surface_type: str, wetness: float) -> float:
    """Factores de reducción de μ según tipo de superficie y humedad."""
    base_factors = {
        "asphalt": 1.00,
        "smooth_asphalt": 1.05,
        "coarse_asphalt": 0.97,
        "concrete": 0.95,
        "gravel": 0.65,
        "coarse_gravel": 0.60,
        "mud": 0.45,
        "snow": 0.30,
        "ice": 0.15,
        "wet_asphalt": 0.78,
    }
    surface_lower = surface_type.lower()
    base = base_factors.get(surface_lower, 1.00)
    # Interpolación lineal: seco → mojado reduce μ hasta un 30%
    wet_factor = 1.0 - 0.30 * float(wetness)
    return base * max(0.1, wet_factor)


def _downsample_profile(
    distances: np.ndarray,
    values: np.ndarray,
    max_points: int = 500,
) -> List[Dict[str, float]]:
    """Reduce el perfil a un máximo de puntos para la respuesta de la API."""
    n = len(distances)
    if n <= max_points:
        step = 1
    else:
        step = n // max_points

    indices = range(0, n, step)
    return [
        {"d": round(float(distances[i]), 1), "v": round(float(values[i]), 3)}
        for i in indices
    ]
