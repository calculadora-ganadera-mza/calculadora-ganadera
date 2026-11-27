from datetime import date

import pytest
from sqlalchemy import delete, func, select, update

from app.models import (
    AnimalCategory,
    CarryingCapacityCalculation,
    Parameter,
    ProductionUnit,
    Scenario,
    Season,
)
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


def test_shows_how_the_carrying_capacity_was_calculated(api, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id, supplemented=True).json()

    # 300 mm × 0,726 = 217,8 kg MS/ha; 3.285 ÷ 217,8 = 15,1 ha/EV
    breakdown = result["pasture_breakdown"]
    assert breakdown["cow_equivalent_dm_intake_kg_year"] == 3285
    assert breakdown["consumable_forage_kg_ha_year"] == pytest.approx(217.8)
    assert round(breakdown["base_carrying_capacity_ha_per_cow_equivalent"], 1) == 15.1
    assert breakdown["indices"] == [
        {"code": "range_condition", "applies": True, "value": None},
        {"code": "early_weaning", "applies": False, "value": None},
        {"code": "supplementation", "applies": True, "value": None},
    ]


def test_simulation_uses_the_supplied_rainfall(api, unit_id):
    add_water_point(api, unit_id)

    response = calculate(api, unit_id, rainfall_mm=600)

    assert response.status_code == 200
    result = response.json()
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


# Rodeo de cría máximo. El sector de prueba tiene unas 101,8 ha y, con
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


def test_max_breeding_herd_fits_in_the_pasture_limit(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id, **herd_with_cows(session)).json()

    # 5 vacas con su toro, ternera y vaquillona suman 7,25 EV: se pasa.
    # 4 vacas + 1 toro + 1 ternera + 1 vaquillona = 4 + 1,3 + 0,25 + 0,7 = 6,25.
    herd = result["max_breeding_herd"]
    assert [c["quantity"] for c in herd["categories"]] == [4, 1, 1, 1]
    assert herd["cow_equivalents"] == pytest.approx(6.25)
    assert herd["cow_equivalents"] <= result["pasture_limit_cow_equivalents"]
    assert herd["weaned_calves"] == {"males": 1, "females": 1}


def test_without_animals_the_water_is_not_evaluated(api, unit_id):
    add_water_point(api, unit_id, refill_l_day=300)

    result = calculate(api, unit_id).json()

    # Sin animales no hay litros por EV: no hay límite por agua ni demanda.
    assert result["max_breeding_herd"] is None
    assert result["water"]["evaluated"] is False
    assert result["water"]["limit_cow_equivalents"] is None
    assert result["water"]["refill_l_day"] == pytest.approx(300)
    assert result["water"]["summer_need_l_day"] is None
    assert result["water"]["winter_need_l_day"] is None
    assert result["max_herd"] == {
        "cow_equivalents": pytest.approx(result["pasture_limit_cow_equivalents"]),
        "limited_by": "pasture",
    }
    codes = [w["code"] for w in result["warnings"]]
    assert codes == ["missing_index", "water_not_evaluated"]
    assert result["scaled_herd"] is None
    load = result["load_thermometer"]
    assert load["status"] == "below"
    assert load["current_cow_equivalents"] == 0


