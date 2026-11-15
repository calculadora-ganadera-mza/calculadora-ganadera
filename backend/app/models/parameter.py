from sqlalchemy import CheckConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IntPk


class Parameter(Base):
    __tablename__ = "parameter"
    # Todo valor cargado es mayor que 0. Solo los índices pueden quedar sin
    # valor, hasta que el administrador los cargue. El IS NOT NULL hace falta
    # porque un CHECK que da NULL no rechaza la fila.
    __table_args__ = (
        CheckConstraint(
            "(value IS NOT NULL AND value > 0) OR (value IS NULL AND key IN ("
            "'range_condition_index_fair', 'range_condition_index_good', "
            "'range_condition_index_very_good', 'early_weaning_index', "
            "'supplementation_index'))",
            name="value_positive",
        ),
    )

    id: Mapped[IntPk]
    key: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    value: Mapped[float | None]
    unit: Mapped[str]
    producer_editable: Mapped[bool] = mapped_column(server_default=false())
