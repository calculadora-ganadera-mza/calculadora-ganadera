"""Da el rol de administrador a un usuario ya registrado.

Uso: docker compose run --rm backend python -m app.commands.make_admin <correo>
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import User
from app.models.enums import Role


def make_admin(session: Session, email: str) -> User:
    """Le da el rol de administrador al usuario con ese correo."""
    user = session.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise LookupError(f"No hay ningún usuario registrado con el correo {email}.")
    user.role = Role.ADMIN
    session.flush()
    return user


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Uso: python -m app.commands.make_admin <correo>", file=sys.stderr)
        return 2
    with SessionLocal() as session:
        try:
            user = make_admin(session, argv[0])
        except LookupError as err:
            print(err, file=sys.stderr)
            return 1
        session.commit()
        print(f"{user.email} ahora es administrador.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
