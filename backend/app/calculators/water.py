"""Límite por agua: calendario de la recría, litros por día y rodeo máximo."""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Annotated

from pydantic import Field

from app.calculators.recommended_herd import (
    MONTHS_PER_YEAR,
    HerdParameters,
    RecommendedHerd,
)
from app.models.enums import LimitedBy

# Mes del año, de 1 (enero) a 12 (diciembre)
Month = Annotated[int, Field(ge=1, le=MONTHS_PER_YEAR)]


@dataclass(frozen=True)
class WaterParameters:
    """Valores de referencia del agua.

    Cada campo se llama igual que su clave en la tabla parameter.
    """

    gestation_days: int
    summer_start_month: Month
    summer_end_month: Month


@dataclass(frozen=True)
class CategoryWater:
    """Litros por día de cada categoría en una estación."""

    cow: float
    bull: float
    calf: float
    heifer: float


@dataclass(frozen=True)
class HerdCalendar:
    """Meses del año en que hay terneras de reposición y vaquillonas en el campo."""

    calf_months: frozenset[int]
    heifer_months: frozenset[int]


def shift_month(month: int, months: int) -> int:
    """Mes que cae months meses después de month, dando la vuelta al año."""
    return (month - 1 + months) % MONTHS_PER_YEAR + 1


def months_between(first: int, last: int) -> frozenset[int]:
    """Meses de first a last, ambos incluidos. Si last < first, cruza el fin de año."""
    count = (last - first) % MONTHS_PER_YEAR + 1
    return frozenset(shift_month(first, k) for k in range(count))


def stage_months(calving: date, start_age: int, end_age: int) -> frozenset[int]:
    """Meses del año en que hay animales de start_age a end_age meses de vida.

    El calendario se repite todos los años. El animal sale de la etapa el día
    que cumple end_age meses: si nació un día 1, ese mes ya no cuenta.
    """

    if end_age - start_age >= MONTHS_PER_YEAR:
        return frozenset(range(1, MONTHS_PER_YEAR + 1))
    last_age = end_age if calving.day > 1 else end_age - 1
    return months_between(
        shift_month(calving.month, start_age), shift_month(calving.month, last_age)
    )


def herd_calendar(
    breeding_start: date,
    early_weaning: bool,
    parameters: HerdParameters,
    water: WaterParameters,
) -> HerdCalendar:
    """Ubica en el año a las terneras de reposición y a las vaquillonas.

    El parto llega gestation_days después del inicio del entore. Las terneras
    están en el campo desde el destete hasta el año, y las vaquillonas desde el
    año hasta el primer entore.
    """
    calving = breeding_start + timedelta(days=water.gestation_days)
    weaning_age = (
        parameters.early_weaning_age_months
        if early_weaning
        else parameters.normal_weaning_age_months
    )
    return HerdCalendar(
        calf_months=stage_months(calving, weaning_age, MONTHS_PER_YEAR),
        heifer_months=stage_months(
            calving, MONTHS_PER_YEAR, parameters.heifer_first_breeding_age_months
        ),
    )


def season_litres(
    litres: CategoryWater, calendar: HerdCalendar, season: frozenset[int]
) -> CategoryWater:
    """Litros por cabeza en la estación.

    Las terneras y las vaquillonas cuentan solo si están en el campo en algún
    mes de la estación; si no, valen 0.
    """
    return replace(
        litres,
        calf=litres.calf if calendar.calf_months & season else 0,
        heifer=litres.heifer if calendar.heifer_months & season else 0,
    )


def litres_per_cow(
    litres: CategoryWater, rate: float, parameters: HerdParameters
) -> float:
    """Litros por día de una vaca con su parte de toros, terneras y vaquillonas."""
    return (
        litres.cow
        + parameters.bulls_per_cow * litres.bull
        + rate * (litres.calf + litres.heifer)
    )


def herd_litres(herd: RecommendedHerd, litres: CategoryWater) -> float:
    """Litros por día que necesita un rodeo en cantidades enteras."""
    return (
        herd.cows * litres.cow
        + herd.bulls * litres.bull
        + herd.replacement_calves * litres.calf
        + herd.heifers * litres.heifer
    )


def water_limit(
    *,
    available_l_day: float,
    composition_l_day: float,
    composition_cow_equivalents: float,
) -> float:
    """Límite por agua en EV: litros disponibles dividido por
    los litros por EV en verano."""
    return available_l_day * composition_cow_equivalents / composition_l_day


def max_herd(
    pasture_limit: float, water_limit: float | None
) -> tuple[float, LimitedBy]:
    """Rodeo máximo en EV y qué lo limita. Sin límite por agua, lo fija el pasto."""
    if water_limit is not None and water_limit < pasture_limit:
        return water_limit, LimitedBy.WATER
    return pasture_limit, LimitedBy.PASTURE
