"""seed reference data

Revision ID: 07340f0fc2e6
Revises: 665fa9925cbc
Create Date: 2026-10-21 00:52:05.501444

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "07340f0fc2e6"
down_revision: str | Sequence[str] | None = "665fa9925cbc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tablas mínimas para insertar. No se importan los modelos: pueden cambiar
# más adelante y esta migración tiene que seguir corriendo igual.
zone = sa.table(
    "zone",
    sa.column("name", sa.String),
    sa.column("mean_rainfall_mm", sa.Double),
    sa.column("reliable_rainfall_mm", sa.Double),
)
parameter = sa.table(
    "parameter",
    sa.column("key", sa.String),
    sa.column("description", sa.String),
    sa.column("value", sa.Double),
    sa.column("unit", sa.String),
    sa.column("confirmed", sa.Boolean),
    sa.column("producer_editable", sa.Boolean),
)
animal_category = sa.table(
    "animal_category",
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("cow_equivalent", sa.Double),
    sa.column("summer_water_l_day", sa.Double),
    sa.column("winter_water_l_day", sa.Double),
)

# Subzonas de la llanura de Mendoza (Guevara, Estevez y Torres, 1995).
ZONES = [
    {"name": "Subzona A", "mean_rainfall_mm": 408, "reliable_rainfall_mm": 315},
    {"name": "Subzona B", "mean_rainfall_mm": 350, "reliable_rainfall_mm": 255},
    {"name": "Subzona C", "mean_rainfall_mm": 275, "reliable_rainfall_mm": 185},
    {"name": "Subzona D", "mean_rainfall_mm": 225, "reliable_rainfall_mm": 150},
    {"name": "Subzona E", "mean_rainfall_mm": 175, "reliable_rainfall_mm": 110},
    {"name": "Subzona F", "mean_rainfall_mm": 135, "reliable_rainfall_mm": 78},
]

PARAMETERS = [
    {
        "key": "cow_equivalent_dm_intake_kg_year",
        "description": "Consumo de materia seca de un equivalente vaca",
        "value": 3285,
        "unit": "kg MS/año",
        "confirmed": True,
    },
    {
        "key": "water_point_radius_km",
        "description": "Alcance de una aguada",
        "value": 2.5,
        "unit": "km",
        "confirmed": True,
    },
    {
        "key": "rain_use_efficiency_herbaceous",
        "description": "Eficiencia de uso de la lluvia en herbáceas",
        "value": 2.15,
        "unit": "kg MS/ha/mm",
        "confirmed": True,
    },
    {
        "key": "rain_use_efficiency_woody",
        "description": "Eficiencia de uso de la lluvia en leñosas",
        "value": 1.4,
        "unit": "kg MS/ha/mm",
        "confirmed": True,
    },
    {
        "key": "accessible_fraction_herbaceous",
        "description": "Fracción accesible del forraje herbáceo",
        "value": 0.8,
        "unit": "fracción",
        "confirmed": True,
    },
    {
        "key": "accessible_fraction_woody",
        "description": "Fracción accesible del forraje leñoso",
        "value": 0.5,
        "unit": "fracción",
        "confirmed": True,
    },
    {
        "key": "forage_use_factor",
        "description": "Factor de uso del forraje",
        "value": 0.3,
        "unit": "fracción",
        "confirmed": True,
    },
    {
        "key": "feedlot_dm_intake_bw_fraction",
        "description": "Consumo diario en corral como fracción del peso vivo",
        "value": 0.035,
        "unit": "fracción del peso vivo por día",
        "confirmed": True,
    },
    {
        "key": "bulls_per_100_cows",
        "description": "Toros cada 100 vacas",
        "value": 4.5,
        "unit": "toros",
        "confirmed": True,
        "producer_editable": True,
    },
]

# Valores provisorios del clúster. El agua es el punto medio de cada rango.
ANIMAL_CATEGORIES = [
    {
        "code": "cow",
        "name": "Vaca",
        "cow_equivalent": 1.0,
        "summer_water_l_day": 70,
        "winter_water_l_day": 37.5,
    },
    {
        "code": "bull",
        "name": "Toro",
        "cow_equivalent": 1.3,
        "summer_water_l_day": 65,
        "winter_water_l_day": 30,
    },
    {
        "code": "heifer",
        "name": "Vaquillona",
        "cow_equivalent": 0.7,
        "summer_water_l_day": 42.5,
        "winter_water_l_day": 20,
    },
    {
        "code": "calf",
        "name": "Ternero",
        "cow_equivalent": 0.5,
        "summer_water_l_day": 25,
        "winter_water_l_day": 12.5,
    },
    {
        "code": "steer",
        "name": "Novillito",
        "cow_equivalent": 0.7,
        "summer_water_l_day": 42.5,
        "winter_water_l_day": 20,
    },
]


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(zone, ZONES)
    # Por defecto el productor no edita los parámetros.
    op.bulk_insert(
        parameter, [{"producer_editable": False, **row} for row in PARAMETERS]
    )
    op.bulk_insert(animal_category, ANIMAL_CATEGORIES)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        animal_category.delete().where(
            animal_category.c.code.in_([row["code"] for row in ANIMAL_CATEGORIES])
        )
    )
    op.execute(
        parameter.delete().where(
            parameter.c.key.in_([row["key"] for row in PARAMETERS])
        )
    )
    op.execute(zone.delete().where(zone.c.name.in_([row["name"] for row in ZONES])))
