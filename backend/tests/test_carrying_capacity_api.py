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


# Rodeo recomendado (#15). El sector de prueba tiene unas 101,8 ha y, con
# 300 mm, 15,08 ha/EV: el límite por pasto es de unos 6,75 EV.


def herd_with_cows(session, **changes) -> dict:
    cow = session.scalars(
        select(AnimalCategory.id).where(AnimalCategory.code == "cow")
    ).one()
    data = {
        "categories": [{"animal_category_id": cow, "quantity": 10}],
        "replacement_rate": 0.2,
        "weaning_rate": 0.5,
        "breeding_start": "2026-11-01",
        "breeding_end": "2027-01-31",
    }
    return data | changes


def test_recommended_herd_fits_in_the_pasture_limit(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id, **herd_with_cows(session)).json()

    # 5 vacas con su toro, ternera y vaquillona suman 7,25 EV: se pasa.
    # 4 vacas + 1 toro + 1 ternera + 1 vaquillona = 4 + 1,3 + 0,25 + 0,7 = 6,25.
    herd = result["recommended_herd"]
    assert [c["quantity"] for c in herd["categories"]] == [4, 1, 1, 1]
    assert herd["cow_equivalents"] == pytest.approx(6.25)
    assert herd["cow_equivalents"] <= result["pasture_limit_cow_equivalents"]
    assert herd["weaned_calves"] == {"males": 1, "females": 1}


def test_without_cows_there_is_no_recommended_herd(api, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id).json()

    assert result["recommended_herd"] is None
    assert [w["code"] for w in result["warnings"]] == ["missing_index"]


def test_bulls_per_100_cows_from_the_request(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(
        api, unit_id, **herd_with_cows(session), bulls_per_100_cows=50
    ).json()

    # 3 vacas con 50 toros cada 100: round(1,5) = 2 toros.
    assert [c["quantity"] for c in result["recommended_herd"]["categories"]][:2] == [
        3,
        2,
    ]


def test_replacement_above_weaned_females_warns(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id, **herd_with_cows(session, weaning_rate=0.3)).json()

    codes = [w["code"] for w in result["warnings"]]
    assert "replacement_exceeds_females" in codes
    assert result["recommended_herd"] is not None


def test_field_too_small_for_a_cow_and_her_bull(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id, **herd_with_cows(session), rainfall_mm=1).json()

    assert result["recommended_herd"] is None
    assert "herd_does_not_fit" in [w["code"] for w in result["warnings"]]
    assert result["pasture_limit_cow_equivalents"] > 0
