from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db import MIGRATIONS_DIR, create_db_engine, run_migrations


def make_tag(client, name="Cereal", kind="category"):
    response = client.post("/api/tags", json={"name": name, "kind": kind})
    assert response.status_code == 201
    return response.json()


def make_product(client, name="Oats", **fields):
    response = client.post("/api/products", json={"name": name, **fields})
    assert response.status_code == 201
    return response.json()


def names(client, **params):
    return [p["name"] for p in client.get("/api/products", params=params).json()]


def test_create_and_list_tags_with_counts(client):
    cereal = make_tag(client, " Cereal ")
    pantry = make_tag(client, "Top shelf", "location")
    make_product(client, tag_ids=[cereal["id"]])

    tags = client.get("/api/tags").json()
    assert [(t["name"], t["kind"], t["product_count"]) for t in tags] == [
        ("Cereal", "category", 1),
        ("Top shelf", "location", 0),
    ]
    assert pantry["kind"] == "location"


def test_kind_is_required_and_checked(client):
    assert client.post("/api/tags", json={"name": "A"}).status_code == 422
    body = {"name": "A", "kind": "colour"}
    assert client.post("/api/tags", json=body).status_code == 422


def test_duplicate_tag_ignores_case(client):
    make_tag(client, "Cereal")
    body = {"name": "CEREAL", "kind": "category"}
    assert client.post("/api/tags", json=body).status_code == 409


def test_same_name_is_allowed_in_each_kind(client):
    make_tag(client, "Freezer", "category")
    make_tag(client, "Freezer", "location")


def test_rename_tag(client):
    tag = make_tag(client)
    url = f"/api/tags/{tag['id']}"
    assert client.put(url, json={"name": "Grains"}).json()["name"] == "Grains"
    assert client.put("/api/tags/999", json={"name": "X"}).status_code == 404


def test_rename_cannot_collide(client):
    make_tag(client, "Cereal")
    other = make_tag(client, "Grains")
    url = f"/api/tags/{other['id']}"
    assert client.put(url, json={"name": "Cereal"}).status_code == 409


def test_kind_cannot_be_changed_by_rename(client):
    tag = make_tag(client)
    body = {"name": "Cereal", "kind": "location"}
    assert client.put(f"/api/tags/{tag['id']}", json=body).status_code == 422


def test_deleting_a_tag_keeps_its_products(client):
    tag = make_tag(client)
    product = make_product(client, tag_ids=[tag["id"]])
    assert client.delete(f"/api/tags/{tag['id']}").status_code == 204
    assert client.get(f"/api/products/{product['id']}").json()["tags"] == []
    assert client.delete(f"/api/tags/{tag['id']}").status_code == 404


def test_deleting_a_product_keeps_its_tags(client):
    tag = make_tag(client)
    product = make_product(client, tag_ids=[tag["id"]])
    client.delete(f"/api/products/{product['id']}")
    assert client.get("/api/tags").json()[0]["product_count"] == 0


def test_product_tags_are_replaced_on_edit(client):
    first = make_tag(client, "Cereal")
    second = make_tag(client, "Top shelf", "location")
    product = make_product(client, tag_ids=[first["id"], first["id"]])
    assert [t["name"] for t in product["tags"]] == ["Cereal"]

    edited = client.put(
        f"/api/products/{product['id']}",
        json={"name": "Oats", "tag_ids": [second["id"]]},
    ).json()
    assert [t["kind"] for t in edited["tags"]] == ["location"]


@pytest.mark.parametrize("method", ["post", "put"])
def test_unknown_tag_is_rejected(client, method):
    product = make_product(client)
    url = "/api/products" if method == "post" else f"/api/products/{product['id']}"
    body = {"name": "Rice", "tag_ids": [999]}
    assert getattr(client, method)(url, json=body).status_code == 422


def test_list_sorts_without_regard_to_case(client):
    for name in ("zucchini", "Apples", "banana"):
        make_product(client, name)
    assert names(client) == ["Apples", "banana", "zucchini"]


@pytest.mark.parametrize(
    "q, expected",
    [
        ("OATS", ["Rolled oats"]),
        ("tobys", ["Rolled oats"]),
        ("930067", ["Rolled oats"]),
        ("cereal", ["Rolled oats"]),
        ("rolled tobys", ["Rolled oats"]),
        ("oats rice", []),
        ("   ", ["Basmati rice", "Rolled oats"]),
        ("%", []),
        ("_", []),
    ],
)
def test_search(client, q, expected):
    tag = make_tag(client)
    make_product(
        client,
        "Rolled oats",
        brand="Uncle Tobys",
        barcodes=["9300675024235"],
        tag_ids=[tag["id"]],
    )
    make_product(client, "Basmati rice")
    assert names(client, q=q) == expected


def test_filter_needs_every_tag(client):
    cereal = make_tag(client)["id"]
    shelf = make_tag(client, "Top shelf", "location")["id"]
    make_product(client, "Oats", tag_ids=[cereal, shelf])
    make_product(client, "Muesli", tag_ids=[cereal])

    assert names(client, tag=[cereal]) == ["Muesli", "Oats"]
    assert names(client, tag=[cereal, shelf]) == ["Oats"]
    assert names(client, tag=[cereal], q="muesli") == ["Muesli"]
    assert names(client, tag=[999]) == []


def test_migration_keeps_existing_products(tmp_path: Path):
    engine = create_db_engine(tmp_path)
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0003")
        connection.execute(text("INSERT INTO products (name) VALUES ('Rice')"))

    run_migrations(engine)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT name FROM products")).scalar() == "Rice"
        assert connection.execute(text("SELECT count(*) FROM tags")).scalar() == 0
