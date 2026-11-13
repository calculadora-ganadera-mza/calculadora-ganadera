from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    AnimalCategory,
    HerdCategory,
    HerdSeason,
    ProductionUnit,
    Scenario,
    Season,
)
from app.schemas.herd import HerdData, HerdRead

# Códigos fijos de las categorías que usan las reglas del rodeo
COW = "cow"
CALF = "calf"


class InvalidHerdError(ValueError):
    """Los datos del rodeo no cumplen una regla del contrato."""


class HerdExistsError(ValueError):
    """El sector ya tiene un rodeo en esa campaña."""


class UnitNotFoundError(LookupError):
    """El sector no existe o no es del establecimiento de la campaña."""


def check_herd_rules(data: HerdData, codes: dict[int, str]) -> None:
    """Revisa las reglas del rodeo; codes asocia cada categoría con su código."""
    ids = [item.animal_category_id for item in data.categories]
    if any(category_id not in codes for category_id in ids):
        raise InvalidHerdError("Alguna categoría de animal no existe.")
    if len(ids) != len(set(ids)):
        raise InvalidHerdError("Hay categorías de animales repetidas.")
    if any(codes[category_id] == CALF for category_id in ids):
        raise InvalidHerdError("Los terneros no se cargan: los calcula la aplicación.")

    if (data.breeding_start is None) != (data.breeding_end is None):
        raise InvalidHerdError("El entore se carga con inicio y fin, o sin ninguno.")
    if data.breeding_start and data.breeding_end <= data.breeding_start:
        raise InvalidHerdError("El fin del entore tiene que ser posterior al inicio.")

    has_cows = any(
        codes[item.animal_category_id] == COW and item.quantity > 0
        for item in data.categories
    )
    missing = (
        data.replacement_rate is None
        or data.weaning_rate is None
        or data.breeding_start is None
    )
    if has_cows and missing:
        raise InvalidHerdError(
            "Si hay vacas, hacen falta el porcentaje de reposición, "
            "el de destete y el período de entore."
        )


def category_codes(session: Session) -> dict[int, str]:
    return dict(session.execute(select(AnimalCategory.id, AnimalCategory.code)).all())


def list_animal_categories(session: Session) -> list[AnimalCategory]:
    return list(session.scalars(select(AnimalCategory).order_by(AnimalCategory.id)))


def get_user_herd(session: Session, user_id: int, herd_id: int) -> HerdSeason | None:
    """El rodeo, solo si es de un establecimiento del usuario."""
    return session.scalar(
        select(HerdSeason)
        .join(Scenario, HerdSeason.scenario_id == Scenario.id)
        .where(HerdSeason.id == herd_id, Scenario.user_id == user_id)
    )


def set_herd_data(session: Session, herd: HerdSeason, data: HerdData) -> None:
    """Copia los datos al rodeo y reemplaza sus categorías."""
    herd.range_condition = data.range_condition
    herd.replacement_rate = data.replacement_rate
    herd.weaning_rate = data.weaning_rate
    herd.early_weaning = data.early_weaning
    herd.supplemented = data.supplemented
    herd.breeding_start = data.breeding_start
    herd.breeding_end = data.breeding_end
    session.flush()
    session.execute(delete(HerdCategory).where(HerdCategory.herd_season_id == herd.id))
    session.add_all(
        HerdCategory(
            herd_season_id=herd.id,
            animal_category_id=item.animal_category_id,
            quantity=item.quantity,
        )
        for item in data.categories
    )
    session.flush()


def create_herd(
    session: Session, season: Season, production_unit_id: int, data: HerdData
) -> HerdSeason:
    """Registra el rodeo de un sector del mismo establecimiento que la campaña."""
    check_herd_rules(data, category_codes(session))
    unit = session.get(ProductionUnit, production_unit_id)
    if unit is None or unit.scenario_id != season.scenario_id:
        raise UnitNotFoundError("Sector no encontrado.")
    exists = session.scalar(
        select(HerdSeason.id).where(
            HerdSeason.season_id == season.id,
            HerdSeason.production_unit_id == production_unit_id,
        )
    )
    if exists:
        raise HerdExistsError("El sector ya tiene un rodeo en esa campaña.")

    herd = HerdSeason(
        scenario_id=season.scenario_id,
        season_id=season.id,
        production_unit_id=production_unit_id,
        range_condition=data.range_condition,
    )
    session.add(herd)
    session.flush()
    set_herd_data(session, herd, data)
    return herd


def update_herd(session: Session, herd: HerdSeason, data: HerdData) -> None:
    """Reemplaza los datos del rodeo."""
    check_herd_rules(data, category_codes(session))
    set_herd_data(session, herd, data)


def list_herds(session: Session, season_id: int) -> list[HerdSeason]:
    """Rodeos de la campaña, uno por sector que ya tiene datos."""
    return list(
        session.scalars(
            select(HerdSeason)
            .where(HerdSeason.season_id == season_id)
            .order_by(HerdSeason.id)
        )
    )


def herd_read(session: Session, herd: HerdSeason) -> HerdRead:
    """El rodeo en el formato de la API, con sus categorías."""
    categories = session.execute(
        select(HerdCategory.animal_category_id, HerdCategory.quantity)
        .where(HerdCategory.herd_season_id == herd.id)
        .order_by(HerdCategory.animal_category_id)
    ).mappings()
    return HerdRead(
        id=herd.id,
        season_id=herd.season_id,
        production_unit_id=herd.production_unit_id,
        categories=[dict(row) for row in categories],
        range_condition=herd.range_condition,
        replacement_rate=herd.replacement_rate,
        weaning_rate=herd.weaning_rate,
        early_weaning=herd.early_weaning,
        supplemented=herd.supplemented,
        breeding_start=herd.breeding_start,
        breeding_end=herd.breeding_end,
    )
