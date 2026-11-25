from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnimalCategory, HerdCategory, HerdSeason, ProductionUnit
from app.schemas.carrying_capacity import HerdQuantity
from app.schemas.history import HistoryEntry
from app.services.scenarios import list_seasons


def unit_history(session: Session, unit: ProductionUnit) -> list[HistoryEntry]:
    """Una entrada por campaña del establecimiento, ordenadas por año.

    Si el sector no tiene rodeo en una campaña, no tiene categorías y los
    porcentajes quedan en None.
    """
    herds = {
        herd.season_id: herd
        for herd in session.scalars(
            select(HerdSeason).where(HerdSeason.production_unit_id == unit.id)
        )
    }
    rows = session.execute(
        select(
            HerdCategory.herd_season_id,
            AnimalCategory.id,
            AnimalCategory.name,
            HerdCategory.quantity,
        )
        .join(AnimalCategory)
        .where(HerdCategory.herd_season_id.in_([herd.id for herd in herds.values()]))
        .order_by(AnimalCategory.id)
    )
    categories: dict[int, list[HerdQuantity]] = {}
    for herd_id, category_id, name, quantity in rows:
        categories.setdefault(herd_id, []).append(
            HerdQuantity(animal_category_id=category_id, name=name, quantity=quantity)
        )

    entries = []
    for season in list_seasons(session, unit.scenario_id):
        herd = herds.get(season.id)
        entries.append(
            HistoryEntry(
                season_id=season.id,
                start_year=season.start_date.year,
                categories=categories.get(herd.id, []) if herd else [],
                replacement_rate=herd.replacement_rate if herd else None,
                weaning_rate=herd.weaning_rate if herd else None,
                rainfall_mm=season.rainfall_mm,
            )
        )
    return entries
