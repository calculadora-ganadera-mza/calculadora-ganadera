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


def add_water_point(api, unit_id: int, **changes) -> None:
    data = {"name": "Tanque", "location": CENTER}
    response = api.post(
        f"/production-units/{unit_id}/water-points", json=data | changes
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
    codes = [warning["code"] for warning in result["warnings"]]
    assert codes == ["missing_index", "water_not_evaluated"]


def test_simulation_uses_the_supplied_rainfall(api, unit_id):
    add_water_point(api, unit_id)
    data = {"categories": [], "range_condition": "good", "rainfall_mm": 600}

    response = api.post(
        f"/production-units/{unit_id}/carrying-capacity/simulate", json=data
    )

    assert response.status_code == 200
    result = response.json()
    assert result == calculate(api, unit_id, rainfall_mm=600).json()
    assert result["carrying_capacity_ha_per_cow_equivalent"] == pytest.approx(
        calculate(api, unit_id).json()["carrying_capacity_ha_per_cow_equivalent"] / 2
    )


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
    assert [w["code"] for w in result["warnings"]] == ["water_not_evaluated"]


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
    add_water_point(api, unit_id, refill_l_day=300)

    result = calculate(api, unit_id).json()

    assert result["recommended_herd"] is None
    assert result["water"]["evaluated"] is False
    assert result["water"]["limit_cow_equivalents"] is None
    assert result["water"]["refill_l_day"] == pytest.approx(300)
    assert result["max_herd"] == {
        "cow_equivalents": pytest.approx(result["pasture_limit_cow_equivalents"]),
        "limited_by": "pasture",
        "categories": [],
    }
    codes = [w["code"] for w in result["warnings"]]
    assert codes == ["missing_index", "water_not_evaluated"]


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


# Límite por agua (#14). Con herd_with_cows (reposición 0,2, entore el 1/11)
# las terneras están en el campo de febrero a agosto: cuentan en verano.
# Cada vaca suma 1,2485 EV y pide 70 + 0,045 × 65 + 0,2 × (25 + 42,5) =
# 86,425 l/día.
EAST_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-68.08, -34.58],
            [-68.07, -34.58],
            [-68.07, -34.57],
            [-68.08, -34.57],
            [-68.08, -34.58],
        ]
    ],
}
# Sobre el alambrado entre los dos cuadrados
EDGE = {"type": "Point", "coordinates": [-68.08, -34.575]}


def add_neighbor(api, session, unit_id: int) -> int:
    """Sector del mismo escenario, pegado al este del sector de prueba."""
    scenario_id = session.scalars(
        select(ProductionUnit.scenario_id).where(ProductionUnit.id == unit_id)
    ).one()
    response = api.post(
        f"/scenarios/{scenario_id}/production-units",
        json={"name": "Vecino", "polygon": EAST_POLYGON},
    )
    assert response.status_code == 201
    return response.json()["id"]


def codes_of(result) -> list[str]:
    return [w["code"] for w in result["warnings"]]


def test_water_limits_the_herd(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=300)

    result = calculate(api, unit_id, **herd_with_cows(session)).json()

    # 300 × 1,2485 ÷ 86,425 = 4,334 EV, menos que los 6,75 del pasto
    water = result["water"]
    assert water["evaluated"] is True
    assert water["refill_l_day"] == pytest.approx(300)
    assert water["limit_cow_equivalents"] == pytest.approx(4.334, abs=0.001)
    max_herd = result["max_herd"]
    assert max_herd["limited_by"] == "water"
    assert max_herd["cow_equivalents"] == pytest.approx(water["limit_cow_equivalents"])
    # 4,334 ÷ 1,2485 = 3,471 vacas, 0,156 toros, 0,694 terneras y vaquillonas
    assert [c["quantity"] for c in max_herd["categories"]] == pytest.approx(
        [3.471, 0.156, 0.694, 0.694], abs=0.001
    )
    # 3 vacas con su toro, ternera y vaquillona suman 5,25 EV: se pasa.
    # 2 vacas y 1 toro suman 3,3 EV.
    herd = result["recommended_herd"]
    assert [c["quantity"] for c in herd["categories"]] == [2, 1, 0, 0]
    assert codes_of(result) == ["missing_index"]


