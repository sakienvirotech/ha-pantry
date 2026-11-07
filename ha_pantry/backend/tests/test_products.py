from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db import MIGRATIONS_DIR, create_db_engine, run_migrations


def create(client, name="Oats", **fields):
    response = client.post("/api/products", json={"name": name, **fields})
    assert response.status_code == 201
    return response.json()


def test_new_product_has_no_stock(client):
    product = create(client, brand=" Uncle Tobys ", barcodes=["9300675024235"])
    assert product["brand"] == "Uncle Tobys"
    assert product["quantity"] == 0
    assert [b["code"] for b in product["barcodes"]] == ["9300675024235"]


def test_scan_finds_product_by_any_of_its_barcodes(client):
    product = create(client, barcodes=["111111", "222222"])
    for code in ("111111", "222222"):
        assert client.get(f"/api/barcodes/{code}").json()["id"] == product["id"]


def test_unknown_barcode_is_404(client):
    assert client.get("/api/barcodes/000000").status_code == 404


def test_barcode_containing_a_slash(client):
    product = create(client, barcodes=["AB/12"])
    assert client.get("/api/barcodes/AB%2F12").json()["id"] == product["id"]


def test_barcode_cannot_belong_to_two_products(client):
    create(client, barcodes=["111111"])
    response = client.post(
        "/api/products", json={"name": "Rice", "barcodes": ["111111"]}
    )
    assert response.status_code == 409
    assert [p["name"] for p in client.get("/api/products").json()] == ["Oats"]


def test_repeated_barcode_in_one_request_is_stored_once(client):
    assert len(create(client, barcodes=["111111", "111111"])["barcodes"]) == 1


def test_link_and_unlink_barcode(client):
    product = create(client, barcodes=["111111"])
    url = f"/api/products/{product['id']}/barcodes"

    linked = client.post(url, json={"code": "222222"})
    assert linked.status_code == 201
    assert client.get("/api/barcodes/222222").json()["id"] == product["id"]

    barcode_id = linked.json()["barcodes"][1]["id"]
    unlinked = client.delete(f"{url}/{barcode_id}")
    assert [b["code"] for b in unlinked.json()["barcodes"]] == ["111111"]
    assert client.get("/api/barcodes/222222").status_code == 404


def test_link_rejects_a_barcode_already_in_use(client):
    create(client, barcodes=["111111"])
    other = create(client, name="Rice")
    response = client.post(
        f"/api/products/{other['id']}/barcodes", json={"code": "111111"}
    )
    assert response.status_code == 409


def test_unlink_needs_the_owning_product(client):
    owner = create(client, barcodes=["111111"])
    other = create(client, name="Rice")
    barcode_id = owner["barcodes"][0]["id"]
    url = f"/api/products/{other['id']}/barcodes/{barcode_id}"
    assert client.delete(url).status_code == 404


def test_add_and_remove_stock(client):
    url = f"/api/products/{create(client)['id']}/stock"
    assert client.post(f"{url}/add").json()["quantity"] == 1
    assert client.post(f"{url}/add", json={"amount": 4}).json()["quantity"] == 5
    assert client.post(f"{url}/remove", json={"amount": 2}).json()["quantity"] == 3


def test_stock_cannot_go_below_zero(client):
    product = create(client)
    url = f"/api/products/{product['id']}"
    client.post(f"{url}/stock/add", json={"amount": 2})

    assert client.post(f"{url}/stock/remove", json={"amount": 3}).status_code == 409
    assert client.get(url).json()["quantity"] == 2


@pytest.mark.parametrize("amount", [0, -1, 1.5, 10000])
def test_invalid_stock_amount_rejected(client, amount):
    url = f"/api/products/{create(client)['id']}/stock/add"
    assert client.post(url, json={"amount": amount}).status_code == 422


def test_stock_change_for_missing_product_is_404(client):
    assert client.post("/api/products/999/stock/add").status_code == 404
    assert client.post("/api/products/999/stock/remove").status_code == 404


def test_edit_changes_details_but_not_stock(client):
    product = create(client, brand="Old")
    url = f"/api/products/{product['id']}"
    client.post(f"{url}/stock/add")

    edited = client.put(url, json={"name": "Rolled oats", "brand": ""}).json()
    assert edited["name"] == "Rolled oats"
    assert edited["brand"] is None
    assert edited["quantity"] == 1


@pytest.mark.parametrize("method", ["post", "put"])
def test_quantity_cannot_be_written_directly(client, method):
    product = create(client)
    url = "/api/products" if method == "post" else f"/api/products/{product['id']}"
    response = getattr(client, method)(url, json={"name": "Oats", "quantity": 5})
    assert response.status_code == 422


def test_deleting_a_product_frees_its_barcodes(client):
    product = create(client, barcodes=["111111"])
    assert client.delete(f"/api/products/{product['id']}").status_code == 204
    assert client.get("/api/barcodes/111111").status_code == 404
    create(client, name="Rice", barcodes=["111111"])


def test_migration_keeps_existing_products(tmp_path: Path):
    engine = create_db_engine(tmp_path)
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0001")
        connection.execute(text("INSERT INTO products (name) VALUES ('Rice')"))

    run_migrations(engine)

    with engine.connect() as connection:
        row = connection.execute(text("SELECT name, brand, quantity FROM products"))
        assert row.one() == ("Rice", None, 0)
