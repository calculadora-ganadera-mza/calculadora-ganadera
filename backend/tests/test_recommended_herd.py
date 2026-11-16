import pytest

from app.calculators.recommended_herd import (
    CategoryEquivalents,
    HerdParameters,
    annual_equivalents,
    recommend_herd,
    replacement_rate_for_calculation,
    round_half_up,
)

# Valores del seed y de la migración de la #15
PARAMETERS = HerdParameters(
    bulls_per_100_cows=4.5,
    weaned_calf_female_share=0.5,
    normal_weaning_age_months=6,
    early_weaning_age_months=3,
    heifer_first_breeding_age_months=24,
)
EQUIVALENTS = CategoryEquivalents(cow=1, bull=1.3, calf=0.5, heifer=0.7)


def recommend(limit: float, *, replacement=0.2, weaning=0.5, early=False):
    return recommend_herd(
        limit_cow_equivalents=limit,
        replacement_rate=replacement,
        weaning_rate=weaning,
        early_weaning=early,
        parameters=PARAMETERS,
        equivalents=EQUIVALENTS,
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
    herd = recommend(120.1, replacement=0.2, weaning=0.3)

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
    herd = recommend(2.5)

    assert (herd.cows, herd.bulls, herd.replacement_calves) == (1, 1, 0)


def test_no_herd_when_a_cow_with_her_bull_does_not_fit():
    assert recommend(2.0) is None


def test_early_weaning_fits_fewer_cows():
    normal = recommend(500)
    early = recommend(500, early=True)

    assert early.cows < normal.cows


@pytest.mark.parametrize("limit", [3, 7.7, 12.4, 55, 120.1, 333.3, 1000])
@pytest.mark.parametrize("weaning", [0.3, 0.5, 0.8])
@pytest.mark.parametrize("early", [False, True])
def test_recommended_herd_never_exceeds_the_limit(limit, weaning, early):
    herd = recommend(limit, weaning=weaning, early=early)

    assert herd.cow_equivalents <= limit
    assert herd.replacement_calves <= herd.weaned_females
    assert herd.bulls >= 1
