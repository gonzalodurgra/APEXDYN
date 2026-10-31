"""Clase Base declarativa y funciones comunes para modelos SQLAlchemy."""

import uuid
from sqlalchemy.orm import DeclarativeBase


def uuid4() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass
