"""Pruebas automatizadas de la Fase 7: Telemetría Real, Parseo de Archivos y Validación Cruzada QSS."""

import uuid
import pytest
from datetime import datetime, timezone
from app.services.telemetry_service import TelemetryService


SAMPLE_MOTEC_CSV = """Time,Distance,Speed,RPM,Gear,Throttle,Brake,LatAcc,LongAcc
0.0,0.0,0.0,1000,1,0.0,0.0,0.0,0.0
0.5,5.0,36.0,3200,1,100.0,0.0,0.0,2.1
1.0,20.0,72.0,6000,1,100.0,0.0,0.0,2.3
1.5,45.0,108.0,4200,2,100.0,0.0,0.1,1.8
2.0,80.0,144.0,5500,2,100.0,0.0,0.2,1.5
2.5,125.0,180.0,6800,2,100.0,0.0,0.1,1.2
3.0,170.0,144.0,5500,2,0.0,80.0,0.3,-3.8
3.5,200.0,108.0,4200,2,0.0,80.0,0.5,-3.5
4.0,225.0,72.0,2800,2,20.0,20.0,1.2,-0.5
"""


SAMPLE_RACECHRONO_CSV = """# RaceChrono Export
# Format: standard_v2
elapsed_time,lap_dist_m,gps_speed,eng_rpm,n_gear,tps,ay,ax
0.0,0.0,0.0,950,1,0,0.0,0.0
0.2,2.0,30.0,2500,1,80,0.0,1.8
0.4,8.0,60.0,4800,1,100,0.0,2.0
0.6,18.0,90.0,7000,1,100,0.0,1.9
0.8,32.0,120.0,4900,2,100,0.0,1.7
"""


def test_parse_motec_csv():
    samples = TelemetryService.parse_csv_telemetry(SAMPLE_MOTEC_CSV)
    assert len(samples) == 9
    assert samples[0]["sample_index"] == 0
    assert samples[0]["speed_m_s"] == 0.0
    # A 180 km/h -> 50 m/s
    assert samples[5]["speed_m_s"] == pytest.approx(180.0 / 3.6, rel=1e-2)
    assert samples[5]["gear"] == 2
    assert samples[6]["brake_percent"] == 80.0
    assert samples[8]["lateral_acceleration_m_s2"] == 1.2


def test_parse_racechrono_csv():
    samples = TelemetryService.parse_csv_telemetry(SAMPLE_RACECHRONO_CSV)
    assert len(samples) == 5
    assert samples[1]["throttle_percent"] == 80.0
    assert samples[4]["engine_rpm"] == 4900.0
    assert samples[4]["speed_m_s"] == pytest.approx(120.0 / 3.6, rel=1e-2)


def test_invalid_csv_raises_error():
    with pytest.raises(ValueError, match="No se encontraron cabeceras válidas"):
        TelemetryService.parse_csv_telemetry("col1,col2,col3\n1,2,3")
