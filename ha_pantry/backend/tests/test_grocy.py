from pathlib import Path
from urllib.error import URLError

import pytest
from fastapi.testclient import TestClient

from app import grocy as grocy_module
from app.grocy import Grocy, GrocyError
from app.main import create_app


def test_status_connected(client):
    assert client.get("/api/status").json() == {
        "connected": True,
        "message": None,
        "grocy_version": "4.7.1",
    }


def test_status_reports_a_bad_key(client):
    client.app.state.grocy.api_key = "wrong"
    body = client.get("/api/status").json()
    assert body["connected"] is False
    assert "API key" in body["message"]


def test_status_when_not_set_up(tmp_path: Path):
    app = create_app(data_dir=tmp_path, allowed_clients="testclient")
    app.state.grocy.api_key = ""
    with TestClient(app) as client:
        body = client.get("/api/status").json()
    assert body["connected"] is False
    assert "isn't set up" in body["message"]


def test_options_configure_grocy(tmp_path: Path):
    (tmp_path / "options.json").write_text(
        '{"grocy_url": "http://grocy.local/", "grocy_api_key": "abc"}'
    )
    app = create_app(data_dir=tmp_path, allowed_clients="testclient")
    assert app.state.grocy.url == "http://grocy.local"
    assert app.state.grocy.api_key == "abc"


