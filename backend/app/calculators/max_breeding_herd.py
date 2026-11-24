"""Rodeo de cría máximo: cuántos animales de cada categoría entran en el límite."""

import math
from collections.abc import Callable
from dataclasses import dataclass

# Las terneras cuentan desde el destete hasta el año y las vaquillonas desde el
# año hasta el primer entore. Un año tiene 12 meses: no es un valor de referencia.
MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class HerdParameters:
    """Valores de referencia del rodeo.

    Cada campo se llama igual que su clave en la tabla parameter, salvo
    bulls_per_100_cows, que puede venir del pedido para simular.
    """

    bulls_per_100_cows: float
    weaned_calf_female_share: float
    # Meses enteros: el calendario del agua cuenta meses del año
    normal_weaning_age_months: int
    early_weaning_age_months: int
    heifer_first_breeding_age_months: int

    @property
    def bulls_per_cow(self) -> float:
        return self.bulls_per_100_cows / 100


@dataclass(frozen=True)
class CategoryEquivalents:
    """EV de cada categoría, según la tabla animal_category."""

    cow: float
    bull: float
    calf: float
    heifer: float


@dataclass(frozen=True)
class MaxBreedingHerd:
    """Rodeo de cría máximo en cabezas enteras, con sus EV y sus destetados."""

    cows: int
    bulls: int
    replacement_calves: int
    heifers: int
    cow_equivalents: float
    weaned_males: int
    weaned_females: int


def round_half_up(value: float) -> int:
    """Redondea al entero más cercano; 2,5 pasa a 3 (round de Python daría 2)."""
    return math.floor(value + 0.5)


def exceeds_limit(cow_equivalents: float, limit: float) -> bool:
    """Si los EV superan el límite, sin contar el error de redondeo de punto flotante.

    Un rodeo que entra justo en el límite por agua puede sumar 11,3 EV contra un
    límite de 11,299999999999999.
    """
    return cow_equivalents > limit and not math.isclose(cow_equivalents, limit)


def replacement_rate_for_calculation(
    replacement_rate: float, weaning_rate: float, female_share: float
) -> tuple[float, bool]:
    """Reposición que se puede cubrir y si la pedida supera las hembras destetadas.

    No se cuentan más terneras de reposición que hembras destetadas.
    """
    females_per_cow = weaning_rate * female_share
    return min(replacement_rate, females_per_cow), replacement_rate > females_per_cow


def weaned_calves(
    cows: int, weaning_rate: float, female_share: float
) -> tuple[int, int]:
    """Terneros destetados de cows vacas y cuántas son hembras, en enteros."""
    weaned = round_half_up(cows * weaning_rate)
    return weaned, round_half_up(weaned * female_share)


def replacement_calves(cows: int, rate: float, weaned_females: int) -> int:
    """Terneras de reposición de cows vacas, sin superar las hembras destetadas.

    rate es la reposición que devuelve replacement_rate_for_calculation.
    """
    return min(round_half_up(cows * rate), weaned_females)


def annual_equivalents(
    early_weaning: bool, parameters: HerdParameters, equivalents: CategoryEquivalents
) -> tuple[float, float]:
    """EV anual de una ternera de reposición y de una vaquillona de recría.

    Cada una vale su EV por los meses que pasa en la etapa, sobre 12.
    """
    weaning_age = (
        parameters.early_weaning_age_months
        if early_weaning
        else parameters.normal_weaning_age_months
    )
    calf_months = MONTHS_PER_YEAR - weaning_age
    heifer_months = parameters.heifer_first_breeding_age_months - MONTHS_PER_YEAR
    return (
        equivalents.calf * calf_months / MONTHS_PER_YEAR,
        equivalents.heifer * heifer_months / MONTHS_PER_YEAR,
    )


def cow_equivalents_per_cow(
    rate: float,
    early_weaning: bool,
    parameters: HerdParameters,
    equivalents: CategoryEquivalents,
) -> float:
    """EV que suma cada vaca con su parte de toros, terneras y vaquillonas."""
    calf_ev, heifer_ev = annual_equivalents(early_weaning, parameters, equivalents)
    return (
        equivalents.cow
        + parameters.bulls_per_cow * equivalents.bull
        + rate * (calf_ev + heifer_ev)
    )


def calculate_max_breeding_herd(
    *,
    limit_cow_equivalents: float,
    replacement_rate: float,
    weaning_rate: float,
    early_weaning: bool,
    parameters: HerdParameters,
    equivalents: CategoryEquivalents,
    fits: Callable[[MaxBreedingHerd], bool] | None = None,
) -> MaxBreedingHerd | None:
    """Rodeo de cría máximo: el rodeo en cantidades enteras que no supera el límite.

    Reparte el límite según la composición de una vaca con sus toros, terneras
    y vaquillonas. Si al redondear se pasa del límite o no cumple fits (por
    ejemplo, los litros de verano), baja una vaca por vez. Devuelve None si no
    entra ni una vaca con su toro.
    """
    rate, _ = replacement_rate_for_calculation(
        replacement_rate, weaning_rate, parameters.weaned_calf_female_share
    )
    calf_ev, heifer_ev = annual_equivalents(early_weaning, parameters, equivalents)
    per_cow = cow_equivalents_per_cow(rate, early_weaning, parameters, equivalents)

    cows = round_half_up(limit_cow_equivalents / per_cow)
    while cows >= 1:
        weaned, weaned_females = weaned_calves(
            cows, weaning_rate, parameters.weaned_calf_female_share
        )
        bulls = max(1, round_half_up(cows * parameters.bulls_per_cow))
        replacement = replacement_calves(cows, rate, weaned_females)
        herd = MaxBreedingHerd(
            cows=cows,
            bulls=bulls,
            replacement_calves=replacement,
            heifers=replacement,
            cow_equivalents=(
                cows * equivalents.cow
                + bulls * equivalents.bull
                + replacement * (calf_ev + heifer_ev)
            ),
            weaned_males=weaned - weaned_females,
            weaned_females=weaned_females,
        )
        if not exceeds_limit(herd.cow_equivalents, limit_cow_equivalents) and (
            fits is None or fits(herd)
        ):
            return herd
        cows -= 1
    return None
