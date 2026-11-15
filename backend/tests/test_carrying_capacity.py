from dataclasses import replace

import pytest

from app.calculators.carrying_capacity import (
    NotCalculableError,
    PastureParameters,
    calculate_pasture_limit,
    consumable_forage_kg_ha_year,
)
from app.models.enums import RangeCondition

# Valores de la migración inicial, sin índices cargados.
PARAMETERS = PastureParameters(
    cow_equivalent_dm_intake_kg_year=3285,
    rain_use_efficiency_herbaceous=2.15,
    rain_use_efficiency_woody=1.4,
    accessible_fraction_herbaceous=0.8,
    accessible_fraction_woody=0.5,
    forage_use_factor=0.3,
    range_condition_index_fair=None,
    range_condition_index_good=None,
    range_condition_index_very_good=None,
    early_weaning_index=None,
    supplementation_index=None,
)
WITH_INDICES = replace(
    PARAMETERS,
    range_condition_index_fair=0.5,
    range_condition_index_good=1.0,
    range_condition_index_very_good=2.0,
    early_weaning_index=1.2,
    supplementation_index=1.25,
)


def calculate(
    parameters=PARAMETERS,
    *,
    rainfall_mm=300,
    usable_area_ha=1000,
    range_condition=RangeCondition.GOOD,
    early_weaning=False,
    supplemented=False,
):
    return calculate_pasture_limit(
        rainfall_mm=rainfall_mm,
        usable_area_ha=usable_area_ha,
        range_condition=range_condition,
        early_weaning=early_weaning,
        supplemented=supplemented,
        parameters=parameters,
    )


def test_each_mm_of_rain_gives_0_73_kg_of_consumable_forage():
    # (2,15 × 0,8 + 1,4 × 0,5) × 0,3 = 0,726
    assert consumable_forage_kg_ha_year(1, PARAMETERS) == pytest.approx(0.726)


def test_without_indices_300_mm_needs_15_1_ha_per_cow_equivalent():
    # 300 × 0,726 = 217,8 kg MS/ha; 3285 ÷ 217,8 = 15,08 ha/EV
    result = calculate()

    assert round(result.carrying_capacity_ha_per_cow_equivalent, 1) == 15.1
    # 1000 ha ÷ 15,08 ha/EV = 66,30 EV
    assert result.pasture_limit_cow_equivalents == pytest.approx(66.30, abs=0.01)
    assert result.missing_index


def test_checked_indices_divide_the_carrying_capacity():
    # 15,08 ÷ (1,0 × 1,2 × 1,25) = 15,08 ÷ 1,5 = 10,06 ha/EV; 1000 ÷ 10,06 = 99,45 EV
    result = calculate(WITH_INDICES, early_weaning=True, supplemented=True)

    assert result.carrying_capacity_ha_per_cow_equivalent == pytest.approx(
        10.055, abs=0.001
    )
    assert result.pasture_limit_cow_equivalents == pytest.approx(99.45, abs=0.01)
    assert not result.missing_index


def test_unchecked_boxes_do_not_apply_their_indices():
    # Solo cuenta el índice del estado bueno, 1,0.
    result = calculate(WITH_INDICES)

    assert round(result.carrying_capacity_ha_per_cow_equivalent, 1) == 15.1
    assert not result.missing_index


@pytest.mark.parametrize(
    ("range_condition", "expected"),
    [
        (RangeCondition.FAIR, 30.17),  # 15,08 ÷ 0,5
        (RangeCondition.GOOD, 15.08),  # 15,08 ÷ 1,0
        (RangeCondition.VERY_GOOD, 7.54),  # 15,08 ÷ 2,0
    ],
)
def test_each_range_condition_uses_its_own_index(range_condition, expected):
    result = calculate(WITH_INDICES, range_condition=range_condition)

    assert result.carrying_capacity_ha_per_cow_equivalent == pytest.approx(
        expected, abs=0.01
    )


def test_missing_index_is_skipped_and_reported():
    # Destete precoz marcado sin valor: 15,08 ÷ (1,0 × 1,25) = 12,07 ha/EV
    parameters = replace(WITH_INDICES, early_weaning_index=None)

    result = calculate(parameters, early_weaning=True, supplemented=True)

    assert result.carrying_capacity_ha_per_cow_equivalent == pytest.approx(
        12.07, abs=0.01
    )
    assert result.missing_index


@pytest.mark.parametrize(
    ("rainfall_mm", "usable_area_ha"), [(0, 1000), (-10, 1000), (300, 0)]
)
def test_does_not_calculate_without_rain_or_usable_area(rainfall_mm, usable_area_ha):
    with pytest.raises(NotCalculableError):
        calculate(rainfall_mm=rainfall_mm, usable_area_ha=usable_area_ha)
