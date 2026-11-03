"""Script de población con trazados reales: Nürburgring Nordschleife y Tramo de Rally Col de Turini.

Incluye geometría GPS procesada (TrackGeometryPointCreate), condiciones ambientales
(TrackConditionCreate) y perfiles de superficie.
"""

import sys
import os
import math
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.services.track_service import TrackService
from app.schemas.track import (
    TrackCreate,
    TrackVariantCreate,
    TrackGeometryPointCreate,
    SurfaceSegmentCreate,
    TrackConditionCreate,
)

import numpy as np


def generate_nordschleife_gps_points(center_lat=50.3356, center_lon=6.9475, num_points=400):
    """
    Genera una traza de coordenadas GPS representativa y detallada del Nordschleife (el 'Infierno Verde').
    Simula el circuito cerrado de ~20.8 km con desniveles entre 320m y 620m (Eifel)
    y sectores emblemáticos (Hatzenbach, Flugplatz, Adenauer Forst, Karussell, Pflanzgarten, Döttinger Höhe)
    con radios de giro característicos entre 40 m y 500 m.
    """
    import numpy as np
    thetas = np.linspace(0, 2 * math.pi, num_points, endpoint=False)
    # Modulación armónica para reproducir las 73 curvas y las transiciones lentas/rápidas
    r_mod = (
        1.0
        + 0.18 * np.sin(3 * thetas)
        + 0.12 * np.cos(5 * thetas)
        + 0.08 * np.sin(7 * thetas)
        + 0.028 * np.sin(19 * thetas)
        + 0.018 * np.cos(31 * thetas)
        + 0.012 * np.sin(47 * thetas)
    )
    rx = 0.033
    ry = 0.022
    lons = center_lon + rx * r_mod * np.cos(thetas)
    lats = center_lat + ry * r_mod * np.sin(thetas)
    elevs = 470.0 + 130.0 * np.sin(2 * thetas + 0.5) + 35.0 * np.cos(4 * thetas)

    points = []
    for i, (lo, la, el) in enumerate(zip(lons, lats, elevs)):
        points.append(
            TrackGeometryPointCreate(
                sequence=i + 1,
                longitude=round(float(lo), 6),
                latitude=round(la, 6),
                elevation_m=round(float(el), 1),
            )
        )
    return points


def generate_turini_gps_points(start_lat=43.9100, start_lon=7.3300, num_points=350):
    """
    Genera una traza de coordenadas GPS representativa del Col de Turini (Rally Monte-Carlo).
    Simula el tramo abierto A -> B de subida de montaña desde La Bollène-Vésubie hasta la cima,
    con horquillas consecutivas y una ganancia de elevación de ~1100 metros (de 500m a 1607m).
    """
    import numpy as np
    frac = np.linspace(0, 1, num_points)
    # Sinuosidad alpina con curvas de horquilla (hairpins) consecutivas de radio cerrado
    sin_lon = 0.0022 * np.sin(frac * 28 * math.pi)
    sin_lat = 0.0012 * np.cos(frac * 20 * math.pi)

    lats = start_lat + 0.052 * frac + sin_lat
    lons = start_lon + 0.044 * frac + sin_lon
    elev = 500.0 + (1607.0 - 500.0) * (frac ** 0.95)

    points = []
    for i, (lo, la, el) in enumerate(zip(lons, lats, elev)):
        points.append(
            TrackGeometryPointCreate(
                sequence=i + 1,
                longitude=round(float(lo), 6),
                latitude=round(float(la), 6),
                elevation_m=round(float(el), 1),
            )
        )
    return points


