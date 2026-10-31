"""Servicio para parseo de telemetría (CSV, MoTeC, RaceChrono) y validación cruzada QSS."""

from __future__ import annotations

import csv
import io
import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.simulation import TelemetrySession, TelemetrySample, SimulationRun
from app.models.vehicle import Vehicle
from app.models.track import TrackVariant
from app.simulation.qss_simulator import QSSSimulator, SimulationResult
from app.services.simulation_service import build_vehicle_physics_model, build_track_profile


# Mapeos habituales de cabeceras de telemetría (MoTeC, AiM, RaceChrono, VBox, CSV estándar)
COLUMN_ALIASES = {
    "time": ["time", "timestamp", "t", "time_s", "elapsed_time", "utc_time"],
    "distance": ["distance", "dist", "distance_m", "lap_distance", "lap_dist_m", "d"],
    "speed": ["speed", "gps_speed", "speed_kmh", "speed_kph", "speed_m_s", "v", "velocity"],
    "rpm": ["rpm", "engine_rpm", "motor_rpm", "eng_rpm"],
    "gear": ["gear", "current_gear", "n_gear"],
    "throttle": ["throttle", "tps", "throttle_pct", "acc_pedal", "pedal_pos"],
    "brake": ["brake", "brake_pct", "brake_press", "brake_pressure"],
    "lat_acc": ["lat_acc", "latacc", "ay", "lateral_acc", "accel_y", "g_lat"],
    "long_acc": ["long_acc", "longacc", "ax", "longitudinal_acc", "accel_x", "g_lon"],
    "lat": ["lat", "latitude", "gps_lat"],
    "lon": ["lon", "long", "longitude", "gps_lon"],
}