def test_bulls_per_100_cows_from_the_request(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(
        api, unit_id, **herd_with_cows(session), bulls_per_100_cows=50
    ).json()

    # 3 vacas con 50 toros cada 100: round(1,5) = 2 toros.
    assert [c["quantity"] for c in result["max_breeding_herd"]["categories"]][:2] == [
        3,
        2,
    ]


def test_replacement_above_weaned_females_warns(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id, **herd_with_cows(session, weaning_rate=0.3)).json()

    codes = [w["code"] for w in result["warnings"]]
    assert "replacement_exceeds_females" in codes
    assert result["max_breeding_herd"] is not None


def test_field_too_small_for_a_cow_and_her_bull(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(api, unit_id, **herd_with_cows(session), rainfall_mm=1).json()

    assert result["max_breeding_herd"] is None
    assert "herd_does_not_fit" in [w["code"] for w in result["warnings"]]
    assert result["pasture_limit_cow_equivalents"] > 0
    assert result["scaled_herd"] is None
    assert result["load_thermometer"]["status"] == "above"


# Límite por agua. Con herd_with_cows (reposición 0,2, entore el 1/11) las
# terneras están en el campo de febrero a agosto: cuentan en verano y en
# invierno. El rodeo actual son 10 vacas y 10 × 0,2 = 2 terneras a 0,25 EV
# anual: 10,5 EV, que piden 10 × 70 + 2 × 25 = 750 l/día en verano y
# 10 × 37,5 + 2 × 12,5 = 400 en invierno.
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

    # 300 × 10,5 ÷ 750 = 4,2 EV, menos que los 6,75 del pasto
    water = result["water"]
    assert water["evaluated"] is True
    assert water["refill_l_day"] == pytest.approx(300)
    assert water["limit_cow_equivalents"] == pytest.approx(4.2)
    # La demanda se calcula con el pasto, aunque el agua limite el rodeo.
    pasture_limit = result["pasture_limit_cow_equivalents"]
    assert water["summer_need_l_day"] == pytest.approx(pasture_limit * 750 / 10.5)
    assert water["winter_need_l_day"] == pytest.approx(pasture_limit * 400 / 10.5)
    assert result["max_herd"] == {
        "cow_equivalents": pytest.approx(4.2),
        "limited_by": "water",
    }
    # El rodeo de cría parte del pasto y baja hasta entrar en los 300 l/día:
    # 4 vacas con su toro, ternera y vaquillona piden 412,5 y 3 piden 342,5.
    # 2 vacas y 1 toro piden 205 l/día y suman 3,3 EV.
    herd = result["max_breeding_herd"]
    assert [c["quantity"] for c in herd["categories"]] == [2, 1, 0, 0]
    assert herd["cow_equivalents"] == pytest.approx(3.3)
    assert codes_of(result) == ["missing_index"]


def test_max_breeding_herd_can_exceed_the_max_herd(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=2100)

    result = calculate(api, unit_id, **herd_with_cows(session), rainfall_mm=1500).json()

    # Por agua: 2100 × 10,5 ÷ 750 = 29,4 EV; el pasto da unos 33,75.
    # El rodeo de cría parte del pasto: 27, 26 y 25 vacas con 1 toro,
    # 5 terneras y 5 vaquillonas piden 2292,5, 2222,5 y 2152,5 l/día.
    # 24 vacas piden 2082,5 y suman 30,05 EV: más que el rodeo máximo,
    # porque piden menos litros por EV que el rodeo actual.
    assert result["max_herd"]["limited_by"] == "water"
    assert result["max_herd"]["cow_equivalents"] == pytest.approx(29.4)
    herd = result["max_breeding_herd"]
    assert [c["quantity"] for c in herd["categories"]] == [24, 1, 5, 5]
    assert herd["cow_equivalents"] == pytest.approx(30.05)


def test_calves_outside_summer_do_not_count(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=300)
    herd = herd_with_cows(
        session, breeding_start="2027-01-01", breeding_end="2027-03-31"
    )

    result = calculate(api, unit_id, **herd).json()

    # Entore el 1/1: las terneras están de abril a octubre, fuera del verano.
    # En verano piden 10 × 70 = 700 l/día; 300 × 10,5 ÷ 700 = 4,5 EV.
    water = result["water"]
    assert water["limit_cow_equivalents"] == pytest.approx(4.5)
    pasture_limit = result["pasture_limit_cow_equivalents"]
    assert water["summer_need_l_day"] == pytest.approx(pasture_limit * 700 / 10.5)
    assert water["winter_need_l_day"] == pytest.approx(pasture_limit * 400 / 10.5)


def test_winter_need_uses_the_configured_months(api, session, unit_id):
    add_water_point(api, unit_id)
    for key, value in [("winter_start_month", 12), ("winter_end_month", 1)]:
        session.execute(
            update(Parameter).where(Parameter.key == key).values(value=value)
        )
    herd = herd_with_cows(
        session, breeding_start="2027-01-01", breeding_end="2027-03-31"
    )

    result = calculate(api, unit_id, **herd).json()

    # Diciembre y enero quedan fuera de la etapa de ternera: en invierno piden
    # solo las vacas, 10 × 37,5 = 375 l/día.
    pasture_limit = result["pasture_limit_cow_equivalents"]
    assert result["water"]["winter_need_l_day"] == pytest.approx(
        pasture_limit * 375 / 10.5
    )


def test_breeding_herd_ignores_heifers_outside_summer(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=450)
    session.execute(
        update(Parameter)
        .where(Parameter.key == "heifer_first_breeding_age_months")
        .values(value=13)
    )

    result = calculate(api, unit_id, **herd_with_cows(session)).json()

    # Las vaquillonas están en agosto y septiembre: en verano no piden agua.
    # Su EV anual es 0,7 ÷ 12. 6 vacas con su toro, ternera y vaquillona
    # suman 7,61 EV: se pasa. 5 vacas suman 6,61 EV y piden
    # 5 × 70 + 65 + 25 = 440 l/día; con la vaquillona serían 482,5.
    herd = result["max_breeding_herd"]
    assert [c["quantity"] for c in herd["categories"]] == [5, 1, 1, 1]


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
    assert result["water"]["summer_need_l_day"] > 0
    assert result["water"]["winter_need_l_day"] > 0
    assert result["max_herd"]["limited_by"] == "pasture"
    assert result["max_herd"]["cow_equivalents"] == pytest.approx(
        result["pasture_limit_cow_equivalents"]
    )
    assert "water_not_evaluated" in codes_of(result)
    assert result["max_breeding_herd"] is not None


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


def test_sector_list_shows_the_same_litres_as_the_calculation(api, session, unit_id):
    neighbor_id = add_neighbor(api, session, unit_id)
    add_water_point(api, unit_id, location=EDGE, refill_l_day=1000, shared=True)
    add_water_point(api, unit_id, refill_l_day=300)
    scenario_id = session.get(ProductionUnit, unit_id).scenario_id

    units = api.get(f"/scenarios/{scenario_id}/production-units").json()

    # El sector tiene sus 300 más la mitad de la compartida; el vecino, la otra
    # mitad.
    refills = {unit["id"]: unit["refill_l_day"] for unit in units}
    assert refills[unit_id] == pytest.approx(800, rel=0.001)
    assert refills[neighbor_id] == pytest.approx(500, rel=0.001)


def test_sector_without_litres_has_no_refill(api, session, unit_id):
    add_water_point(api, unit_id)
    scenario_id = session.get(ProductionUnit, unit_id).scenario_id

    [unit] = api.get(f"/scenarios/{scenario_id}/production-units").json()

    assert unit["refill_l_day"] is None


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


# Mi rodeo ajustado al campo. Con herd_with_cows el rodeo actual son 10 vacas
# y 2 terneras: 10 × 0,2 = 2; destetados 5, hembras 2,5 -> 3.


def category_ids(session) -> dict[str, int]:
    return dict(session.execute(select(AnimalCategory.code, AnimalCategory.id)).all())


def test_scaled_herd_keeps_the_loaded_proportions(api, session, unit_id):
    add_water_point(api, unit_id)
    ids = category_ids(session)
    herd = herd_with_cows(
        session,
        categories=[
            {"animal_category_id": ids["cow"], "quantity": 10},
            {"animal_category_id": ids["steer"], "quantity": 5},
        ],
    )

    result = calculate(api, unit_id, **herd).json()

    # Sin litros se ajusta hasta el rodeo máximo, unos 6,75 EV de pasto.
    # 5 vacas: novillos 2,5 -> 3, terneras 1; 5 + 2,4 + 0,25 = 7,65 se pasa.
    # 4 vacas: novillos 2, terneras 0,8 -> 1; 4 + 1,6 + 0,25 = 5,85.
    scaled = result["scaled_herd"]
    assert scaled["cow_equivalents"] == pytest.approx(5.85)
    assert [
        (c["animal_category_id"], c["current_quantity"], c["quantity"])
        for c in scaled["categories"]
    ] == [(ids["cow"], 10, 4), (ids["calf"], 2, 1), (ids["steer"], 5, 2)]


def test_scaled_herd_fits_in_the_max_herd(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=300)

    result = calculate(api, unit_id, **herd_with_cows(session)).json()

    # El agua limita el rodeo máximo a 4,2 EV. 4 vacas con 1 ternera suman
    # 4,25 EV: se pasa. 3 vacas con 1 ternera suman 3,25 EV y piden 235 l/día.
    scaled = result["scaled_herd"]
    assert result["max_herd"]["cow_equivalents"] == pytest.approx(4.2)
    assert scaled["cow_equivalents"] == pytest.approx(3.25)
    assert [c["quantity"] for c in scaled["categories"]] == [3, 1]
    load = result["load_thermometer"]
    assert load["status"] == "above"
    assert load["current_cow_equivalents"] == pytest.approx(10.5)
    assert load["below_cow_equivalents"] == pytest.approx(4.2 * 0.9)


def test_load_counts_the_annual_equivalent_for_early_weaning(api, session, unit_id):
    add_water_point(api, unit_id)

    result = calculate(
        api, unit_id, **herd_with_cows(session, early_weaning=True)
    ).json()

    # 10 vacas y 2 terneras a 0,5 EV por 9 de 12 meses.
    assert result["load_thermometer"]["current_cow_equivalents"] == pytest.approx(10.75)


def test_herd_without_cows_uses_its_own_litres(api, session, unit_id):
    add_water_point(api, unit_id, refill_l_day=300)
    steer = category_ids(session)["steer"]

    result = calculate(
        api, unit_id, categories=[{"animal_category_id": steer, "quantity": 10}]
    ).json()

    # 10 novillos suman 8 EV y piden 425 l/día en verano y 200 en invierno.
    # 300 × 8 ÷ 425 = 5,65 EV, menos que los 6,75 del pasto.
    water = result["water"]
    assert water["limit_cow_equivalents"] == pytest.approx(300 * 8 / 425)
    pasture_limit = result["pasture_limit_cow_equivalents"]
    assert water["summer_need_l_day"] == pytest.approx(pasture_limit * 425 / 8)
    assert water["winter_need_l_day"] == pytest.approx(pasture_limit * 200 / 8)
    assert result["max_herd"]["limited_by"] == "water"
    assert result["max_breeding_herd"] is None
    assert result["scaled_herd"] is None
    assert codes_of(result) == ["missing_index"]
    load = result["load_thermometer"]
    assert load["status"] == "above"
    assert load["current_cow_equivalents"] == pytest.approx(8)


def test_load_status_uses_the_threshold_from_parameters(api, session, unit_id):
    add_water_point(api, unit_id)
    cow = category_ids(session)["cow"]
    herd = herd_with_cows(
        session,
        categories=[{"animal_category_id": cow, "quantity": 6}],
        replacement_rate=0,
    )

    initial = calculate(api, unit_id, **herd).json()
    assert initial["load_thermometer"]["status"] == "below"
    assert initial["load_thermometer"]["below_cow_equivalents"] == pytest.approx(
        initial["max_herd"]["cow_equivalents"] * 0.9
    )

    session.execute(
        update(Parameter)
        .where(Parameter.key == "load_thermometer_below_threshold")
        .values(value=0.85)
    )
    updated = calculate(api, unit_id, **herd).json()
    assert updated["load_thermometer"]["status"] == "within"
    assert updated["load_thermometer"]["below_cow_equivalents"] == pytest.approx(
        updated["max_herd"]["cow_equivalents"] * 0.85
    )


# Guardado, consulta y borrado de cálculos


@pytest.fixture
def saved_farm(api, session, unit_id) -> dict[str, int]:
    """Sector con aguada y campaña asociada para probar cálculos guardados."""
    scenario_id = session.scalars(
        select(ProductionUnit.scenario_id).where(ProductionUnit.id == unit_id)
    ).one()
    season = Season(
        scenario_id=scenario_id,
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
        rainfall_mm=300,
    )
    session.add(season)
    session.flush()
    add_water_point(api, unit_id, refill_l_day=1000)
    return {"scenario_id": scenario_id, "season_id": season.id, "unit_id": unit_id}


def saved_input(session, **changes) -> dict:
    return (
        {"range_condition": "good", "rainfall_mm": 300}
        | herd_with_cows(session)
        | changes
    )


def save_calculation(api, unit_id: int, season_id: int, kind: str, calc_input: dict):
    return api.post(
        f"/production-units/{unit_id}/carrying-capacity-calculations",
        json={"season_id": season_id, "kind": kind, "input": calc_input},
    )


def test_save_calculation_records_result_and_reference_values(api, session, saved_farm):
    calc_input = saved_input(session)

    response = save_calculation(
        api, saved_farm["unit_id"], saved_farm["season_id"], "result", calc_input
    )

    assert response.status_code == 201
    saved = response.json()
    assert saved["production_unit_id"] == saved_farm["unit_id"]
    assert saved["season_id"] == saved_farm["season_id"]
    assert saved["scenario_name"] == "Campo"
    assert saved["production_unit_name"] == "Sector"
    assert saved["season_start_date"] == "2026-07-01"
    assert saved["season_end_date"] == "2027-06-30"
    assert saved["kind"] == "result"
    assert saved["season_updated"] is False
    assert saved["input"]["rainfall_mm"] == 300
    assert "bulls_per_100_cows" not in saved["input"]
    assert saved["result"]["pasture_limit_cow_equivalents"] > 0

    refs = saved["reference_values"]
    assert refs["parameters"]["cow_equivalent_dm_intake_kg_year"] == 3285
    assert refs["parameters"]["water_point_radius_km"] == 2.5
    assert len(refs["animal_categories"]) == 5
    cow_ref = next(c for c in refs["animal_categories"] if c["code"] == "cow")
    assert cow_ref["cow_equivalent"] == 1.0


def test_saved_calculation_does_not_change_when_reference_values_change(
    api, session, saved_farm
):
    calc_input = saved_input(session)
    saved = save_calculation(
        api, saved_farm["unit_id"], saved_farm["season_id"], "simulation", calc_input
    ).json()

    # El administrador cambia parámetros y categorías después del guardado
    session.execute(
        update(Parameter)
        .where(Parameter.key == "cow_equivalent_dm_intake_kg_year")
        .values(value=6570)
    )
    session.execute(
        update(AnimalCategory)
        .where(AnimalCategory.code == "cow")
        .values(cow_equivalent=2.0, name="Vaca editada")
    )
    session.flush()

    # Un cálculo nuevo refleja los valores cambiados
    fresh = api.post(
        f"/production-units/{saved_farm['unit_id']}/carrying-capacity", json=calc_input
    ).json()
    assert fresh["carrying_capacity_ha_per_cow_equivalent"] == pytest.approx(
        saved["result"]["carrying_capacity_ha_per_cow_equivalent"] * 2
    )

    # El cálculo guardado sigue intacto al consultarlo por ID y al listarlo
    fetched = api.get(f"/carrying-capacity-calculations/{saved['id']}").json()
    [listed] = api.get(
        f"/production-units/{saved_farm['unit_id']}/carrying-capacity-calculations"
    ).json()

    for copy in (fetched, listed):
        assert copy["result"] == saved["result"]
        assert (
            copy["reference_values"]["parameters"]["cow_equivalent_dm_intake_kg_year"]
            == 3285
        )
        cow_ref = next(
            c
            for c in copy["reference_values"]["animal_categories"]
            if c["code"] == "cow"
        )
        assert cow_ref["cow_equivalent"] == 1.0
        assert cow_ref["name"] == "Vaca"


def test_saving_new_season_result_demotes_previous_result_to_simulation(
    api, session, saved_farm
):
    first = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "result",
        saved_input(session),
    ).json()
    second = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "result",
        saved_input(session, rainfall_mm=450),
    ).json()

    assert first["kind"] == "result"
    assert second["kind"] == "result"

    listed = api.get(
        f"/production-units/{saved_farm['unit_id']}/carrying-capacity-calculations"
    ).json()
    assert [item["id"] for item in listed] == [second["id"], first["id"]]
    assert [item["kind"] for item in listed] == ["result", "simulation"]


