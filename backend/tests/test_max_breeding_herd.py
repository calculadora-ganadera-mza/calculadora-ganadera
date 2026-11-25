from dataclasses import replace

import pytest

from app.calculators.max_breeding_herd import (
    CategoryEquivalents,
    HerdParameters,
    annual_equivalents,
    calculate_max_breeding_herd,
    cow_equivalents_per_cow,
    replacement_rate_for_calculation,
    round_half_up,
)
from app.calculators.water import CategoryWater, herd_litres

# Valores del seed y de la migración de la #15
PARAMETERS = HerdParameters(
    bulls_per_100_cows=4.5,
    weaned_calf_female_share=0.5,
    normal_weaning_age_months=6,
    early_weaning_age_months=3,
    heifer_first_breeding_age_months=24,
)
EQUIVALENTS = CategoryEquivalents(cow=1, bull=1.3, calf=0.5, heifer=0.7)


def max_breeding(limit: float, *, replacement=0.2, weaning=0.5, early=False, fits=None):
    return calculate_max_breeding_herd(
        limit_cow_equivalents=limit,
        replacement_rate=replacement,
        weaning_rate=weaning,
        early_weaning=early,
        parameters=PARAMETERS,
        equivalents=EQUIVALENTS,
        fits=fits,
    )


def test_round_half_up():
    assert [round_half_up(x) for x in (2.4, 2.5, 3.5, 0.5)] == [2, 3, 4, 1]


# Ejemplo de la issue: 100 vacas, 20% de reposición y 50% de destete.
# Ternera: 0,5 EV × 6/12 = 0,25 (normal) o 0,5 × 9/12 = 0,375 (precoz).
# Vaquillona: 0,7 EV × (24 - 12)/12 = 0,7.
@pytest.mark.parametrize(
    ("early", "calf_ev", "total_ev"),
    [(False, 0.25, 19.0), (True, 0.375, 21.5)],
)
def test_issue_example_replacement_heifers(early, calf_ev, total_ev):
    calf, heifer = annual_equivalents(early, PARAMETERS, EQUIVALENTS)

    assert calf == pytest.approx(calf_ev)
    assert heifer == pytest.approx(0.7)
    assert 20 * calf + 20 * heifer == pytest.approx(total_ev)


def test_replacement_is_capped_by_weaned_females():
    # 30% de destete: 15 hembras cada 100 vacas. Se piden 20: se cuentan 15.
    rate, exceeds = replacement_rate_for_calculation(0.2, 0.3, 0.5)

    assert rate == pytest.approx(0.15)
    assert exceeds is True


def test_replacement_within_weaned_females_is_kept():
    rate, exceeds = replacement_rate_for_calculation(0.2, 0.5, 0.5)

    assert rate == pytest.approx(0.2)
    assert exceeds is False


def test_rounded_herd_is_lowered_until_it_fits():
    # Por vaca: 1 + 0,045 × 1,3 + 0,15 × (0,25 + 0,7) = 1,201 EV.
    # Con 120,1 EV entrarían 100 vacas, pero redondeadas suman
    # 100 + 5 toros × 1,3 + 15 × 0,95 = 120,75: se pasa.
    # Con 99 vacas: 99 + 4 × 1,3 + 15 × 0,95 = 118,45, que entra.
    herd = max_breeding(120.1, replacement=0.2, weaning=0.3)
    assert herd is not None

    assert (herd.cows, herd.bulls, herd.replacement_calves, herd.heifers) == (
        99,
        4,
        15,
        15,
    )
    assert herd.cow_equivalents == pytest.approx(118.45)
    assert (herd.weaned_males, herd.weaned_females) == (15, 15)


def test_with_cows_there_is_at_least_one_bull():
    # 1 vaca + 1 toro = 2,3 EV entra en 2,5; con 2 vacas serían 3,3.
    herd = max_breeding(2.5)

    assert herd is not None
    assert (herd.cows, herd.bulls, herd.replacement_calves) == (1, 1, 0)


def test_no_herd_when_a_cow_with_her_bull_does_not_fit():
    assert max_breeding(2.0) is None


def test_early_weaning_fits_fewer_cows():
    normal = max_breeding(500)
    early = max_breeding(500, early=True)

    assert early is not None
    assert normal is not None
    assert early.cows < normal.cows


@pytest.mark.parametrize("limit", [3, 7.7, 12.4, 55, 120.1, 333.3, 1000])
@pytest.mark.parametrize("weaning", [0.3, 0.5, 0.8])
@pytest.mark.parametrize("early", [False, True])
def test_max_breeding_herd_never_exceeds_the_limit(limit, weaning, early):
    herd = max_breeding(limit, weaning=weaning, early=early)

    assert herd is not None
    assert herd.cow_equivalents <= limit
    assert herd.replacement_calves <= herd.weaned_females
    assert herd.bulls >= 1


def test_cow_equivalents_per_cow():
    # 1 vaca + 0,045 * 1,3 + 0,2 * (0,25 + 0,7) = 1 + 0,0585 + 0,19 = 1,2485
    per_cow = cow_equivalents_per_cow(0.2, False, PARAMETERS, EQUIVALENTS)

    assert per_cow == pytest.approx(1.2485)


def test_extra_condition_lowers_cows():
    # Con 10 EV entran 7 vacas, 1 toro, 1 ternera y 1 vaquillona (9,25 EV).
    # Si la condición extra pide como máximo 6 vacas, baja una más.
    without_condition = max_breeding(10)
    with_condition = max_breeding(10, fits=lambda herd: herd.cows <= 6)

    assert without_condition is not None
    assert with_condition is not None
    assert without_condition.cows == 7
    assert with_condition.cows == 6


def test_herd_that_fits_exactly_is_not_lost_to_rounding():
    # 10 toros cada 100 vacas y sin reposición: 10 vacas y 1 toro suman
    # 10 × 1 + 1 × 1,3 = 11,3 EV. Un límite calculado en punto flotante puede
    # dar 11,299999999999999 en vez de 11,3.
    herd = calculate_max_breeding_herd(
        limit_cow_equivalents=11.299999999999999,
        replacement_rate=0,
        weaning_rate=0.5,
        early_weaning=False,
        parameters=replace(PARAMETERS, bulls_per_100_cows=10),
        equivalents=EQUIVALENTS,
    )

    assert herd is not None
    assert (herd.cows, herd.bulls) == (10, 1)


def test_can_be_above_the_max_herd():
    # Con 7.000 l/día, un rodeo actual de 100 vacas a 70 L/EV tiene un rodeo
    # máximo de 100 EV. El rodeo de cría parte de un límite por pasto de 200 EV y
    # baja hasta que sus litros de verano entran. Con entore el 1/1 las terneras
    # no toman agua en verano y las vaquillonas toman menos por EV que las vacas.
    # 86 vacas, 4 toros, 17 terneras y 17 vaquillonas piden
    # 6.020 + 260 + 722,5 = 7.002,5 l/día: no entran.
    # 85 vacas, 4 toros, 17 y 17 piden 6.932,5 l/día y suman
    # 85 + 5,2 + 17 × 0,95 = 106,35 EV.
    summer = CategoryWater(cow=70, bull=65, calf=0, heifer=42.5)
    herd = max_breeding(
        200, fits=lambda candidate: herd_litres(candidate, summer) <= 7000
    )

    assert herd is not None
    assert herd.cows == 85
    assert herd.cow_equivalents == pytest.approx(106.35)
