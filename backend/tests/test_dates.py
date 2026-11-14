from datetime import UTC, date, datetime

from app.core.dates import local_date


def test_late_night_june_30_in_mendoza_is_still_june_30():
    # 1 de julio a la 1 en UTC = 30 de junio a las 22 en Mendoza
    moment = datetime(2027, 7, 1, 1, 0, tzinfo=UTC)

    assert local_date(moment) == date(2027, 6, 30)


def test_timezone_comes_from_settings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "app_timezone", "UTC")
    moment = datetime(2027, 7, 1, 1, 0, tzinfo=UTC)

    assert local_date(moment) == date(2027, 7, 1)
