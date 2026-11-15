from sqlalchemy import Select, select

from app.models import Parameter


def select_parameter(key: str) -> Select[float | None]:
    """Consulta del valor de un parámetro según su clave.

    Devuelve la consulta y no el valor, para usarla sola o como subconsulta
    dentro de otra consulta.
    """
    return select(Parameter.value).where(Parameter.key == key)
