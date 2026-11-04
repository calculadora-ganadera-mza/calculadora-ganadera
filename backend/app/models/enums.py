from enum import StrEnum

from sqlalchemy import Enum


class Role(StrEnum):
    PRODUCER = "producer"
    TECHNICIAN = "technician"
    ADMIN = "admin"


def pg_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Enum nativo de PostgreSQL que guarda el valor del miembro, no su nombre."""
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class ProductionSystem(StrEnum):
    RAINFED = "rainfed"
    IRRIGATED = "irrigated"
    FEEDLOT = "feedlot"


class RangeCondition(StrEnum):
    FAIR = "fair"
    GOOD = "good"
    VERY_GOOD = "very_good"
