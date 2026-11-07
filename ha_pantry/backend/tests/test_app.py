from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_other_clients_forbidden(tmp_path: Path):
    app = create_app(data_dir=tmp_path)
    with TestClient(app) as test_client:
        assert test_client.get("/api/health").status_code == 403
