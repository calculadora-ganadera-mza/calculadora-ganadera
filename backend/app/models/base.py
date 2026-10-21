from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, Identity, MetaData, func
from sqlalchemy.orm import DeclarativeBase, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

IntPk = Annotated[int, mapped_column(Identity(), primary_key=True)]
CreatedAt = Annotated[datetime, mapped_column(server_default=func.now())]
UpdatedAt = Annotated[
    datetime, mapped_column(server_default=func.now(), onupdate=func.now())
]


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: DateTime(timezone=True)}
