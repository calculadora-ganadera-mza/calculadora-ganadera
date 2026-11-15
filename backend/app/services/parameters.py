from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Parameter


def select_parameter(key: str) -> Select[float | None]:
    """Consulta del valor de un parámetro según su clave.

    Devuelve la consulta y no el valor, para usarla sola o como subconsulta
    dentro de otra consulta.
    """
    return select(Parameter.value).where(Parameter.key == key)


def get_parameters(session: Session, keys: list[str]) -> dict[str, float | None]:
    """Valores de varios parámetros, leídos en una sola consulta.

    Falla si falta alguna clave, porque el cálculo no puede seguir sin ella.
    """
    rows = session.execute(
        select(Parameter.key, Parameter.value).where(Parameter.key.in_(keys))
    )
    values = {key: value for key, value in rows}
    missing = sorted(set(keys) - values.keys())
    if missing:
        raise LookupError("Faltan los parámetros: " + ", ".join(missing) + ".")
    return values
