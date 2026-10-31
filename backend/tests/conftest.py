"""Pytest fixtures compartidas para la suite de pruebas del backend."""

import pytest
from app.core.database import SessionLocal


@pytest.fixture
def db_session():
    """Proporciona una sesión de base de datos para pruebas que lo requieran."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
