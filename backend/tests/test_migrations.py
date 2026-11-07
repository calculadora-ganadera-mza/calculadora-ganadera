from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

TABLES = {
    "animal_category",
    "app_user",
    "refresh_session",
    "herd_category",
    "herd_season",
    "parameter",
    "production_unit",
    "scenario",
    "season",
    "water_point",
}

# Migración anterior a la que quita las subzonas.
BEFORE_DROP_ZONE = "07340f0fc2e6"


def test_migrations_go_down_and_up(alembic_config: Config, engine: Engine):
    command.downgrade(alembic_config, "base")
    assert TABLES.isdisjoint(inspect(engine).get_table_names())

    command.upgrade(alembic_config, "head")
    assert set(inspect(engine).get_table_names()) >= TABLES


def test_zone_is_dropped_and_restored(alembic_config: Config, engine: Engine):
    command.downgrade(alembic_config, BEFORE_DROP_ZONE)
    with engine.connect() as connection:
        zones = connection.scalar(text("SELECT count(*) FROM zone"))
    columns = {c["name"]: c for c in inspect(engine).get_columns("scenario")}

    # Se vuelve a la última migración antes de comprobar, para no dejar la
    # base a medio camino si algo falla.
    command.upgrade(alembic_config, "head")
    inspector = inspect(engine)

    assert zones == 6
    assert columns["zone_id"]["nullable"]
    assert "zone" not in inspector.get_table_names()
    assert "zone_id" not in {c["name"] for c in inspector.get_columns("scenario")}
