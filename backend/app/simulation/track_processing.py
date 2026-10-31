"""Módulo matemático para el procesamiento de geometrías de circuitos y tramos de rally.

Incluye:
- Conversión y proyección entre coordenadas geográficas (WGS84 / EPSG:4326) y plano métrico local.
- Filtrado de ruido GPS (Savitzky-Golay / Moving Average) para evitar derivadas numéricas erráticas.
- Cálculo de distancias acumuladas a lo largo de la pista.
- Cálculo numérico de curvatura kappa (1/m), radio de curva R = 1/|kappa|, rumbo (heading) y pendientes (%).
"""

import math
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from scipy.signal import savgol_filter


def wgs84_to_local_enu(
    coords: List[Tuple[float, float, Optional[float]]],
    origin: Optional[Tuple[float, float, float]] = None,
) -> Tuple[np.ndarray, Tuple[float, float, float]]:
    """Convierte una lista de puntos GPS (lon, lat, elevación opcional) a coordenadas métricas ENU locales (x_east, y_north, z_up).

    Usa una proyección ortográfica / equirrectangular de alta precisión centrada en el origen local.
    coords: Lista de tuplas (lon_deg, lat_deg, alt_m)
    Retorna: (matriz Nx3 con x, y, z en metros, tupla origen (lon0, lat0, alt0))
    """
    if not coords:
        return np.empty((0, 3)), (0.0, 0.0, 0.0)

    lons = np.array([c[0] for c in coords], dtype=np.float64)
    lats = np.array([c[1] for c in coords], dtype=np.float64)
    alts = np.array([c[2] if len(c) > 2 and c[2] is not None else 0.0 for c in coords], dtype=np.float64)

    if origin is None:
        lon0 = float(lons[0])
        lat0 = float(lats[0])
        alt0 = float(alts[0])
    else:
        lon0, lat0, alt0 = origin

    lat0_rad = math.radians(lat0)
    R_earth = 6371000.0  # Radio medio terrestre en metros

    # Transformación planar equidistante local
    x = np.radians(lons - lon0) * R_earth * math.cos(lat0_rad)
    y = np.radians(lats - lat0) * R_earth
    z = alts - alt0

    enu = np.column_stack([x, y, z])
    return enu, (lon0, lat0, alt0)


def filter_gps_noise(points_xy: np.ndarray, window_length: int = 7, polyorder: int = 2) -> np.ndarray:
    """Aplica un filtro Savitzky-Golay a las coordenadas métricas (x, y) para eliminar micro-ruido de GPS

    sin falsear la geometría real de las curvas.
    """
    n_points = len(points_xy)
    if n_points < 5:
        return points_xy.copy()

    # La ventana debe ser impar y menor o igual al número de puntos
    win = min(window_length, n_points)
    if win % 2 == 0:
        win -= 1
    if win <= polyorder:
        poly = max(1, win - 1)
    else:
        poly = polyorder

    if win < 3:
        return points_xy.copy()

    filtered_x = savgol_filter(points_xy[:, 0], window_length=win, polyorder=poly)
    filtered_y = savgol_filter(points_xy[:, 1], window_length=win, polyorder=poly)
    filtered = np.column_stack([filtered_x, filtered_y])

    if points_xy.shape[1] > 2:
        filtered_z = savgol_filter(points_xy[:, 2], window_length=win, polyorder=poly)
        filtered = np.column_stack([filtered, filtered_z])

    return filtered


def calculate_track_derivatives(
    points_xyz: np.ndarray,
    is_closed_loop: bool = False,
) -> Dict[str, np.ndarray]:
    """Calcula distancias acumuladas s (m), curvatura kappa (1/m), radio R (m),

    rumbo heading (grados) y pendiente grade (%) a partir de coordenadas métricas (x, y, z).
    """
    n = len(points_xyz)
    if n < 2:
        return {
            "distance_m": np.zeros(n),
            "curvature_1_m": np.zeros(n),
            "radius_m": np.full(n, np.inf),
            "heading_deg": np.zeros(n),
            "grade_percent": np.zeros(n),
        }

    x = points_xyz[:, 0]
    y = points_xyz[:, 1]
    z = points_xyz[:, 2] if points_xyz.shape[1] > 2 else np.zeros(n)

    # 1. Distancias acumuladas s
    dx = np.diff(x)
    dy = np.diff(y)
    dz = np.diff(z)
    segment_lengths = np.sqrt(dx**2 + dy**2 + dz**2)
    # Evitar divisiones por distancias nulas en puntos duplicados consecutivos
    segment_lengths = np.maximum(segment_lengths, 1e-4)
    s = np.insert(np.cumsum(segment_lengths), 0, 0.0)

    # 2. Primeras y segundas derivadas respecto a s
    dx_ds = np.gradient(x, s)
    dy_ds = np.gradient(y, s)
    dz_ds = np.gradient(z, s)

    d2x_ds2 = np.gradient(dx_ds, s)
    d2y_ds2 = np.gradient(dy_ds, s)

    # 3. Curvatura kappa en el plano horizontal 2D: kappa = |x' y'' - y' x''| / (x'^2 + y'^2)^(3/2)
    speed_2d_sq = dx_ds**2 + dy_ds**2
    speed_2d_sq = np.maximum(speed_2d_sq, 1e-6)
    numerator = dx_ds * d2y_ds2 - dy_ds * d2x_ds2
    kappa = numerator / (speed_2d_sq ** 1.5)

    # Radio de curvatura R = 1 / |kappa|
    abs_kappa = np.abs(kappa)
    radius = np.where(abs_kappa > 1e-5, 1.0 / np.maximum(abs_kappa, 1e-5), 99999.0)
    # Acotar al radio mínimo físicamente transitable en carreteras/circuitos (>= 8.0 m)
    radius = np.where(radius < 99999.0, np.maximum(radius, 8.0), 99999.0)

    # 4. Rumbo (Heading en grados 0-360 respecto al Norte geográfico)
    # y = Norte, x = Este. Rumbo = atan2(dx, dy)
    heading_rad = np.arctan2(dx_ds, dy_ds)
    heading_deg = (np.degrees(heading_rad) + 360.0) % 360.0

    # 5. Pendiente longitudinal en % (dz / ds_horizontal * 100)
    ds_horiz = np.sqrt(dx_ds**2 + dy_ds**2)
    ds_horiz = np.maximum(ds_horiz, 1e-4)
    grade_percent = (dz_ds / ds_horiz) * 100.0

    return {
        "distance_m": s,
        "curvature_1_m": kappa,
        "radius_m": radius,
        "heading_deg": heading_deg,
        "grade_percent": grade_percent,
    }