def test_saving_simulation_keeps_existing_season_result(api, session, saved_farm):
    season_result = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "result",
        saved_input(session),
    ).json()
    simulation = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "simulation",
        saved_input(session, rainfall_mm=450),
    ).json()

    listed = api.get(
        f"/production-units/{saved_farm['unit_id']}/carrying-capacity-calculations"
    ).json()
    assert [(item["id"], item["kind"]) for item in listed] == [
        (simulation["id"], "simulation"),
        (season_result["id"], "result"),
    ]


def test_result_uniqueness_is_scoped_per_season(api, session, saved_farm):
    other_season = Season(
        scenario_id=saved_farm["scenario_id"],
        start_date=date(2027, 7, 1),
        end_date=date(2028, 6, 30),
        rainfall_mm=320,
    )
    session.add(other_season)
    session.flush()

    first = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "result",
        saved_input(session),
    ).json()
    other = save_calculation(
        api,
        saved_farm["unit_id"],
        other_season.id,
        "result",
        saved_input(session, breeding_start="2027-11-01", breeding_end="2028-01-31"),
    ).json()

    assert (
        api.get(f"/carrying-capacity-calculations/{first['id']}").json()["kind"]
        == "result"
    )
    assert (
        api.get(f"/carrying-capacity-calculations/{other['id']}").json()["kind"]
        == "result"
    )

    filtered = api.get(
        f"/production-units/{saved_farm['unit_id']}/carrying-capacity-calculations",
        params={"season_id": other_season.id},
    ).json()
    assert [item["id"] for item in filtered] == [other["id"]]


