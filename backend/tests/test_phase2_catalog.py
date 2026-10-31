"""Pruebas automatizadas de la Fase 2: Catálogo de Vehículos, Fabricantes y Subsistemas."""

import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_manufacturer_crud_endpoints():
    # 1. Crear fabricante
    unique_name = f"Alpine {uuid.uuid4().hex[:6]}"
    create_payload = {
        "name": unique_name,
        "country_code": "FR",
        "website": "https://www.alpinecars.com",
        "notes": "Marca deportiva francesa",
    }
    resp = client.post("/api/v1/manufacturers", json=create_payload)
    assert resp.status_code == 201
    mfg_data = resp.json()
    mfg_id = mfg_data["id"]
    assert mfg_data["name"] == unique_name
    assert mfg_data["country_code"] == "FR"

    # 2. Conflicto nombre duplicado
    dup_resp = client.post("/api/v1/manufacturers", json=create_payload)
    assert dup_resp.status_code == 409

    # 3. Listar fabricantes con filtro
    list_resp = client.get(f"/api/v1/manufacturers?search={unique_name}")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == mfg_id

    # 4. Actualizar fabricante
    upd_resp = client.put(f"/api/v1/manufacturers/{mfg_id}", json={"notes": "Actualizado"})
    assert upd_resp.status_code == 200
    assert upd_resp.json()["notes"] == "Actualizado"

    # 5. Obtener por ID
    get_resp = client.get(f"/api/v1/manufacturers/{mfg_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == mfg_id


def test_vehicle_complete_hierarchy_and_subsystems():
    # 1. Crear fabricante base
    mfg_resp = client.post(
        "/api/v1/manufacturers",
        json={"name": f"Honda {uuid.uuid4().hex[:6]}", "country_code": "JP"},
    )
    assert mfg_resp.status_code == 201
    mfg_id = mfg_resp.json()["id"]

    # 2. Crear vehículo completo con motor, curva, caja, suspensión, aero y neumáticos
    vehicle_payload = {
        "manufacturer_id": mfg_id,
        "model": "Civic",
        "generation": "FK8",
        "variant": "Type R",
        "model_year": 2019,
        "body_style": "hatchback",
        "drive_type": "FWD",
        "differential_type": "Helical LSD",
        "mass_kg": 1380.0,
        "mass_definition": "DIN",
        "front_mass_fraction": 0.62,
        "wheelbase_m": 2.699,
        "front_track_m": 1.599,
        "rear_track_m": 1.593,
        "is_stock_specification": True,
        "engine": {
            "vehicle_id": mfg_id,  # se reasigna en backend al vehículo creado
            "engine_code": "K20C1",
            "fuel_type": "gasoline",
            "aspiration": "turbo",
            "layout": "inline",
            "cylinders": 4,
            "displacement_cc": 1996.0,
            "max_power_kw": 235.0,  # 320 CV
            "max_power_rpm": 6500.0,
            "max_torque_nm": 400.0,
            "max_torque_rpm": 2500.0,
            "idle_rpm": 750.0,
            "max_rpm": 7000.0,
            "curve_points": [
                {"rpm": 2500.0, "torque_nm": 400.0},  # power calculado automáticamente por validador
                {"rpm": 4500.0, "torque_nm": 400.0},
                {"rpm": 6500.0, "torque_nm": 345.0, "power_kw": 235.0},
            ],
        },
        "gearbox": {
            "vehicle_id": mfg_id,
            "transmission_type": "manual",
            "gear_count": 6,
            "final_drive_ratio": 4.111,
            "efficiency": 0.93,
            "shift_time_s": 0.30,
            "gears": [
                {"gear_number": 1, "ratio": 3.625},
                {"gear_number": 2, "ratio": 2.115},
                {"gear_number": 3, "ratio": 1.529},
                {"gear_number": 4, "ratio": 1.125},
                {"gear_number": 5, "ratio": 0.911},
                {"gear_number": 6, "ratio": 0.735},
            ],
        },
        "suspension": {
            "vehicle_id": mfg_id,
            "front_type": "Dual Axis Strut",
            "rear_type": "Multi-link",
            "front_spring_rate_n_m": 45000.0,
            "rear_spring_rate_n_m": 50000.0,
        },
        "aerodynamics": {
            "vehicle_id": mfg_id,
            "drag_coefficient_cd": 0.36,
            "frontal_area_m2": 2.18,
            "lift_coefficient_cl": -0.05,  # carga aerodinámica neta
        },
        "tires": [
            {
                "vehicle_id": mfg_id,
                "axle": "FRONT",
                "tire_brand": "Continental",
                "tire_model": "SportContact 6",
                "width_mm": 245,
                "aspect_ratio": 30,
                "rim_diameter_in": 20.0,
                "rolling_resistance_coefficient": 0.011,
            }
        ],
    }

    create_v_resp = client.post("/api/v1/vehicles", json=vehicle_payload)
    assert create_v_resp.status_code == 201
    v_data = create_v_resp.json()
    vehicle_id = v_data["id"]

    assert v_data["model"] == "Civic"
    assert v_data["variant"] == "Type R"
    assert v_data["manufacturer"]["id"] == mfg_id
    assert v_data["engine"]["engine_code"] == "K20C1"
    assert len(v_data["engine"]["curve_points"]) == 3
    # Comprobar cálculo físico consistente de potencia en rpm=2500
    assert v_data["engine"]["curve_points"][0]["power_kw"] > 100.0
    assert v_data["gearbox"]["gear_count"] == 6
    assert len(v_data["gearbox"]["gears"]) == 6
    assert v_data["suspension"]["front_type"] == "Dual Axis Strut"
    assert v_data["aerodynamics"]["drag_coefficient_cd"] == 0.36
    assert len(v_data["tires"]) == 1

    # 3. Filtrar vehículos por modelo y potencia
    query_resp = client.get("/api/v1/vehicles?search=Type R&min_power_kw=200&drive_type=FWD")
    assert query_resp.status_code == 200
    paged = query_resp.json()
    assert paged["total"] >= 1
    assert any(item["id"] == vehicle_id for item in paged["items"])

    # 4. Probar endpoints de subsistemas individuales
    engine_resp = client.get(f"/api/v1/vehicles/{vehicle_id}/engine")
    assert engine_resp.status_code == 200
    assert engine_resp.json()["max_power_kw"] == 235.0

    gearbox_resp = client.get(f"/api/v1/vehicles/{vehicle_id}/gearbox")
    assert gearbox_resp.status_code == 200
    assert gearbox_resp.json()["final_drive_ratio"] == 4.111

    # 5. Agregar puntos de curva adicionales al motor
    curve_pt_resp = client.post(
        f"/api/v1/engines/{v_data['engine']['id']}/curve-points",
        json=[{"rpm": 7000.0, "torque_nm": 300.0}],
    )
    assert curve_pt_resp.status_code == 200
    assert len(curve_pt_resp.json()) == 1

    # 6. Borrado en cascada
    del_resp = client.delete(f"/api/v1/vehicles/{vehicle_id}")
    assert del_resp.status_code == 204

    # Verificar que el vehículo ya no existe
    get_deleted = client.get(f"/api/v1/vehicles/{vehicle_id}")
    assert get_deleted.status_code == 404
