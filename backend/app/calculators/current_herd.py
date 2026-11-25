"""Rodeo actual: terneras de reposición, termómetro y Mi rodeo ajustado al campo.

Los rodeos son cabezas por código de categoría.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.calculators.max_breeding_herd import (
    HerdParameters,
    exceeds_limit,
    replacement_calves,
    replacement_rate_for_calculation,
    round_half_up,
    weaned_calves,
)
from app.models.enums import LoadStatus

# Códigos fijos de las categorías con reglas propias
COW = "cow"
BULL = "bull"
CALF = "calf"


def load_status(
    current_cow_equivalents: float,
    max_cow_equivalents: float,
    below_cow_equivalents: float,
) -> LoadStatus:
    """Ubica la carga en EV con la tolerancia de punto flotante del ajuste."""
    if exceeds_limit(current_cow_equivalents, max_cow_equivalents):
        return LoadStatus.ABOVE
    if exceeds_limit(below_cow_equivalents, current_cow_equivalents):
        return LoadStatus.BELOW
    return LoadStatus.WITHIN


@dataclass(frozen=True)
class ScaledHerd:
    """Mi rodeo ajustado al campo: cabezas por código de categoría y sus EV."""

    quantities: dict[str, int]
    cow_equivalents: float


def herd_total(herd: Mapping[str, int], per_head: Mapping[str, float]) -> float:
    """Suma de las cabezas por el valor por cabeza de su categoría.

    Sirve para los EV y para los litros por día.
    """
    return sum(quantity * per_head[code] for code, quantity in herd.items())


def herd_with_calves(
    herd: Mapping[str, int],
    *,
    replacement_rate: float,
    weaning_rate: float,
    parameters: HerdParameters,
) -> dict[str, int]:
    """El rodeo con las terneras de reposición que salen de sus vacas."""
    female_share = parameters.weaned_calf_female_share
    rate, _ = replacement_rate_for_calculation(
        replacement_rate, weaning_rate, female_share
    )
    cows = herd.get(COW, 0)
    _, weaned_females = weaned_calves(cows, weaning_rate, female_share)
    return {**herd, CALF: replacement_calves(cows, rate, weaned_females)}


def scale_herd(
    *,
    loaded: Mapping[str, int],
    limit_cow_equivalents: float,
    replacement_rate: float,
    weaning_rate: float,
    parameters: HerdParameters,
    cow_equivalents: Mapping[str, float],
    fits: Callable[[Mapping[str, int]], bool] | None = None,
) -> ScaledHerd | None:
    """Mi rodeo ajustado al campo: el rodeo cargado escalado hasta el límite.

    Parte de las vacas que llenan el límite solas, redondeando hacia arriba para
    que el error de punto flotante no deje afuera la última vaca.
    Las demás categorías cargadas se escalan en la misma proporción que las
    vacas, redondeando al entero más cercano, con al menos un toro si se
    cargaron toros. Las terneras de reposición salen de las vacas. Si el rodeo
    se pasa del límite o no cumple fits (por ejemplo, los litros de verano),
    baja una vaca por vez. Devuelve None si no entra ni una vaca con su parte
    de los demás animales.
    """
    loaded_cows = loaded.get(COW, 0)
    if loaded_cows <= 0:
        raise ValueError("Sin vacas no se ajusta el rodeo.")

    cows = math.ceil(limit_cow_equivalents / cow_equivalents[COW])
    while cows >= 1:
        # Producto entero antes de dividir: los casos de media cabeza
        # redondean exacto
        herd = {
            code: round_half_up(quantity * cows / loaded_cows)
            for code, quantity in loaded.items()
        }
        if loaded.get(BULL, 0) > 0:
            herd[BULL] = max(1, herd[BULL])
        herd = herd_with_calves(
            herd,
            replacement_rate=replacement_rate,
            weaning_rate=weaning_rate,
            parameters=parameters,
        )
        total = herd_total(herd, cow_equivalents)
        if not exceeds_limit(total, limit_cow_equivalents) and (
            fits is None or fits(herd)
        ):
            return ScaledHerd(quantities=herd, cow_equivalents=total)
        cows -= 1
    return None