def test_delete_saved_calculation(api, session, saved_farm):
    saved = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "simulation",
        saved_input(session),
    ).json()

    delete_res = api.delete(f"/carrying-capacity-calculations/{saved['id']}")
    assert delete_res.status_code == 204
    assert api.get(f"/carrying-capacity-calculations/{saved['id']}").status_code == 404
    assert (
        api.delete(f"/carrying-capacity-calculations/{saved['id']}").status_code == 404
    )
    assert (
        api.get(
            f"/production-units/{saved_farm['unit_id']}/carrying-capacity-calculations"
        ).json()
        == []
    )


def test_cannot_access_or_delete_another_users_calculation(
    api, session, saved_farm, other_user
):
    other_scenario = Scenario(user_id=other_user.id, name="Ajeno", is_main=True)
    session.add(other_scenario)
    session.flush()
    other_season = Season(
        scenario_id=other_scenario.id,
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
    )
    other_unit = ProductionUnit(
        scenario_id=other_scenario.id,
        name="Sector ajeno",
        production_system=ProductionSystem.RAINFED,
        polygon="SRID=4326;POLYGON((-68.09 -34.58,-68.08 -34.58,-68.08 -34.57,"
        "-68.09 -34.57,-68.09 -34.58))",
    )
    session.add_all([other_season, other_unit])
    session.flush()

    # No puede guardar ni listar en un sector ajeno
    assert (
        save_calculation(
            api, other_unit.id, other_season.id, "simulation", saved_input(session)
        ).status_code
        == 404
    )
    assert (
        api.get(
            f"/production-units/{other_unit.id}/carrying-capacity-calculations"
        ).status_code
        == 404
    )
    # Tampoco puede usar una campaña de otro escenario en su propio sector
    assert (
        save_calculation(
            api,
            saved_farm["unit_id"],
            other_season.id,
            "simulation",
            saved_input(session),
        ).status_code
        == 404
    )

    # Cálculo persistido de otro usuario: 404 al consultar o borrar
    other_calc = CarryingCapacityCalculation(
        scenario_id=other_scenario.id,
        season_id=other_season.id,
        production_unit_id=other_unit.id,
        kind="simulation",
        input=saved_input(session),
        reference_values={"parameters": {}, "animal_categories": []},
        result={},
    )
    session.add(other_calc)
    session.flush()

    assert (
        api.get(f"/carrying-capacity-calculations/{other_calc.id}").status_code == 404
    )
    assert (
        api.delete(f"/carrying-capacity-calculations/{other_calc.id}").status_code
        == 404
    )


