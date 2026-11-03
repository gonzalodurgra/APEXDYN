"""Endpoints REST para el módulo de simulación de resistencia y fiabilidad."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.endurance import EnduranceRequest, EnduranceResult
from app.services.endurance_service import EnduranceService

router = APIRouter(prefix="/endurance", tags=["endurance"])

@router.post(
    "/simulate",
    response_model=EnduranceResult,
    summary="Ejecutar simulación de carrera de resistencia y fiabilidad",
    description="Simula una carrera de resistencia completa vuelta a vuelta considerando desgaste mecánico, Weibull, degradación térmica, consumo de combustible y paradas en boxes."
)
def run_endurance_simulation(
    request: EnduranceRequest,
    db: Session = Depends(get_db),
) -> EnduranceResult:
    try:
        return EnduranceService.run(db=db, request=request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la simulación de resistencia: {str(e)}",
        )
