from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

TABLES = {
    "animal_category",
    "app_user",
    "herd_category",
    "herd_season",
    "parameter",
    "production_unit",
    "scenario",
    "season",
    "water_point",
    "zone",
}


def test_migrations_go_down_and_up(alembic_config: Config, engine: Engine):
    command.downgrade(alembic_config, "base")
    assert TABLES.isdisjoint(inspect(engine).get_table_names())

    command.upgrade(alembic_config, "head")
    assert set(inspect(engine).get_table_names()) >= TABLES