def test_unreachable_grocy_gives_a_clear_error(client, monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("Name does not resolve")

    monkeypatch.setattr(grocy_module, "urlopen", fail)
    client.app.state.grocy.transport = grocy_module.urllib_transport
    response = client.get("/api/products")
    assert response.status_code == 502
    assert "Can't reach Grocy" in response.json()["detail"]


@pytest.mark.parametrize(
    "response",
    [(500, b'{"error_message": "boom"}'), (200, b"<html>login</html>")],
)
def test_unexpected_grocy_responses(client, grocy, response):
    grocy.fail_with = response
    result = client.get("/api/products")
    assert result.status_code == 502
    assert "doesn't understand" in result.json()["detail"]


def test_setup_lists_choices_and_the_preset_location(client, grocy):
    body = client.get("/api/setup").json()
    assert [u["name"] for u in body["units"]] == ["Can - 225g", "Piece"]
    assert [l["name"] for l in body["locations"]] == ["Fridge", "Pantry"]
    assert body["groups"] == [{"id": 1, "name": "Grains"}]
    assert body["default_location_id"] == 3


@pytest.mark.parametrize("preset", ["-1", None, "999", "abc"])
def test_setup_ignores_an_unusable_preset(client, grocy, preset):
    grocy.settings["product_presets_location_id"] = preset
    assert client.get("/api/setup").json()["default_location_id"] is None


def test_scan_finds_a_product_by_any_barcode(client, grocy):
    product_id = grocy.add_product("Oats", barcodes=["111111", "222222"], stock=2)
    for code in ("111111", "222222"):
        body = client.get(f"/api/barcodes/{code}").json()
        assert body["id"] == product_id
    assert body == {
        "id": product_id,
        "name": "Oats",
        "stock_amount": 2,
        "unit": "Piece",
        "location": "Pantry",
        "group": None,
        "barcodes": [
            {"id": body["barcodes"][0]["id"], "code": "111111"},
            {"id": body["barcodes"][1]["id"], "code": "222222"},
        ],
        "picture": None,
        "warning": None,
    }


def test_unknown_barcode_is_404(client, grocy):
    grocy.add_product("Oats", barcodes=["111111"])
    assert client.get("/api/barcodes/999999").status_code == 404


def test_barcode_with_special_characters_is_matched_exactly(client, grocy):
    product_id = grocy.add_product("Oats", barcodes=["AB/1&x=2"])
    assert client.get("/api/barcodes/AB%2F1%26x%3D2").json()["id"] == product_id
    assert client.get("/api/barcodes/AB").status_code == 404


def test_product_shows_its_group(client, grocy):
    product_id = grocy.add_product("Oats", group_id=1)
    assert client.get(f"/api/products/{product_id}").json()["group"] == "Grains"


def test_search(client, grocy):
    for name in ("Rolled oats - Uncle Tobys", "Basmati rice", "Crème fraîche"):
        grocy.add_product(name)
    grocy.add_product("Old oats", active=0)

    def names(q):
        return [p["name"] for p in client.get("/api/products", params={"q": q}).json()]

    assert names("") == ["Basmati rice", "Crème fraîche", "Rolled oats - Uncle Tobys"]
    assert names("OATS tobys") == ["Rolled oats - Uncle Tobys"]
    assert names("CRÈME") == ["Crème fraîche"]
    assert names("oats rice") == []


def test_create_product_with_barcode(client, grocy):
    response = client.post(
        "/api/products",
        json={
            "name": " Polenta - Lowan ",
            "unit_id": 5,
            "location_id": 3,
            "group_id": 1,
            "barcode": "9300000000001",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Polenta - Lowan"
    assert body["unit"] == "Can - 225g"
    assert body["group"] == "Grains"
    assert [b["code"] for b in body["barcodes"]] == ["9300000000001"]

    product = grocy.objects["products"][body["id"]]
    assert {product[k] for k in ("qu_id_purchase", "qu_id_stock", "qu_id_consume", "qu_id_price")} == {5}


def test_create_without_location_is_rejected_before_grocy(client, grocy):
    response = client.post("/api/products", json={"name": "Oats", "unit_id": 2})
    assert response.status_code == 422
    assert not [c for c in grocy.calls if c[0] == "POST"]


def test_duplicate_name_gets_a_readable_message(client, grocy):
    grocy.add_product("Oats")
    response = client.post(
        "/api/products", json={"name": "Oats", "unit_id": 2, "location_id": 3}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Grocy already has a product with that name."


def test_create_is_undone_when_the_barcode_is_taken(client, grocy):
    grocy.add_product("Oats", barcodes=["111111"])
    response = client.post(
        "/api/products",
        json={"name": "Rice", "unit_id": 2, "location_id": 3, "barcode": "111111"},
    )
    assert response.status_code == 409
    assert "already on a product" in response.json()["detail"]
    assert [p["name"] for p in grocy.objects["products"].values()] == ["Oats"]


def test_add_stock_is_never_due_unless_a_date_is_given(client, grocy):
    product_id = grocy.add_product("Oats")
    url = f"/api/products/{product_id}/stock/add"

    assert client.post(url).json()["stock_amount"] == 1
    body = client.post(url, json={"amount": 2, "best_before_date": "2027-01-31"}).json()
    assert body["stock_amount"] == 3
    assert [due for _, due in grocy.stock[product_id]] == ["2999-12-31", "2027-01-31"]


def test_remove_stock(client, grocy):
    product_id = grocy.add_product("Oats", stock=3)
    url = f"/api/products/{product_id}/stock/remove"
    assert client.post(url, json={"amount": 2}).json()["stock_amount"] == 1


def test_cannot_remove_more_than_is_in_stock(client, grocy):
    product_id = grocy.add_product("Oats", stock=1)
    response = client.post(f"/api/products/{product_id}/stock/remove", json={"amount": 2})
    assert response.status_code == 400
    assert "cannot be >" in response.json()["detail"]
    assert grocy.amount(product_id) == 1


@pytest.mark.parametrize("amount", [0, -1, 1.5, 10000])
def test_invalid_amount_rejected(client, grocy, amount):
    product_id = grocy.add_product("Oats")
    url = f"/api/products/{product_id}/stock/add"
    assert client.post(url, json={"amount": amount}).status_code == 422


def test_stock_for_a_missing_product(client):
    response = client.post("/api/products/999/stock/add")
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_link_and_unlink_barcode(client, grocy):
    product_id = grocy.add_product("Oats", barcodes=["111111"])
    url = f"/api/products/{product_id}/barcodes"

    linked = client.post(url, json={"code": "222222"})
    assert linked.status_code == 201
    assert client.get("/api/barcodes/222222").json()["id"] == product_id

    barcode_id = linked.json()["barcodes"][1]["id"]
    unlinked = client.delete(f"{url}/{barcode_id}").json()
    assert [b["code"] for b in unlinked["barcodes"]] == ["111111"]


def test_link_rejects_a_barcode_in_use(client, grocy):
    grocy.add_product("Oats", barcodes=["111111"])
    other = grocy.add_product("Rice")
    response = client.post(f"/api/products/{other}/barcodes", json={"code": "111111"})
    assert response.status_code == 409


def test_unlink_needs_the_owning_product(client, grocy):
    grocy.add_product("Oats", barcodes=["111111"])
    other = grocy.add_product("Rice")
    barcode_id = next(iter(grocy.objects["product_barcodes"]))
    url = f"/api/products/{other}/barcodes/{barcode_id}"
    assert client.delete(url).status_code == 404
    assert len(grocy.objects["product_barcodes"]) == 1


def test_unknown_raw_database_error_is_hidden():
    def transport(*args):
        return 400, b'{"error_message": "SQLSTATE[23000]: CHECK constraint failed: x"}'

    with pytest.raises(GrocyError) as raised:
        Grocy("http://grocy", "key", transport=transport).get("objects/products")
    assert raised.value.message == "Grocy rejected the change."
    assert raised.value.status == 400


def similar(client, name):
    response = client.get("/api/similar-products", params={"name": name})
    return [p["name"] for p in response.json()]


def test_similar_ignores_case_and_punctuation(client, grocy):
    grocy.add_product("Mandarin Segments in Syrup - Woolworths")
    grocy.add_product("Mandarin Segments in Juice - SPC")
    grocy.add_product("Peaches Sliced in Syrup - Woolworths")
    grocy.add_product("Golden Syrup - CSR")

    assert similar(client, "Mandarin segments in syrup Woolworths") == [
        "Mandarin Segments in Syrup - Woolworths",
        "Mandarin Segments in Juice - SPC",
        "Peaches Sliced in Syrup - Woolworths",
    ]


def test_similar_allows_extra_words(client, grocy):
    grocy.add_product("Dark Peanut Butter Crunchy - Mayver's")
    assert similar(client, "Dark Peanut Butter Crunchy Mayver's 100% peanuts") == [
        "Dark Peanut Butter Crunchy - Mayver's"
    ]


def test_similar_drops_weak_and_inactive_matches(client, grocy):
    grocy.add_product("Golden Syrup - CSR")
    grocy.add_product("Mandarin Segments in Syrup - Woolworths", active=0)
    assert similar(client, "Mandarin segments in syrup Woolworths") == []
    assert similar(client, "") == []


def test_similar_returns_at_most_five(client, grocy):
    for n in range(8):
        grocy.add_product(f"Baked beans {n}")
    assert len(similar(client, "Baked beans")) == 5


JPEG = b"\xff\xd8\xff\xe0" + b"picture" * 10
OFF_PICTURE = "https://images.openfoodfacts.org/images/products/1/front.jpg"


def create_with_picture(client, url=OFF_PICTURE):
    return client.post(
        "/api/products",
        json={"name": "Nutella", "unit_id": 2, "location_id": 3, "image_url": url},
    )


def test_create_saves_the_picture_to_grocy(client, grocy):
    fetched = []
    client.app.state.fetch_picture = lambda url: fetched.append(url) or JPEG

    body = create_with_picture(client).json()
    assert fetched == [OFF_PICTURE]
    assert body["warning"] is None
    assert body["picture"].startswith(f"ha-pantry-{body['id']}-")
    assert body["picture"].endswith(".jpg")
    assert grocy.files[body["picture"]] == JPEG

    picture = client.get(f"/api/products/{body['id']}/picture")
    assert picture.status_code == 200
    assert picture.headers["content-type"] == "image/jpeg"
    assert picture.content == JPEG


@pytest.mark.parametrize(
    "url",
    [
        "http://images.openfoodfacts.org/a.jpg",
        "https://example.com/a.jpg",
        "https://images.openfoodfacts.org.evil.example/a.jpg",
        "https://images.openfoodfacts.org@192.168.0.1/a.jpg",
        "https://images.openfoodfacts.org:8443/a.jpg",
        "https://192.168.0.41/a.jpg",
    ],
)
def test_picture_from_elsewhere_is_never_fetched(client, grocy, url):
    fetched = []
    client.app.state.fetch_picture = lambda u: fetched.append(u) or JPEG
    response = create_with_picture(client, url)
    assert response.status_code == 201
    assert fetched == []
    assert response.json()["warning"] is not None
    assert response.json()["picture"] is None


@pytest.mark.parametrize(
    "download",
    [b"<html>not found</html>", JPEG + b"x" * 5_000_000],
)
def test_unusable_download_still_creates_the_product(client, grocy, download):
    client.app.state.fetch_picture = lambda url: download
    response = create_with_picture(client)
    assert response.status_code == 201
    assert response.json()["warning"] == "The product was created, but its picture couldn't be saved to Grocy."
    assert grocy.files == {}


def test_failed_download_still_creates_the_product(client, grocy):
    from app.pictures import PictureError

    def fail(url):
        raise PictureError("timed out")

    client.app.state.fetch_picture = fail
    response = create_with_picture(client)
    assert response.status_code == 201
    assert response.json()["warning"] is not None
    assert [p["name"] for p in grocy.objects["products"].values()] == ["Nutella"]


def test_create_without_picture_has_no_warning(client, grocy):
    response = client.post(
        "/api/products", json={"name": "Oats", "unit_id": 2, "location_id": 3}
    )
    assert response.json()["warning"] is None
    assert response.json()["picture"] is None


def test_product_without_picture(client, grocy):
    product_id = grocy.add_product("Oats")
    assert client.get(f"/api/products/{product_id}/picture").status_code == 404


def test_existing_grocy_picture_is_served(client, grocy):
    product_id = grocy.add_product("Oats")
    grocy.objects["products"][product_id]["picture_file_name"] = "abc_oats.png"
    grocy.files["abc_oats.png"] = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    assert client.get(f"/api/products/{product_id}").json()["picture"] == "abc_oats.png"
    response = client.get(f"/api/products/{product_id}/picture")
    assert response.headers["content-type"] == "image/png"