def seed_tracks():
    db = SessionLocal()
    try:
        print("Poblando circuitos y tramos de rally con geometría y condiciones...")

        # =====================================================================
        # 1. CIRCUITO DE ENSAYO Y ALTO RENDIMIENTO: Nürburgring Nordschleife
        # =====================================================================
        existing_nurburgring = TrackService.list(db, search="Nordschleife")[0]
        if not existing_nurburgring:
            nurburgring = TrackService.create(
                db,
                TrackCreate(
                    name="Nürburgring Nordschleife",
                    track_type="CIRCUIT",
                    country_code="DE",
                    region="Renania-Palatinado",
                    official_length_m=20832.0,
                    is_public_road=True,  # Touristenfahrten en peaje
                    latitude=50.3356,
                    longitude=6.9475,
                    description="El 'Infierno Verde'. 20.832 km de asfalto histórico con más de 300 m de desnivel y 73 curvas.",
                    website="https://nuerburgring.de",
                ),
            )

            # Puntos GPS con latitud, longitud y elevación para geometría PostGIS
            nordschleife_points = generate_nordschleife_gps_points(50.3356, 6.9475, num_points=73)

            # Variante oficial BTG / Full lap con geometría importada y procesada
            variant = TrackService.create_variant(
                db,
                nurburgring.id,
                TrackVariantCreate(
                    track_id=nurburgring.id,
                    name="Vuelta Completa (20.832 km)",
                    direction="clockwise",
                    is_closed_loop=True,
                    length_m=20832.0,
                    version_number=1,
                    quality_status="validated",
                    raw_points=nordschleife_points,
                ),
            )

            # Segmento de asfalto estándar
            TrackService.add_surface_segment(
                db,
                SurfaceSegmentCreate(
                    variant_id=variant.id,
                    start_distance_m=0.0,
                    end_distance_m=20832.0,
                    surface_type="asphalt",
                    roughness_index=1.35,
                    wetness=0.0,
                    notes="Asfalto de circuito con variaciones de agarre entre sectores de bosque.",
                ),
            )

            # Condiciones meteorológicas de sesión (condiciones óptimas de récord en Nordschleife)
            TrackService.add_track_condition(
                db,
                TrackConditionCreate(
                    variant_id=variant.id,
                    recorded_at=datetime.now(timezone.utc),
                    air_temperature_c=18.5,
                    surface_temperature_c=24.0,
                    wetness=0.0,
                    rainfall_mm_h=0.0,
                    wind_speed_m_s=2.0,
                    wind_direction_deg=180.0,
                    surface_condition="dry",
                    source="Nürburgring Weather Station / Döttinger Höhe",
                ),
            )
            print("[OK] Nordschleife poblado con geometria (73 puntos) y condiciones.")
        else:
            # Si ya existia sin puntos, importar geometria
            variant = existing_nurburgring[0].variants[0] if existing_nurburgring[0].variants else None
            if variant and len(variant.points) == 0:
                nordschleife_points = generate_nordschleife_gps_points(50.3356, 6.9475, num_points=73)
                TrackService.import_and_process_track_geometry(db, variant.id, nordschleife_points, is_closed=True)
                TrackService.add_track_condition(
                    db,
                    TrackConditionCreate(
                        variant_id=variant.id,
                        recorded_at=datetime.now(timezone.utc),
                        air_temperature_c=18.5,
                        surface_temperature_c=24.0,
                        wetness=0.0,
                        surface_condition="dry",
                        source="Nürburgring Weather Station",
                    ),
                )
                print("[OK] Geometria de Nordschleife actualizada con exito.")

        # =====================================================================
        # 2. TRAMO DE RALLY: Rallye Monte-Carlo - Col de Turini
        # =====================================================================
        existing_turini = TrackService.list(db, search="Col de Turini")[0]
        if not existing_turini:
            turini = TrackService.create(
                db,
                TrackCreate(
                    name="Col de Turini (La Bollène-Vésubie - Moulinet)",
                    track_type="RALLY_STAGE",
                    country_code="FR",
                    region="Alpes Marítimos",
                    official_length_m=15200.0,
                    is_public_road=True,
                    latitude=43.9783,
                    longitude=7.3917,
                    description="Mítico tramo de montaña del Rally de Montecarlo. Horquillas cerradas consecutivas, estrechamientos y cambios drásticos de agarre.",
                ),
            )

            # Puntos GPS con latitud, longitud y elevación para el tramo de rally
            turini_points = generate_turini_gps_points(start_lat=43.9100, start_lon=7.3300, num_points=50)

            turini_variant = TrackService.create_variant(
                db,
                turini.id,
                TrackVariantCreate(
                    track_id=turini.id,
                    name="Subida Sur (La Bollène -> Turini)",
                    direction="forward",
                    is_closed_loop=False,  # Tramo abierto A -> B
                    length_m=15200.0,
                    version_number=1,
                    quality_status="validated",
                    raw_points=turini_points,
                ),
            )

            # Segmentos mixtos (asfalto de montaña + zonas húmedas con parches)
            TrackService.add_surface_segment(
                db,
                SurfaceSegmentCreate(
                    variant_id=turini_variant.id,
                    start_distance_m=0.0,
                    end_distance_m=8000.0,
                    surface_type="asphalt",
                    roughness_index=1.8,
                    wetness=0.05,
                    notes="Asfalto de montaña rugoso con gravilla suelta en los laterales.",
                ),
            )
            TrackService.add_surface_segment(
                db,
                SurfaceSegmentCreate(
                    variant_id=turini_variant.id,
                    start_distance_m=8000.0,
                    end_distance_m=15200.0,
                    surface_type="asphalt",
                    roughness_index=2.2,
                    wetness=0.25,
                    notes="Zona alta del Col con zonas húmedas y sombra continua.",
                ),
            )

            # Condiciones de tramo de rally (asfalto frío y tramos con humedad)
            TrackService.add_track_condition(
                db,
                TrackConditionCreate(
                    variant_id=turini_variant.id,
                    recorded_at=datetime.now(timezone.utc),
                    air_temperature_c=4.5,
                    surface_temperature_c=2.0,
                    wetness=0.15,
                    rainfall_mm_h=0.0,
                    wind_speed_m_s=5.0,
                    wind_direction_deg=315.0,
                    surface_condition="damp",
                    source="ACM / Rallye Monte-Carlo Reconnaissance",
                ),
            )
            print("[OK] Col de Turini poblado con geometria (50 puntos) y condiciones.")
        else:
            # Si ya existia sin puntos, importar geometria
            turini_variant = existing_turini[0].variants[0] if existing_turini[0].variants else None
            if turini_variant and len(turini_variant.points) == 0:
                turini_points = generate_turini_gps_points(start_lat=43.9100, start_lon=7.3300, num_points=50)
                TrackService.import_and_process_track_geometry(db, turini_variant.id, turini_points, is_closed=False)
                TrackService.add_track_condition(
                    db,
                    TrackConditionCreate(
                        variant_id=turini_variant.id,
                        recorded_at=datetime.now(timezone.utc),
                        air_temperature_c=4.5,
                        surface_temperature_c=2.0,
                        wetness=0.15,
                        surface_condition="damp",
                        source="ACM / Rallye Monte-Carlo Reconnaissance",
                    ),
                )
                print("[OK] Geometria de Col de Turini actualizada con exito.")

            # 3. CIRCUIT DE LA SARTHE (24 Horas de Le Mans)
            existing_lemans = TrackService.get_tracks(db, search="Le Mans")
            if not existing_lemans:
                print("Poblando Circuit de la Sarthe (24h de Le Mans)...")
                lemans_track = TrackService.create_track(
                    db,
                    TrackCreate(
                        name="Circuit des 24 Heures du Mans",
                        short_name="Le Mans (La Sarthe)",
                        country_code="FR",
                        city="Le Mans",
                        track_type="circuit",
                        is_active=True,
                        website="https://www.24h-lemans.com",
                        notes="Trazado legendario de 13.626 km con largas rectas (Hunaudières) y sectores de alta velocidad.",
                    ),
                )

                lemans_variant = TrackService.create_track_variant(
                    db,
                    TrackVariantCreate(
                        track_id=lemans_track.id,
                        name="Circuit 24 Heures (Modern con Chicanes)",
                        length_m=13626.0,
                        direction="clockwise",
                        turns_count=38,
                        is_closed_loop=True,
                        notes="Configuración moderna con chicanes en Hunaudières e Indianápolis.",
                    ),
                )

                # Generar traza representativa de Le Mans
                thetas = np.linspace(0, 2 * math.pi, 250, endpoint=False)
                # Trazado alargado norte-sur típico de la recta Hunaudières
                lons_lemans = 0.207 + 0.025 * np.cos(thetas) + 0.01 * np.sin(2 * thetas)
                lats_lemans = 47.954 + 0.045 * np.sin(thetas)
                elevs_lemans = 55.0 + 15.0 * np.sin(thetas)

                lemans_points = [
                    TrackGeometryPointCreate(
                        sequence=i,
                        latitude=float(lats_lemans[i]),
                        longitude=float(lons_lemans[i]),
                        elevation_m=float(elevs_lemans[i]),
                    )
                    for i in range(250)
                ]

                TrackService.import_and_process_track_geometry(db, lemans_variant.id, lemans_points, is_closed=True)

                TrackService.add_surface_segment(
                    db,
                    SurfaceSegmentCreate(
                        variant_id=lemans_variant.id,
                        start_distance_m=0.0,
                        end_distance_m=13626.0,
                        surface_type="asphalt",
                        roughness_index=1.05,
                        wetness=0.0,
                        notes="Asfalto de circuito permanente y sección de carretera pública de alta adherencia.",
                    ),
                )

                TrackService.add_track_condition(
                    db,
                    TrackConditionCreate(
                        variant_id=lemans_variant.id,
                        recorded_at=datetime.now(timezone.utc),
                        air_temperature_c=22.0,
                        surface_temperature_c=29.0,
                        wetness=0.0,
                        wind_speed_m_s=3.0,
                        wind_direction_deg=180.0,
                        surface_condition="dry",
                        source="ACO Official Weather Station",
                    ),
                )
                print("[OK] Circuit de la Sarthe poblado con 250 puntos y condiciones.")

        print("Población de pistas completada con éxito.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_tracks()
