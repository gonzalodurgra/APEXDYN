"""Pruebas automatizadas de la Fase 3: Geometría de Pistas, Filtrado GPS, Curvaturas y Rutas API."""

import uuid
import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.simulation.track_processing import (
    wgs84_to_local_enu,
    filter_gps_noise,
    calculate_track_derivatives,
)

client = TestClient(app)


def test_track_processing_math_circular_loop():
    """Valida los cálculos matemáticos sobre un círculo perfecto con radio conocido R=100m.

    La curvatura teórica es kappa = 1/R = 0.01 1/m constante.
    """
    R_target = 100.0
    theta = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    x = R_target * np.cos(theta)
    y = R_target * np.sin(theta)
    z = np.sin(theta) * 5.0  # desnivel ondulatorio de 5m
    points_xyz = np.column_stack([x, y, z])

    # Aplicar derivadas
    res = calculate_track_derivatives(points_xyz, is_closed_loop=True)
    radii = res["radius_m"]

    # Comprobar que el radio medio calculado está dentro del 2% del radio teórico
    mean_radius = np.mean(radii)
    assert abs(mean_radius - R_target) < 2.0
    assert len(res["distance_m"]) == 200
    assert res["distance_m"][-1] > 0.0


def test_gps_noise_filtering():
    """Valida que el filtro Savitzky-Golay reduce la varianza del ruido GPS artificial."""
    t = np.linspace(0, 100, 100)
    true_x = t * 2.0
    true_y = t * 1.0

    # Inyectar ruido gaussiano blanco
    np.random.seed(42)
    noise_x = np.random.normal(0, 0.8, size=100)
    noise_y = np.random.normal(0, 0.8, size=100)

    noisy_pts = np.column_stack([true_x + noise_x, true_y + noise_y])
    filtered_pts = filter_gps_noise(noisy_pts, window_length=9, polyorder=2)

    raw_mse = np.mean((noisy_pts[:, 0] - true_x)**2)
    filtered_mse = np.mean((filtered_pts[:, 0] - true_x)**2)

    # El MSE filtrado debe ser sensiblemente menor
    assert filtered_mse < raw_mse


def test_track_and_geometry_endpoints():
    # 1. Crear un circuito y un tramo de rally
    track_payload = {
        "name": f"Circuito del Jarama {uuid.uuid4().hex[:6]}",
        "track_type": "CIRCUIT",
        "country_code": "ES",
        "region": "Madrid",
        "official_length_m": 3850.0,
        "is_public_road": False,
        "latitude": 40.617,
        "longitude": -3.585,
    }
    resp = client.post("/api/v1/tracks", json=track_payload)
    assert resp.status_code == 201
    track_data = resp.json()
    track_id = track_data["id"]

    # 2. Crear una variante de trazado
    variant_payload = {
        "track_id": track_id,
        "name": "Trazado GP Completo",
        "direction": "clockwise",
        "is_closed_loop": True,
        "version_number": 1,
    }
    v_resp = client.post(f"/api/v1/tracks/{track_id}/variants", json=variant_payload)
    assert v_resp.status_code == 201
    variant_id = v_resp.json()["id"]

    # 3. Importar una secuencia GPS realista para calcular geometría, longitud y perfiles
    # Simula una horquilla + recta: 5 puntos
    raw_gps = [
        {"latitude": 40.6170, "longitude": -3.5850, "elevation_m": 600.0},
        {"latitude": 40.6175, "longitude": -3.5845, "elevation_m": 602.0},
        {"latitude": 40.6180, "longitude": -3.5840, "elevation_m": 604.5},
        {"latitude": 40.6185, "longitude": -3.5835, "elevation_m": 607.0},
        {"latitude": 40.6190, "longitude": -3.5830, "elevation_m": 610.0},
    ]
    geom_resp = client.post(
        f"/api/v1/tracks/variants/{variant_id}/import-geometry?is_closed=false",
        json=raw_gps,
    )
    assert geom_resp.status_code == 200
    calc_info = geom_resp.json()
    assert calc_info["total_points"] == 5
    assert calc_info["calculated_length_m"] > 200.0
    assert calc_info["max_grade_percent"] > 0.0

    # 4. Consultar detalle de la variante con puntos calculados y elevación
    detail_resp = client.get(f"/api/v1/tracks/variants/{variant_id}")
    assert detail_resp.status_code == 200
    v_detail = detail_resp.json()
    assert len(v_detail["points"]) == 5
    assert len(v_detail["elevation_profile"]) == 5
    # Comprobar que los puntos tienen coordenadas métricas proyectadas x_m e y_m
    assert v_detail["points"][1]["distance_m"] > 0
    assert v_detail["points"][1]["x_m"] is not None

    # 5. Agregar un segmento de superficie (ej: asfalto rugoso con mu=1.05)
    surf_payload = {
        "variant_id": variant_id,
        "start_distance_m": 0.0,
        "end_distance_m": 150.0,
        "surface_type": "asphalt",
        "roughness_index": 1.2,
        "wetness": 0.0,
    }
    surf_resp = client.post(f"/api/v1/tracks/variants/{variant_id}/surfaces", json=surf_payload)
    assert surf_resp.status_code == 201

    # 6. Agregar condiciones de sesión (temperatura ambiente 22°C, asfalto 35°C)
    cond_payload = {
        "variant_id": variant_id,
        "air_temperature_c": 22.0,
        "surface_temperature_c": 35.0,
        "surface_condition": "dry",
        "wind_speed_m_s": 2.5,
    }
    cond_resp = client.post(f"/api/v1/tracks/variants/{variant_id}/conditions", json=cond_payload)
    assert cond_resp.status_code == 201

    # 7. Listar pistas con filtro por país y tipo
    list_resp = client.get("/api/v1/tracks?country_code=ES&track_type=CIRCUIT")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 8. Limpiar trazado creado
    del_resp = client.delete(f"/api/v1/tracks/{track_id}")
    assert del_resp.status_code == 204
