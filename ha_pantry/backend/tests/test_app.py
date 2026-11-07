from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_and_list_products(client):
    created = client.post("/api/products", json={"name": "  Rolled oats "})
    assert created.status_code == 201
    assert created.json()["name"] == "Rolled oats"
    assert [p["name"] for p in client.get("/api/products").json()] == ["Rolled oats"]


def test_blank_name_rejected(client):
    assert client.post("/api/products", json={"name": "   "}).status_code == 422


def test_data_survives_restart(tmp_path: Path):
    app = create_app(data_dir=tmp_path, allowed_clients="testclient")
    with TestClient(app) as first:
        first.post("/api/products", json={"name": "Rice"})
    with TestClient(create_app(data_dir=tmp_path, allowed_clients="testclient")) as second:
        assert [p["name"] for p in second.get("/api/products").json()] == ["Rice"]


def test_other_clients_forbidden(tmp_path: Path):
    app = create_app(data_dir=tmp_path)
    with TestClient(app) as test_client:
        assert test_client.get("/api/health").status_code == 403