def test_herd_also_fits_in_the_summer_litres(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=2150)

    result = calculate(api, unit_id, **herd_with_cows(session), rainfall_mm=1500).json()

    # Por agua: 2150 × 1,2485 ÷ 86,425 = 31,059 EV; el pasto da unos 33,75.
    # 25 vacas, 1 toro, 5 terneras y 5 vaquillonas suman 31,05 EV y entran,
    # pero piden 2152,5 l/día. Con 24 vacas piden 2082,5.
    assert result["max_herd"]["limited_by"] == "water"
    herd = result["recommended_herd"]
    assert [c["quantity"] for c in herd["categories"]] == [24, 1, 5, 5]


def test_calves_outside_summer_do_not_count(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=300)
    herd = herd_with_cows(
        session, breeding_start="2027-01-01", breeding_end="2027-03-31"
    )

    result = calculate(api, unit_id, **herd).json()

    # Entore el 1/1: las terneras están de abril a octubre.
    # 70 + 2,925 + 0,2 × 42,5 = 81,425 l/día; 300 × 1,2485 ÷ 81,425 = 4,600 EV
    assert result["water"]["limit_cow_equivalents"] == pytest.approx(4.6, abs=0.001)


def test_partial_water_data_warns(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=300)
    add_water_point(api, unit_id, name="Pozo")

    result = calculate(api, unit_id, **herd_with_cows(session)).json()

    assert result["water"]["evaluated"] is True
    assert result["water"]["refill_l_day"] == pytest.approx(300)
    assert "partial_water_data" in codes_of(result)


def test_without_litres_the_pasture_limits(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id, **herd_with_cows(session)).json()

    assert result["water"]["evaluated"] is False
    assert result["water"]["limit_cow_equivalents"] is None
    assert result["water"]["refill_l_day"] is None
    assert result["max_herd"]["limited_by"] == "pasture"
    assert result["max_herd"]["cow_equivalents"] == pytest.approx(
        result["pasture_limit_cow_equivalents"]
    )
    assert "water_not_evaluated" in codes_of(result)
    assert result["recommended_herd"] is not None


def test_point_of_another_sector_does_not_count(api, session, unit_id):
    neighbor_id = add_neighbor(api, session, unit_id)
    add_water_point(api, unit_id, refill_l_day=300)
    add_water_point(api, neighbor_id, location=EDGE, refill_l_day=5000)

    result = calculate(api, unit_id, **herd_with_cows(session)).json()

    assert result["water"]["refill_l_day"] == pytest.approx(300)


def test_shared_point_splits_its_litres(api, session, unit_id):
    neighbor_id = add_neighbor(api, session, unit_id)
    add_water_point(api, unit_id, location=EDGE, refill_l_day=1000, shared=True)

    refills = [
        calculate(api, unit, **herd_with_cows(session)).json()["water"]["refill_l_day"]
        for unit in (unit_id, neighbor_id)
    ]

    # El alcance cubre los dos cuadrados enteros, que miden lo mismo: cada
    # sector recibe la mitad y entre los dos suman todos los litros.
    assert refills == pytest.approx([500, 500], rel=0.001)


def test_breeding_beyond_the_limit_is_rejected(api, session, unit_id):
    add_water_point(api, unit_id)
    herd = herd_with_cows(
        session, breeding_start="9999-06-01", breeding_end="9999-07-01"
    )

    response = calculate(api, unit_id, **herd)

    assert response.status_code == 422


def test_overlapping_sectors_share_the_litres_without_creating_more(
    api, session, unit_id
):
    # La API ya no deja crear sectores superpuestos, pero pueden quedar de antes.
    unit = session.get(ProductionUnit, unit_id)
    copy = ProductionUnit(
        scenario_id=unit.scenario_id,
        name="Copia",
        production_system=ProductionSystem.RAINFED,
        polygon=unit.polygon,
    )
    session.add(copy)
    session.flush()
    add_water_point(api, unit_id, location=EDGE, refill_l_day=1000, shared=True)

    refills = [
        calculate(api, unit, **herd_with_cows(session)).json()["water"]["refill_l_day"]
        for unit in (unit_id, copy.id)
    ]

    # Los dos sectores son idénticos: cada uno recibe la mitad, no los 1.000.
    assert refills == pytest.approx([500, 500], rel=0.001)
