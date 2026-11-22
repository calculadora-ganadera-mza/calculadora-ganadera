from datetime import date

import pytest

from app.calculators.recommended_herd import HerdParameters, RecommendedHerd
from app.calculators.water import (
    CategoryWater,
    WaterParameters,
    herd_calendar,
    herd_litres,
    litres_per_cow,
    max_herd,
    months_between,
    season_litres,
    stage_months,
    water_limit,
)
from app.models.enums import LimitedBy

# Valores del seed y de las migraciones de la #14 y la #15
HERD = HerdParameters(
    bulls_per_100_cows=4.5,
    weaned_calf_female_share=0.5,
    normal_weaning_age_months=6,
    early_weaning_age_months=3,
    heifer_first_breeding_age_months=24,
)
WATER = WaterParameters(
    gestation_days=283,
    summer_start_month=12,
    summer_end_month=2,
    winter_start_month=6,
    winter_end_month=8,
)
SUMMER = months_between(12, 2)
# Agua en verano de la tabla de categorías
SUMMER_LITRES = CategoryWater(cow=70, bull=65, calf=25, heifer=42.5)


def test_months_between():
    assert months_between(6, 8) == {6, 7, 8}
    assert months_between(12, 2) == {12, 1, 2}


# Entore 1/11: parto 11/8, destete 11/2; tocan febrero a agosto.
# Entore 1/1: parto 11/10, destete 11/4; tocan abril a octubre.
# Entore 1/1 con destete precoz: destete 11/1; tocan enero a octubre.
# Entore 1/9: parto 11/6, destete 11/12; la etapa cruza el fin de año.
@pytest.mark.parametrize(
    ("breeding_start", "early", "calf_months"),
    [
        (date(2026, 11, 1), False, {2, 3, 4, 5, 6, 7, 8}),
        (date(2027, 1, 1), False, {4, 5, 6, 7, 8, 9, 10}),
        (date(2027, 1, 1), True, set(range(1, 11))),
        (date(2026, 9, 1), False, {12, 1, 2, 3, 4, 5, 6}),
    ],
)
def test_calf_months(breeding_start, early, calf_months):
    calendar = herd_calendar(breeding_start, early, HERD, WATER)

    assert calendar.calf_months == calf_months
    # De 12 a 24 meses: las vaquillonas están todo el año.
    assert calendar.heifer_months == set(range(1, 13))


def test_stage_ends_the_day_the_age_is_reached():
    # Parto el 1/8: destete el 1/2 y el año el 1/8, así que agosto no cuenta.
    assert stage_months(date(2027, 8, 1), 6, 12) == {2, 3, 4, 5, 6, 7}


# Ejemplo de la issue: 100 vacas, 4,5 toros, 20 terneras y 20 vaquillonas.
# 7.000 + 292,5 + 500 + 850 = 8.642,5 con terneras; sin ellas, 8.142,5.
@pytest.mark.parametrize(
    ("breeding_start", "litres"),
    [(date(2026, 11, 1), 8642.5), (date(2027, 1, 1), 8142.5)],
)
def test_issue_example_summer_litres(breeding_start, litres):
    calendar = herd_calendar(breeding_start, False, HERD, WATER)
    summer = season_litres(SUMMER_LITRES, calendar, SUMMER)

    assert 100 * litres_per_cow(summer, 0.2, HERD) == pytest.approx(litres)


def test_water_limit():
    # Con 8.642,5 l/día entran justo las 100 vacas del ejemplo: 124,85 EV.
    limit = water_limit(
        available_l_day=8642.5,
        composition_l_day=86.425,
        composition_cow_equivalents=1.2485,
    )

    assert limit == pytest.approx(124.85)


def test_herd_litres():
    herd = RecommendedHerd(
        cows=7,
        bulls=1,
        replacement_calves=1,
        heifers=1,
        cow_equivalents=9.25,
        weaned_males=2,
        weaned_females=2,
    )

    # 490 + 65 + 25 + 42,5
    assert herd_litres(herd, SUMMER_LITRES) == pytest.approx(622.5)


@pytest.mark.parametrize(
    ("water", "expected"),
    [
        (None, (100, LimitedBy.PASTURE)),
        (80, (80, LimitedBy.WATER)),
        (120, (100, LimitedBy.PASTURE)),
    ],
)
def test_max_herd(water, expected):
    assert max_herd(100, water) == expected
