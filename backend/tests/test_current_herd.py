import pytest

from app.calculators.current_herd import (
    herd_total,
    herd_with_calves,
    load_status,
    scale_herd,
)
from app.calculators.max_breeding_herd import HerdParameters
from app.calculators.water import max_herd, water_limit
from app.models.enums import LimitedBy

# Valores del seed y de las migraciones de la #14 y la #15
PARAMETERS = HerdParameters(
    bulls_per_100_cows=4.5,
    weaned_calf_female_share=0.5,
    normal_weaning_age_months=6,
    early_weaning_age_months=3,
    heifer_first_breeding_age_months=24,
)
# EV de la tabla de categorías. La ternera de reposición va con su valor
# anual con destete normal: 0,5 * 6 / 12 = 0,25.
EQUIVALENTS = {"cow": 1, "bull": 1.3, "heifer": 0.7, "steer": 0.8, "calf": 0.25}
# Agua en verano de la tabla de categorías. Con entore el 1/1 las terneras de
# reposición están en el campo de abril a octubre: en verano valen 0.
SUMMER_LITRES = {"cow": 70, "bull": 65, "heifer": 42.5, "steer": 42.5, "calf": 0}


@pytest.mark.parametrize(
    ("current", "expected"),
    [(89.999, "below"), (90, "within"), (100, "within"), (100.001, "above")],
)
def test_load_status_uses_unrounded_boundaries(current, expected):
    assert load_status(current, 100, 90) == expected


@pytest.mark.parametrize(
    ("refill_l_day", "expected"), [(70, "within"), (69.9999, "above")]
)
def test_load_status_at_the_water_limit(refill_l_day, expected):
    herd = {"cow": 1}
    equivalents = {"cow": 0.98}
    current = herd_total(herd, equivalents)
    limit = water_limit(
        available_l_day=refill_l_day,
        herd_l_day=herd_total(herd, {"cow": 70}),
        herd_cow_equivalents=current,
    )

    assert load_status(current, limit, limit * 0.9) == expected


def test_load_status_at_the_computed_lower_boundary():
    assert load_status(0.09, 0.1, 0.1 * 0.9) == "within"


# Con 5.000 l/día y un límite por pasto de 100 EV, el agua fija el rodeo máximo.
# 72 EV a 70 L/EV: rodeo máximo de 71,4 EV, quedan por encima.
# 80 EV a 60 L/EV: rodeo máximo de 83,3 EV, quedan dentro (el piso es 75).
@pytest.mark.parametrize(
    ("current", "litres_per_ev", "expected"),
    [(72, 70, "above"), (80, 60, "within")],
)
def test_load_status_when_water_limits_the_herd(current, litres_per_ev, expected):
    limit = water_limit(
        available_l_day=5000,
        herd_l_day=current * litres_per_ev,
        herd_cow_equivalents=current,
    )
    maximum, _ = max_herd(100, limit)

    assert load_status(current, maximum, maximum * 0.9) == expected


def test_herd_of_steers_that_does_not_fit_the_water_is_above():
    # Sin vacas cuentan los litros de cada categoría cargada.
    # 100 novillos: 80 EV y 4.250 l/día. Con 3.000 l/día el límite por agua es
    # 3.000 × 80 / 4.250 = 56,47 EV.
    herd = {"steer": 100}
    current = herd_total(herd, EQUIVALENTS)
    limit = water_limit(
        available_l_day=3000,
        herd_l_day=herd_total(herd, SUMMER_LITRES),
        herd_cow_equivalents=current,
    )
    maximum, limited_by = max_herd(100, limit)

    assert maximum == pytest.approx(56.47, abs=0.01)
    assert limited_by == LimitedBy.WATER
    assert load_status(current, maximum, maximum * 0.9) == "above"


def scale(loaded, limit, *, replacement=0.2, weaning=0.75, fits=None):
    return scale_herd(
        loaded=loaded,
        limit_cow_equivalents=limit,
        replacement_rate=replacement,
        weaning_rate=weaning,
        parameters=PARAMETERS,
        cow_equivalents=EQUIVALENTS,
        fits=fits,
    )


def with_calves(herd, *, replacement=0.2, weaning=0.75):
    return herd_with_calves(
        herd,
        replacement_rate=replacement,
        weaning_rate=weaning,
        parameters=PARAMETERS,
    )


def test_herd_total():
    # 10 * 1 + 1 * 1,3 + 2 * 0,25 = 11,8
    total = herd_total({"cow": 10, "bull": 1, "calf": 2}, EQUIVALENTS)

    assert total == pytest.approx(11.8)


def test_calves_come_from_the_cows():
    # 95 * 0,2 = 19 terneras; destetados 95 * 0,75 = 71,25 -> 71,
    # hembras 71 * 0,5 = 35,5 -> 36. Entran las 19.
    assert with_calves({"cow": 95}) == {"cow": 95, "calf": 19}


def test_calves_are_capped_by_weaned_females():
    # Destete 30%: la reposición baja a 0,3 * 0,5 = 0,15.
    # 100 * 0,15 = 15; destetados 30, hembras 15.
    herd = with_calves({"cow": 100, "bull": 4}, weaning=0.3)

    assert herd == {"cow": 100, "bull": 4, "calf": 15}


