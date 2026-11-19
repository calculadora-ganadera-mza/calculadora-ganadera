import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.commands.make_admin import main, make_admin
from app.core.config import settings
from app.core.db import get_session
from app.core.jwt import create_access_token
from app.main import app
from app.models import AnimalCategory, Parameter, User
from app.models.enums import Role
from app.services.carrying_capacity import read_pasture_parameters


@pytest.fixture
def admin(session: Session) -> User:
    admin = User(
        name="Admin", email="admin@example.com", password_hash="x", role=Role.ADMIN
    )
    session.add(admin)
    session.flush()
    return admin


@pytest.fixture
def admin_api(monkeypatch, session: Session, admin: User):
    """Cliente de la API con un administrador que inició sesión."""
    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-" * 5)
    app.dependency_overrides[get_session] = lambda: session
    token = create_access_token({"sub": str(admin.id)})
    try:
        yield TestClient(app, headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()


def category_id(session: Session, code: str) -> int:
    return session.scalars(
        select(AnimalCategory.id).where(AnimalCategory.code == code)
    ).one()


# Comando para el primer administrador


def test_make_admin_gives_the_role(session: Session, user: User):
    make_admin(session, " PRUEBA@example.com ")

    assert user.role == Role.ADMIN


def test_make_admin_with_unknown_email_fails(session: Session):
    with pytest.raises(LookupError, match="No hay ningún usuario"):
        make_admin(session, "nadie@example.com")


def test_make_admin_command_needs_one_email():
    assert main([]) == 2


# Lectura: cualquier usuario con sesión


def test_any_user_reads_parameters_sorted_by_key(api: TestClient):
    response = api.get("/parameters")

    assert response.status_code == 200
    keys = [p["key"] for p in response.json()]
    assert keys == sorted(keys)
    assert "early_weaning_index" in keys


def test_any_user_reads_categories(api: TestClient):
    response = api.get("/animal-categories")

    assert response.status_code == 200
    assert {"cow", "bull", "calf"} <= {c["code"] for c in response.json()}


# Edición: solo el administrador


def test_admin_changes_a_parameter(admin_api: TestClient, session: Session):
    response = admin_api.patch("/parameters/water_point_radius_km", json={"value": 3})

    assert response.status_code == 200
    assert response.json()["value"] == 3
    stored = session.scalar(
        select(Parameter.value).where(Parameter.key == "water_point_radius_km")
    )
    assert stored == 3


def test_admin_loads_and_clears_an_index(admin_api: TestClient):
    loaded = admin_api.patch("/parameters/early_weaning_index", json={"value": 1.1})
    cleared = admin_api.patch("/parameters/early_weaning_index", json={"value": None})

    assert loaded.json()["value"] == 1.1
    assert cleared.status_code == 200
    assert cleared.json()["value"] is None


def test_only_indices_can_be_left_without_value(admin_api: TestClient):
    response = admin_api.patch(
        "/parameters/cow_equivalent_dm_intake_kg_year", json={"value": None}
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Solo los índices pueden quedar sin valor."}


@pytest.mark.parametrize("value", [0, -1])
def test_parameter_value_must_be_positive(admin_api: TestClient, value: float):
    response = admin_api.patch("/parameters/early_weaning_index", json={"value": value})

    assert response.status_code == 422


def test_unknown_parameter_is_not_found(admin_api: TestClient):
    response = admin_api.patch("/parameters/no_existe", json={"value": 1})

    assert response.status_code == 404


def test_the_next_calculation_uses_the_new_value(
    admin_api: TestClient, session: Session
):
    admin_api.patch("/parameters/range_condition_index_good", json={"value": 1.5})

    assert read_pasture_parameters(session).range_condition_index_good == 1.5


def test_admin_changes_a_category(admin_api: TestClient, session: Session):
    cow = category_id(session, "cow")

    response = admin_api.patch(
        f"/animal-categories/{cow}", json={"name": " Vaca ", "summer_water_l_day": 72}
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["code"], body["summer_water_l_day"]) == (
        "Vaca",
        "cow",
        72,
    )


def test_repeated_category_name_is_a_conflict(admin_api: TestClient, session: Session):
    cow = category_id(session, "cow")

    response = admin_api.patch(f"/animal-categories/{cow}", json={"name": "Toro"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Ya existe una categoría con ese nombre."}


@pytest.mark.parametrize(
    "data", [{}, {"cow_equivalent": 0}, {"name": "   "}, {"cow_equivalent": None}]
)
def test_invalid_category_changes_are_rejected(
    admin_api: TestClient, session: Session, data: dict
):
    cow = category_id(session, "cow")

    response = admin_api.patch(f"/animal-categories/{cow}", json=data)

    assert response.status_code == 422


def test_unknown_category_is_not_found(admin_api: TestClient):
    assert (
        admin_api.patch("/animal-categories/999999", json={"name": "X"}).status_code
        == 404
    )


@pytest.mark.parametrize(
    "path, data",
    [
        ("/parameters/water_point_radius_km", {"value": 3}),
        ("/animal-categories/1", {"name": "Otra"}),
    ],
)
def test_a_producer_cannot_edit(api: TestClient, path: str, data: dict):
    response = api.patch(path, json=data)

    assert response.status_code == 403
    assert response.json() == {"detail": "Acción reservada a administradores."}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/parameters"),
        ("patch", "/parameters/water_point_radius_km"),
        ("patch", "/animal-categories/1"),
    ],
)
def test_routes_require_login(method: str, path: str):
    response = TestClient(app).request(method, path, json={"value": 1})

    assert response.status_code == 401
