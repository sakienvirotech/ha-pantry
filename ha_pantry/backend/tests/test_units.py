import pytest

from app.api import grocy_edit_url


def test_create_unit(client, grocy):
    response = client.post("/api/units", json={"name": " Jar - 375g "})
    assert response.status_code == 201
    unit = response.json()
    assert unit["name"] == "Jar - 375g"
    stored = grocy.objects["quantity_units"][unit["id"]]
    assert stored["name"] == stored["name_plural"] == "Jar - 375g"
    assert unit in client.get("/api/setup").json()["units"]


@pytest.mark.parametrize("name", ["Can - 225g", "can - 225G", " CAN - 225g "])
def test_duplicate_unit_gets_a_readable_message(client, grocy, name):
    response = client.post("/api/units", json={"name": name})
    assert response.status_code == 409
    assert response.json()["detail"] == "Grocy already has a unit called Can - 225g."
    assert not [c for c in grocy.calls if c[0] == "POST"]


def test_unit_grocy_rejects_as_duplicate_gets_a_readable_message(client, grocy):
    # In case Grocy's check is stricter than ours, its raw SQL error is turned into words.
    grocy.objects["quantity_units"][9] = {"id": 9, "name": "Bag"}
    original = grocy.route

    def hide_units(method, path, query, payload):
        if method == "GET" and path == "objects/quantity_units":
            return 200, []
        return original(method, path, query, payload)

    grocy.route = hide_units
    response = client.post("/api/units", json={"name": "Bag"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Grocy already has a unit with that name."


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_unusable_unit_name_rejected_before_grocy(client, grocy, name):
    assert client.post("/api/units", json={"name": name}).status_code == 422
    assert not grocy.calls


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://a0d7b954-grocy", "/app/a0d7b954_grocy"),
        ("http://a0d7b954-grocy:80/", "/app/a0d7b954_grocy"),
        ("http://local-my-grocy", "/app/local_my_grocy"),
        ("http://192.168.0.5:9283", "http://192.168.0.5:9283/product/7"),
        ("https://grocy.example.com/", "https://grocy.example.com/product/7"),
        ("http://grocy", "http://grocy/product/7"),
    ],
)
def test_grocy_edit_url(url, expected):
    assert grocy_edit_url(url, 7) == expected
