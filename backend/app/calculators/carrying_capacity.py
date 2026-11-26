"""Receptividad según la lluvia, con el método de Guevara y otros (1995)."""

import math
from dataclasses import dataclass

from app.models.enums import CorrectionIndexCode, RangeCondition


class NotCalculableError(ValueError):
    """Faltan datos para calcular la receptividad."""


@dataclass(frozen=True)
class PastureParameters:
    """Valores de referencia del cálculo.

    Cada campo se llama igual que su clave en la tabla parameter. Los índices
    pueden faltar porque se cargan más adelante.
    """

    cow_equivalent_dm_intake_kg_year: float
    rain_use_efficiency_herbaceous: float
    rain_use_efficiency_woody: float
    accessible_fraction_herbaceous: float
    accessible_fraction_woody: float
    forage_use_factor: float
    range_condition_index_fair: float | None
    range_condition_index_good: float | None
    range_condition_index_very_good: float | None
    early_weaning_index: float | None
    supplementation_index: float | None


@dataclass(frozen=True)
class CorrectionIndex:
    """Un índice de corrección: si corresponde aplicarlo y su valor, si se cargó."""

    code: CorrectionIndexCode
    applies: bool
    value: float | None


@dataclass(frozen=True)
class PastureLimit:
    consumable_forage_kg_ha_year: float
    # Receptividad antes de corregir por los índices
    base_carrying_capacity_ha_per_cow_equivalent: float
    indices: list[CorrectionIndex]
    carrying_capacity_ha_per_cow_equivalent: float
    pasture_limit_cow_equivalents: float
    missing_index: bool


def consumable_forage_kg_ha_year(
    rainfall_mm: float, parameters: PastureParameters
) -> float:
    """Forraje que el rodeo puede consumir por hectárea en un año."""
    herbaceous = (
        rainfall_mm
        * parameters.rain_use_efficiency_herbaceous
        * parameters.accessible_fraction_herbaceous
    )
    woody = (
        rainfall_mm
        * parameters.rain_use_efficiency_woody
        * parameters.accessible_fraction_woody
    )
    return (herbaceous + woody) * parameters.forage_use_factor


def correction_indices(
    range_condition: RangeCondition,
    early_weaning: bool,
    supplemented: bool,
    parameters: PastureParameters,
) -> list[CorrectionIndex]:
    """Los tres índices. El del estado del campo siempre corresponde; los otros
    dos, solo si su casilla está marcada."""
    range_condition_indices = {
        RangeCondition.FAIR: parameters.range_condition_index_fair,
        RangeCondition.GOOD: parameters.range_condition_index_good,
        RangeCondition.VERY_GOOD: parameters.range_condition_index_very_good,
    }
    return [
        CorrectionIndex(
            CorrectionIndexCode.RANGE_CONDITION,
            True,
            range_condition_indices[range_condition],
        ),
        CorrectionIndex(
            CorrectionIndexCode.EARLY_WEANING,
            early_weaning,
            parameters.early_weaning_index,
        ),
        CorrectionIndex(
            CorrectionIndexCode.SUPPLEMENTATION,
            supplemented,
            parameters.supplementation_index,
        ),
    ]


def calculate_pasture_limit(
    *,
    rainfall_mm: float,
    usable_area_ha: float,
    range_condition: RangeCondition,
    early_weaning: bool,
    supplemented: bool,
    parameters: PastureParameters,
) -> PastureLimit:
    """Hectáreas por EV y límite por pasto.

    Un índice mayor que 1 indica que el campo soporta más animales, por eso la
    receptividad se divide por el producto de los índices. Un índice sin valor
    se omite y queda marcado en el resultado.
    """
    if rainfall_mm <= 0:
        raise NotCalculableError("La lluvia debe ser mayor que 0.")
    if usable_area_ha <= 0:
        raise NotCalculableError("El sector no tiene superficie aprovechable.")
    forage = consumable_forage_kg_ha_year(rainfall_mm, parameters)
    base = parameters.cow_equivalent_dm_intake_kg_year / forage
    indices = correction_indices(
        range_condition, early_weaning, supplemented, parameters
    )
    applied = [index for index in indices if index.applies]
    loaded = [index.value for index in applied if index.value is not None]
    carrying_capacity = base / math.prod(loaded)
    return PastureLimit(
        consumable_forage_kg_ha_year=forage,
        base_carrying_capacity_ha_per_cow_equivalent=base,
        indices=indices,
        carrying_capacity_ha_per_cow_equivalent=carrying_capacity,
        pasture_limit_cow_equivalents=usable_area_ha / carrying_capacity,
        missing_index=len(loaded) < len(applied),
    )
