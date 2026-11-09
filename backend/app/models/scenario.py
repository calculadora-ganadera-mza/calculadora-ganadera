from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import ForeignKey, Index, false, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk


class Scenario(Base):
    __tablename__ = "scenario"
    __table_args__ = (
        # Un solo establecimiento principal por usuario
        Index(
            "uq_scenario_main_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_main"),
        ),
    )

    id: Mapped[IntPk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str]
    is_main: Mapped[bool] = mapped_column(server_default=false())
    location: Mapped[WKBElement | None] = mapped_column(Geometry("POINT", srid=4326))
    created_at: Mapped[CreatedAt]
