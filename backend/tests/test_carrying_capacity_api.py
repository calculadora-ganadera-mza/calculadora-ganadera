import pytest
from sqlalchemy import delete, select, update

from app.models import AnimalCategory, Parameter, ProductionUnit, Scenario
from app.models.enums import ProductionSystem
from app.services.carrying_capacity import read_pasture_parameters

# Cuadrado de unos 100 ha en Mendoza
POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-68.09, -34.58],
            [-68.08, -34.58],
            [-68.08, -34.57],
            [-68.09, -34.57],
            [-68.09, -34.58],
        ]
    ],
}
# Con el alcance del seed, una aguada en el centro cubre todo el cuadrado.
CENTER = {"type": "Point", "coordinates": [-68.085, -34.575]}


@pytest.fixture
def unit_id(api, session, user) -> int:
    scenario = Scenario(user_id=user.id, name="Campo", is_main=True)
    session.add(scenario)
    session.flush()
    response = api.post(
        f"/scenarios/{scenario.id}/production-units",
        json={"name": "Sector", "polygon": POLYGON},
    )
    assert response.status_code == 201
    return response.json()["id"]


def add_water_point(api, unit_id: int) -> None:
    response = api.post(
        f"/production-units/{unit_id}/water-points",
        json={"name": "Tanque", "location": CENTER},
    )
    assert response.status_code == 201


def calculate(api, unit_id: int, **changes):
    data = {"categories": [], "range_condition": "good", "rainfall_mm": 300}
    return api.post(
        f"/production-units/{unit_id}/carrying-capacity", json=data | changes
    )


def test_without_indices_calculates_and_warns(api, unit_id):
    add_water_point(api, unit_id)

    response = calculate(api, unit_id)

    assert response.status_code == 200
    result = response.json()
    assert round(result["carrying_capacity_ha_per_cow_equivalent"], 1) == 15.1
    assert result["usable_area_ha"] == pytest.approx(result["area_ha"], rel=0.001)
    assert result["pasture_limit_cow_equivalents"] == pytest.approx(
        result["usable_area_ha"] / result["carrying_capacity_ha_per_cow_equivalent"]
    )
    assert [warning["code"] for warning in result["warnings"]] == ["missing_index"]


def test_uses_the_loaded_index(api, session, unit_id):
    add_water_point(api, unit_id)
    session.execute(
        update(Parameter)
        .where(Parameter.key == "range_condition_index_good")
        .values(value=1.5)
    )

    result = calculate(api, unit_id).json()

    # 15,08 ÷ 1,5 = 10,06 ha/EV
    assert result["carrying_capacity_ha_per_cow_equivalent"] == pytest.approx(
        10.06, abs=0.01
    )
    assert result["warnings"] == []


def test_sector_without_usable_area_is_not_calculated(api, unit_id):
    response = calculate(api, unit_id)

    assert response.status_code == 422
    assert response.json()["detail"] == "El sector no tiene superficie aprovechable."


@pytest.mark.parametrize("rainfall", [0, -10, None])
def test_rainfall_is_required_and_greater_than_zero(api, unit_id, rainfall):
    add_water_point(api, unit_id)

    assert calculate(api, unit_id, rainfall_mm=rainfall).status_code == 422


def test_herd_rules_are_checked(api, session, unit_id):
    add_water_point(api, unit_id)
    calf = session.scalars(
        select(AnimalCategory.id).where(AnimalCategory.code == "calf")
    ).one()

    response = calculate(
        api, unit_id, categories=[{"animal_category_id": calf, "quantity": 10}]
    )

    assert response.status_code == 422


def test_sector_of_another_user_is_not_found(api, session, other_user):
    scenario = Scenario(user_id=other_user.id, name="Ajeno", is_main=True)
    session.add(scenario)
    session.flush()
    unit = ProductionUnit(
        scenario_id=scenario.id,
        name="Ajeno",
        production_system=ProductionSystem.RAINFED,
        polygon="SRID=4326;POLYGON((-68.09 -34.58,-68.08 -34.58,-68.08 -34.57,"
        "-68.09 -34.57,-68.09 -34.58))",
    )
    session.add(unit)
    session.flush()

    assert calculate(api, unit.id).status_code == 404


def test_missing_reference_parameter_fails(session):
    session.execute(
        delete(Parameter).where(Parameter.key == "cow_equivalent_dm_intake_kg_year")
    )

    with pytest.raises(LookupError, match="cow_equivalent_dm_intake_kg_year"):
        read_pasture_parameters(session)