class TelemetryService:
    @staticmethod
    def parse_csv_telemetry(csv_content: str) -> List[Dict[str, Any]]:
        """
        Parsea un contenido CSV de telemetría reconociendo automáticamente
        canales de diferentes sistemas (RaceChrono, MoTeC, VBox, AiM).
        """
        reader = csv.reader(io.StringIO(csv_content.strip()))
        headers = []
        rows = []

        # Buscar la fila de cabeceras (saltando metadatos iniciales habituales de MoTeC o RaceChrono)
        for line in reader:
            if not line or len(line) < 2:
                continue
            # Comprobar si parece fila de nombres de columna
            lower_line = [c.strip().lower() for c in line]
            if any(k in lower_line for k in ["time", "speed", "distance", "rpm", "gps_speed"]):
                headers = lower_line
                break

        if not headers:
            raise ValueError("No se encontraron cabeceras válidas de telemetría en el archivo CSV.")

        # Mapear nombres de columnas
        col_map = {}
        for canonical, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in headers:
                    col_map[canonical] = headers.index(alias)
                    break

        if "speed" not in col_map and "distance" not in col_map:
            raise ValueError("El archivo CSV debe contener al menos un canal de velocidad o distancia.")

        samples = []
        idx = 0
        cumulative_dist = 0.0
        last_t = 0.0
        start_time = datetime.now(timezone.utc)

        for line in reader:
            if not line or len(line) < len(headers):
                continue

            def get_val(key: str) -> Optional[float]:
                if key in col_map:
                    try:
                        raw = line[col_map[key]].strip()
                        return float(raw) if raw else None
                    except ValueError:
                        return None
                return None

            t = get_val("time")
            if t is None:
                t = idx * 0.1  # Asumir 10 Hz por defecto si no hay columna time

            # Manejar velocidad (convertir km/h a m/s si viene en km/h)
            speed_val = get_val("speed")
            speed_m_s = None
            if speed_val is not None:
                speed_header = headers[col_map["speed"]]
                if "kmh" in speed_header or "kph" in speed_header or speed_val > 60:
                    speed_m_s = speed_val / 3.6
                else:
                    speed_m_s = speed_val

            # Distancia
            dist = get_val("distance")
            if dist is None and speed_m_s is not None:
                dt = t - last_t if idx > 0 else 0.0
                cumulative_dist += speed_m_s * max(0.0, dt)
                dist = cumulative_dist
            elif dist is not None:
                cumulative_dist = dist

            sample = {
                "sample_index": idx,
                "timestamp": start_time + timedelta(seconds=t),
                "distance_m": dist,
                "speed_m_s": speed_m_s,
                "engine_rpm": get_val("rpm"),
                "gear": int(get_val("gear")) if get_val("gear") is not None else None,
                "throttle_percent": get_val("throttle"),
                "brake_percent": get_val("brake"),
                "lateral_acceleration_m_s2": get_val("lat_acc"),
                "longitudinal_acceleration_m_s2": get_val("long_acc"),
                "latitude": get_val("lat"),
                "longitude": get_val("lon")
            }
            samples.append(sample)
            last_t = t
            idx += 1

        return samples

    @staticmethod
    def import_session(
        db: Session,
        vehicle_id: uuid.UUID,
        variant_id: uuid.UUID,
        csv_content: str,
        driver_id: Optional[uuid.UUID] = None,
        data_source: str = "CSV Telemetry",
        notes: Optional[str] = None
    ) -> TelemetrySession:
        """Importa y guarda una sesión con sus muestras asociadas en la BD."""
        raw_samples = TelemetryService.parse_csv_telemetry(csv_content)
        if not raw_samples:
            raise ValueError("No se extrajeron muestras válidas del CSV.")

        session = TelemetrySession(
            vehicle_id=vehicle_id,
            variant_id=variant_id,
            driver_id=driver_id,
            data_source=data_source,
            quality_status="imported",
            started_at=raw_samples[0]["timestamp"],
            notes=notes
        )
        db.add(session)
        db.flush()

        # Batch insert de muestras
        sample_objects = []
        for s in raw_samples:
            sample_obj = TelemetrySample(
                session_id=session.id,
                sample_index=s["sample_index"],
                timestamp=s["timestamp"],
                distance_m=s["distance_m"],
                speed_m_s=s["speed_m_s"],
                longitudinal_acceleration_m_s2=s["longitudinal_acceleration_m_s2"],
                lateral_acceleration_m_s2=s["lateral_acceleration_m_s2"],
                throttle_percent=s["throttle_percent"],
                brake_percent=s["brake_percent"],
                engine_rpm=s["engine_rpm"],
                gear=s["gear"]
            )
            sample_objects.append(sample_obj)

        db.add_all(sample_objects)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def validate_against_simulation(
        db: Session,
        session_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Ejecuta la validación cruzada y correlación entre los datos de telemetría reales
        de la sesión y la predicción del motor físico cuasi-estacionario QSS.
        """
        session = db.get(TelemetrySession, session_id)
        if not session:
            raise ValueError(f"Sesión de telemetría no encontrada: {session_id}")

        samples = session.samples
        if not samples or len(samples) < 10:
            raise ValueError("La sesión no tiene suficientes muestras de telemetría.")

        # Calcular métricas reales
        times = [(s.timestamp - session.started_at).total_seconds() for s in samples if session.started_at]
        real_lap_time = times[-1] if times else (len(samples) * 0.1)
        real_speeds_kmh = [((s.speed_m_s or 0.0) * 3.6) for s in samples]
        real_max_speed = float(np.max(real_speeds_kmh)) if real_speeds_kmh else 0.0
        real_avg_speed = float(np.mean(real_speeds_kmh)) if real_speeds_kmh else 0.0
        real_distances = [(s.distance_m or 0.0) for s in samples]

        # Simular con el motor QSS para el mismo vehículo y variante
        vehicle_model = build_vehicle_physics_model(db, session.vehicle_id)
        track_profile = build_track_profile(db, session.variant_id)

        simulator = QSSSimulator(vehicle_model)
        sim_res = simulator.run(track_profile, initial_speed_km_h=0.0)

        # Muestreo comparativo interpolado por distancia
        eval_distances = np.linspace(0, track_profile.total_length_m, 100)
        sim_speeds_interp = np.interp(eval_distances, sim_res.s_m, sim_res.speed_kmh)
        real_speeds_interp = np.interp(eval_distances, real_distances, real_speeds_kmh)

        # Error cuadrático medio y coeficiente de correlación de Pearson
        diffs = sim_speeds_interp - real_speeds_interp
        rmse = float(np.sqrt(np.mean(diffs ** 2)))

        std_sim = np.std(sim_speeds_interp)
        std_real = np.std(real_speeds_interp)
        if std_sim > 1e-4 and std_real > 1e-4:
            corr_mat = np.corrcoef(sim_speeds_interp, real_speeds_interp)
            correlation = float(corr_mat[0, 1])
        else:
            correlation = 1.0

        delta_s = sim_res.total_time_s - real_lap_time
        percentage_error = (delta_s / real_lap_time) * 100.0 if real_lap_time > 0 else 0.0

        sampled_points = []
        for d, s_sim, s_real in zip(eval_distances, sim_speeds_interp, real_speeds_interp):
            sampled_points.push if hasattr(sampled_points, 'push') else sampled_points.append({
                "distance_m": round(float(d), 1),
                "simulated_speed_kmh": round(float(s_sim), 1),
                "real_speed_kmh": round(float(s_real), 1),
                "speed_delta_kmh": round(float(s_sim - s_real), 1)
            })

        return {
            "session_id": session.id,
            "vehicle_id": session.vehicle_id,
            "variant_id": session.variant_id,
            "real_lap_time_s": round(float(real_lap_time), 3),
            "simulated_lap_time_s": round(float(sim_res.total_time_s), 3),
            "delta_s": round(float(delta_s), 3),
            "percentage_error": round(float(percentage_error), 2),
            "real_max_speed_kmh": round(real_max_speed, 1),
            "simulated_max_speed_kmh": round(float(sim_res.max_speed_kmh), 1),
            "real_avg_speed_kmh": round(real_avg_speed, 1),
            "simulated_avg_speed_kmh": round(float(sim_res.avg_speed_kmh), 1),
            "speed_rmse_kmh": round(rmse, 2),
            "correlation_coefficient": round(correlation, 3),
            "sampled_comparison": sampled_points
        }
