from pydantic import BaseModel

from app.schemas.carrying_capacity import HerdQuantity


class HistoryEntry(BaseModel):
    """Datos de un sector en una campaña, para el gráfico de evolución."""

    season_id: int
    start_year: int
    categories: list[HerdQuantity]
    replacement_rate: float | None
    weaning_rate: float | None
    # Lluvia de la campaña anterior, de julio a junio, en mm
    rainfall_mm: float | None
