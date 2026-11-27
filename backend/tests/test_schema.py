from datetime import date

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AnimalCategory,
    CarryingCapacityCalculation,
    HerdCategory,
    HerdSeason,
    Parameter,
    ProductionUnit,
    Scenario,
    Season,
    User,
    WaterPoint,
)
from app.models.enums import CalculationKind, ProductionSystem, RangeCondition

# Cuadrado de 1km de lado en UTM 19S (Mendoza), pasado a WGS 84.
SQUARE_1KM = func.ST_Transform(
    func.ST_MakeEnvelope(500000, 6350000, 501000, 6351000, 32719), 4326
)

INDEX_KEYS = [
    "range_condition_index_fair",
    "range_condition_index_good",
    "range_condition_index_very_good",
    "early_weaning_index",
    "supplementation_index",
]


@pytest.fixture
def herd(session: Session) -> HerdSeason:
    """Escenario con una unidad, una aguada, una campaña y su rodeo."""
    user = User(name="Prueba", email="prueba@example.com", password_hash="x")
    session.add(user)
    session.flush()

    scenario = Scenario(user_id=user.id, name="Campo")
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

    assert session.scalar(select(func.count()).select_from(AnimalCategory)) == 5
    assert "cow_equivalent_dm_intake_kg_year" in keys


def test_indices_are_loaded_without_value(session: Session):
    rows = session.execute(
        select(Parameter.key, Parameter.value).where(Parameter.key.in_(INDEX_KEYS))
    ).all()

    assert dict(rows) == dict.fromkeys(INDEX_KEYS)


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
    session.add(
        CarryingCapacityCalculation(
            scenario_id=herd.scenario_id,
            season_id=herd.season_id,
            production_unit_id=herd.production_unit_id,
            kind=CalculationKind.RESULT,
            input={},
            reference_values={},
            result={},
        )
    )
    session.flush()

    session.execute(delete(Scenario).where(Scenario.id == herd.scenario_id))

    for model in (
        ProductionUnit,
        WaterPoint,
        Season,
        HerdSeason,
        HerdCategory,
        CarryingCapacityCalculation,
    ):
        assert session.scalar(select(func.count()).select_from(model)) == 0


def test_carrying_capacity_result_is_unique_per_unit_and_season(
    session: Session, herd: HerdSeason
):
    base = {
        "scenario_id": herd.scenario_id,
        "season_id": herd.season_id,
        "production_unit_id": herd.production_unit_id,
        "input": {},
        "reference_values": {},
        "result": {},
    }
    session.add_all(
        [
            CarryingCapacityCalculation(**base, kind=CalculationKind.RESULT),
            CarryingCapacityCalculation(**base, kind=CalculationKind.SIMULATION),
            CarryingCapacityCalculation(**base, kind=CalculationKind.SIMULATION),
        ]
    )
    session.flush()

    with (
        pytest.raises(
            IntegrityError, match="uq_carrying_capacity_result_per_unit_season"
        ),
        session.begin_nested(),
    ):
        session.add(CarryingCapacityCalculation(**base, kind=CalculationKind.RESULT))


def test_carrying_capacity_calculation_requires_same_scenario(
    session: Session, herd: HerdSeason
):
    scenario = session.get_one(Scenario, herd.scenario_id)
    other_scenario = Scenario(user_id=scenario.user_id, name="Otro campo")
    session.add(other_scenario)
    session.flush()
    other_season = Season(
        scenario_id=other_scenario.id,
        start_date=date(2025, 7, 1),
        end_date=date(2026, 6, 30),
    )
    session.add(other_season)
    session.flush()

    with (
        pytest.raises(IntegrityError, match="fk_carrying_capacity_calc_season"),
        session.begin_nested(),
    ):
        session.add(
            CarryingCapacityCalculation(
                scenario_id=herd.scenario_id,
                season_id=other_season.id,
                production_unit_id=herd.production_unit_id,
                kind=CalculationKind.SIMULATION,
                input={},
                reference_values={},
                result={},
            )
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("cow_equivalent_dm_intake_kg_year", None),
        ("cow_equivalent_dm_intake_kg_year", 0),
        ("range_condition_index_good", 0),
        ("range_condition_index_good", -1),
    ],
)
def test_parameter_rejects_invalid_value(session: Session, key: str, value):
    parameter = session.scalars(select(Parameter).where(Parameter.key == key)).one()

    with (
        pytest.raises(IntegrityError, match="ck_parameter_value_positive"),
        session.begin_nested(),
    ):
        parameter.value = value


def test_index_accepts_positive_value(session: Session):
    parameter = session.scalars(
        select(Parameter).where(Parameter.key == "range_condition_index_good")
    ).one()

    parameter.value = 1.2
    session.flush()