def test_deleting_scenario_cascades_saved_calculations(api, session, saved_farm):
    save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "result",
        saved_input(session),
    )

    session.execute(delete(Scenario).where(Scenario.id == saved_farm["scenario_id"]))

    assert (
        session.scalar(select(func.count()).select_from(CarryingCapacityCalculation))
        == 0
    )


def test_update_season_true_is_rejected_until_implemented(api, session, saved_farm):
    response = api.post(
        f"/production-units/{saved_farm['unit_id']}/carrying-capacity-calculations",
        json={
            "season_id": saved_farm["season_id"],
            "kind": "result",
            "update_season": True,
            "input": saved_input(session),
        },
    )

    assert response.status_code == 422


def test_list_user_calculations_returns_summary_history(
    api, session, saved_farm, other_user
):
    first = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "simulation",
        saved_input(session, rainfall_mm=300),
    ).json()
    second = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "result",
        saved_input(session, rainfall_mm=450, bulls_per_100_cows=6),
    ).json()
    assert second["input"]["bulls_per_100_cows"] == 6
    assert "bulls_per_100_cows" not in second["reference_values"]["parameters"]
    assert "bulls_per_100_cows" in first["reference_values"]["parameters"]

    summary = api.get("/carrying-capacity-calculations").json()

    assert [item["id"] for item in summary] == [second["id"], first["id"]]
    assert summary[0]["scenario_name"] == "Campo"
    assert summary[0]["production_unit_name"] == "Sector"
    assert summary[0]["season_start_date"] == "2026-07-01"
    assert summary[0]["season_end_date"] == "2027-06-30"
    assert summary[0]["kind"] == "result"
    assert summary[0]["rainfall_mm"] == 450
    assert summary[0]["max_herd_cow_equivalents"] == pytest.approx(
        second["result"]["max_herd"]["cow_equivalents"]
    )
    assert summary[0]["carrying_capacity_ha_per_cow_equivalent"] == pytest.approx(
        second["result"]["carrying_capacity_ha_per_cow_equivalent"]
    )


def test_save_rejects_breeding_outside_season(api, session, saved_farm):
    response = save_calculation(
        api,
        saved_farm["unit_id"],
        saved_farm["season_id"],
        "result",
        saved_input(session, breeding_start="2025-11-01", breeding_end="2026-01-31"),
    )

    assert response.status_code == 422
