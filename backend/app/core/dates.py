from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def local_date(moment: datetime) -> date:
    """Día que corresponde a moment en la zona horaria de la app."""
    return moment.astimezone(ZoneInfo(settings.app_timezone)).date()


def today() -> date:
    """Fecha de hoy en la zona horaria de la app, no en la del servidor."""
    return local_date(datetime.now(UTC))
