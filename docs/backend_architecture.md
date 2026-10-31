# Documentación Técnica del Proyecto

## Arquitectura del Backend

- **Framework Web**: FastAPI con especificación OpenAPI en `/api/v1/docs`.
- **Motor ORM**: SQLAlchemy 2.x declarativo con tipos estrictos (`Mapped[...]` y `mapped_column`).
- **Conector de Base de Datos**: `psycopg` 3 binario con soporte nativo para PostgreSQL.
- **Base de Datos y Datos Espaciales**: PostgreSQL 18 con extensión **PostGIS 3.6** habilitada.
- **Migraciones**: Alembic configurado para autogenerar y rastrear cambios de esquema sobre `Base.metadata`.
- **Capa Espacial**: GeoAlchemy2 con soporte para `Geometry` y `Geography`, proyecciones métricas locales ($x, y, z$) y sistemas SRID 4326.

## Estructura de Directorios

```
backend/
├── alembic/                # Historial y configuración de migraciones
│   ├── versions/           # Scripts de migración individuales
│   ├── env.py              # Conexión y target_metadata de Alembic
│   └── script.py.mako      # Plantilla con GeoAlchemy2
├── app/
│   ├── core/
│   │   ├── config.py       # Pydantic Settings y variables de entorno
│   │   └── database.py     # Motor SQLAlchemy y sesiones
│   ├── models/
│   │   ├── base.py         # Base declarativa y helpers UUID
│   │   ├── vehicle.py      # Fabricantes, Vehículos, Motores, Cajas, Suspensiones, Aero, Neumáticos
│   │   ├── track.py        # Trazados, Variantes, Geometría PostGIS, Elevación, Superficies, Condiciones
│   │   ├── simulation.py   # Pilotos, Sesiones de Telemetría, Mediciones Reales y Simulaciones
│   │   └── __init__.py     # Re-exportación unificada
│   └── main.py             # Aplicación FastAPI con CORS y /health
├── tests/
│   ├── test_phase1_database.py # Pruebas de integración de BD, ORM y PostGIS
│   └── test_api_health.py      # Pruebas de API y endpoint /health
├── pytest.ini
├── requirements.txt
└── .env
```
