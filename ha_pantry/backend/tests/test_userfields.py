from pathlib import Path

import pytest

from app.main import create_app


@pytest.fixture
def configured(client):
    client.app.state.product_userfields = ["box", "shelf", "manual", "missing"]
    return client


def create(client, **userfields):
    return client.post(
        "/api/products",
        json={"name": "Oats", "unit_id": 2, "location_id": 3, "userfields": userfields},
    )


def test_option_names_the_fields(tmp_path: Path):
    (tmp_path / "options.json").write_text(
        '{"product_userfields": [" shelf", "box", "", "shelf"]}'
    )
    app = create_app(data_dir=tmp_path, allowed_clients="testclient")
    assert app.state.product_userfields == ["shelf", "box"]


def test_setup_lists_configured_fields_in_order(configured):
    fields = configured.get("/api/setup").json()["userfields"]
    # The file field and the unknown name are left out, not errors.
    assert [f["name"] for f in fields] == ["box", "shelf"]
    assert fields[0] == {
        "name": "box",
        "caption": "Box",
        "type": "preset-checklist",
        "options": ["Pasta", "Teas"],
        "required": False,
        "default": None,
    }
    # Options keep their trailing spaces, so values match Grocy's exactly.
    assert fields[1]["options"] == ["Red", "Large Wire Basket ", "Teal"]


def test_nothing_configured_asks_grocy_nothing(client, grocy):
    assert client.get("/api/setup").json()["userfields"] == []
    product = create(client, shelf="Red").json()
    assert product["userfields"] == []
    assert not [c for c in grocy.calls if "userfields" in c[1]]


def test_create_saves_userfields(configured, grocy):
    response = create(configured, shelf="Large Wire Basket ", box="", notes="ignored")
    assert response.status_code == 201
    body = response.json()
    assert body["warning"] is None
    assert grocy.userfield_values[body["id"]] == {"shelf": "Large Wire Basket "}
    assert body["userfields"] == [{"caption": "Shelf", "value": "Large Wire Basket"}]
    assert configured.get(f"/api/products/{body['id']}").json()["userfields"] == body["userfields"]


def test_value_not_in_the_options_creates_nothing(configured, grocy):
    response = create(configured, shelf="Purple")
    assert response.status_code == 422
    assert response.json()["detail"] == "Purple isn't a valid Shelf."
    assert grocy.objects["products"] == {}


def test_required_field(configured, grocy):
    grocy.objects["userfields"][4]["input_required"] = 1
    response = create(configured, shelf="Red")
    assert response.status_code == 422
    assert response.json()["detail"] == "Box is required."
    assert grocy.objects["products"] == {}


def test_failed_userfield_save_keeps_the_product(configured, grocy):
    original = grocy.route

    def failing(method, path, query, payload):
        if method == "PUT" and path.startswith("userfields/"):
            return 500, {"error_message": "boom"}
        return original(method, path, query, payload)

    grocy.route = failing
    response = create(configured, shelf="Red", box="Teas")
    assert response.status_code == 201
    assert response.json()["warning"] == (
        "The product was created, but Grocy didn't save Box or Shelf."
    )
    assert len(grocy.objects["products"]) == 1


@pytest.mark.parametrize(
    ("field_type", "good", "bad"),
    [
        ("text-single-line", "Top", "x" * 1001),
        ("number-integral", "12", "1.5"),
        ("number-decimal", "1.5", "lots"),
        ("checkbox", "1", "yes"),
        ("date", "2026-11-08", "08/11/2026"),
    ],
)
def test_other_field_types(client, grocy, field_type, good, bad):
    grocy.objects["userfields"][5]["type"] = field_type
    client.app.state.product_userfields = ["notes"]
    assert create(client, notes=bad).status_code == 422
    assert create(client, notes=good).status_code == 201


def test_unticked_checkbox_isnt_shown(client, grocy):
    grocy.objects["userfields"][5]["type"] = "checkbox"
    client.app.state.product_userfields = ["notes"]
    product_id = create(client, notes="0").json()["id"]
    assert client.get(f"/api/products/{product_id}").json()["userfields"] == []
    grocy.userfield_values[product_id]["notes"] = "1"
    shown = client.get(f"/api/products/{product_id}").json()["userfields"]
    assert shown == [{"caption": "Notes", "value": "Yes"}]