def test_issue_example_shrinks_the_herd():
    # 51 vacas: toros 4 * 51 / 100 = 2,04 -> 2, terneras 10,2 -> 10;
    # 51 + 2,6 + 2,5 = 56,1 se pasa de 55,2.
    # 50 vacas: toros 2, terneras 10; 50 + 2,6 + 2,5 = 55,1.
    herd = scale({"cow": 100, "bull": 4}, 55.2)

    assert herd is not None
    assert herd.quantities == {"cow": 50, "bull": 2, "calf": 10}
    assert herd.cow_equivalents == pytest.approx(55.1)


def test_herd_grows_with_its_proportions():
    # 29 vacas: toros 2,9 -> 3, novillos 8,7 -> 9, terneras 5,8 -> 6;
    # 29 + 3,9 + 7,2 + 1,5 = 41,6 se pasa de 40.
    # 28 vacas: toros 2,8 -> 3, novillos 8,4 -> 8, terneras 5,6 -> 6
    # (destetados 16,8 -> 17, hembras 8,5 -> 9); 28 + 3,9 + 6,4 + 1,5 = 39,8.
    herd = scale({"cow": 10, "bull": 1, "steer": 3}, 40, weaning=0.6)

    assert herd is not None
    assert herd.quantities == {"cow": 28, "bull": 3, "steer": 8, "calf": 6}
    assert herd.cow_equivalents == pytest.approx(39.8)


def test_at_least_one_bull_if_bulls_were_loaded():
    # 10 vacas: toros 10 / 30 = 0,33 -> 0, sube a 1; 10 + 1,3 = 11,3 se pasa.
    # 9 vacas: 1 toro; 9 + 1,3 = 10,3.
    herd = scale({"cow": 30, "bull": 1}, 10.5, replacement=0)

    assert herd is not None
    assert herd.quantities == {"cow": 9, "bull": 1, "calf": 0}


def test_no_bull_if_none_were_loaded():
    herd = scale({"cow": 20, "bull": 0}, 7.5, replacement=0)

    assert herd is not None
    assert herd.quantities == {"cow": 7, "bull": 0, "calf": 0}


def test_no_herd_when_one_cow_with_her_share_does_not_fit():
    # 1 vaca lleva 2 toros: 1 + 2,6 = 3,6 se pasa de 2.
    assert scale({"cow": 1, "bull": 2}, 2, replacement=0) is None


@pytest.mark.parametrize("loaded", [{"bull": 3}, {"cow": 0, "bull": 3}])
def test_without_cows_the_herd_is_not_scaled(loaded):
    with pytest.raises(ValueError):
        scale(loaded, 100)


def test_extra_condition_lowers_cows():
    # Sin condición entran 95 vacas y 19 terneras: 99,75 EV.
    # Con 6.522 litros: 95 y 94 vacas piden 6.650 y 6.580 litros; 93 vacas
    # con 19 terneras piden 93 * 70 = 6.510 y entran.
    def fits(herd):
        return herd_total(herd, SUMMER_LITRES) <= 6522

    without_condition = scale({"cow": 95}, 100)
    herd = scale({"cow": 95}, 100, fits=fits)

    assert without_condition is not None
    assert without_condition.quantities == {"cow": 95, "calf": 19}
    assert herd is not None
    assert herd.quantities == {"cow": 93, "calf": 19}
    assert herd.cow_equivalents == pytest.approx(97.75)


@pytest.mark.parametrize("limit", [3, 7.7, 12.4, 55, 120.1, 333.3, 1000])
def test_scaled_herd_never_exceeds_the_limit(limit):
    herd = scale({"cow": 10, "bull": 1, "steer": 3}, limit, weaning=0.6)

    assert herd is not None
    assert herd.cow_equivalents <= limit
    assert herd.quantities["bull"] >= 1


def test_herd_that_fits_exactly_is_not_lost_to_rounding():
    # Vaca de 0,98 EV y 70 l/día, sin reposición, con 70 l/día disponibles.
    # El límite da 0,9799999999999999 en punto flotante: con floor la búsqueda
    # arrancaría en 0 vacas, y la vaca de 0,98 EV parecería pasarse del límite.
    equivalents = {"cow": 0.98, "calf": 0.25}
    limit = water_limit(
        available_l_day=70,
        herd_l_day=herd_total({"cow": 1, "calf": 0}, {"cow": 70, "calf": 0}),
        herd_cow_equivalents=herd_total({"cow": 1, "calf": 0}, equivalents),
    )

    herd = scale_herd(
        loaded={"cow": 1},
        limit_cow_equivalents=limit,
        replacement_rate=0,
        weaning_rate=0.75,
        parameters=PARAMETERS,
        cow_equivalents=equivalents,
    )

    # El caso existe solo si el redondeo deja el límite por debajo de 0,98
    assert limit < 0.98
    assert herd is not None
    assert herd.quantities == {"cow": 1, "calf": 0}
