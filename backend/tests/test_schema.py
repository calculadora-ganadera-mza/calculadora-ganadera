from datetime import date

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AnimalCategory,
    HerdCategory,
    HerdSeason,
    Parameter,
    ProductionUnit,
    Scenario,
    Season,
    User,
    WaterPoint,
    Zone,
)
from app.models.enums import ProductionSystem, RangeCondition

# Cuadrado de 1km de lado en UTM 19S (Mendoza), pasado a WGS 84.
SQUARE_1KM = func.ST_Transform(
    func.ST_MakeEnvelope(500000, 6350000, 501000, 6351000, 32719), 4326
)


@pytest.fixture
def herd(session: Session) -> HerdSeason:
    """Escenario con una unidad, una aguada, una campaña y su rodeo."""
    user = User(name="Prueba", email="prueba@example.com", password_hash="x")
    session.add(user)
    session.flush()

    zone = session.scalars(select(Zone).where(Zone.name == "Subzona A")).one()
    scenario = Scenario(user_id=user.id, zone_id=zone.id, name="Campo")
    session.add(scenario)
    session.flush()

    unit = ProductionUnit(
        scenario_id=scenario.id,
        name="Potrero",
        production_system=ProductionSystem.RAINFED,
        polygon=SQUARE_1KM,
    )
    season = Season(
        scenario_id=scenario.id,
        start_date=date(2025, 7, 1),
        end_date=date(2026, 6, 30),
    )
    session.add_all([unit, season])
    session.flush()

    herd = HerdSeason(
        scenario_id=scenario.id,
        season_id=season.id,
        production_unit_id=unit.id,
        range_condition=RangeCondition.GOOD,
    )
    water_point = WaterPoint(
        production_unit_id=unit.id,
        name="Aguada",
        location=func.ST_Centroid(SQUARE_1KM),
    )
    session.add_all([herd, water_point])
    session.flush()
    return herd


@pytest.fixture
def cows(session: Session, herd: HerdSeason) -> HerdCategory:
    """100 vacas en el rodeo de prueba."""
    cow = session.scalars(
        select(AnimalCategory).where(AnimalCategory.code == "cow")
    ).one()
    cows = HerdCategory(herd_season_id=herd.id, animal_category_id=cow.id, quantity=100)
    session.add(cows)
    session.flush()
    return cows


def test_seed_data_is_loaded(session: Session):
    keys = set(session.scalars(select(Parameter.key)))

    assert session.scalar(select(func.count()).select_from(Zone)) == 6
    assert session.scalar(select(func.count()).select_from(AnimalCategory)) == 5
    assert "cow_equivalent_dm_intake_kg_year" in keys


def test_area_is_calculated_from_polygon(session: Session, herd: HerdSeason):
    unit = session.get_one(ProductionUnit, herd.production_unit_id)
    session.refresh(unit)

    assert unit.area_ha == pytest.approx(100, abs=1)


def test_herd_season_is_unique_per_season_and_unit(session: Session, herd: HerdSeason):
    duplicate = HerdSeason(
        scenario_id=herd.scenario_id,
        season_id=herd.season_id,
        production_unit_id=herd.production_unit_id,
        range_condition=RangeCondition.FAIR,
    )

    with (
        pytest.raises(IntegrityError, match="uq_herd_season"),
        session.begin_nested(),
    ):
        session.add(duplicate)


def test_herd_category_is_unique_per_herd_and_category(
    session: Session, cows: HerdCategory
):
    duplicate = HerdCategory(
        herd_season_id=cows.herd_season_id,
        animal_category_id=cows.animal_category_id,
        quantity=5,
    )

    with (
        pytest.raises(IntegrityError, match="uq_herd_category"),
        session.begin_nested(),
    ):
        session.add(duplicate)


def test_deleting_scenario_cascades(session: Session, cows: HerdCategory):
    herd = session.get_one(HerdSeason, cows.herd_season_id)

    session.execute(delete(Scenario).where(Scenario.id == herd.scenario_id))

    for model in (ProductionUnit, WaterPoint, Season, HerdSeason, HerdCategory):
        assert session.scalar(select(func.count()).select_from(model)) == 0
