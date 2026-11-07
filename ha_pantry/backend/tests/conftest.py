from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(data_dir=tmp_path, allowed_clients="testclient")
    with TestClient(app) as test_client:
        yield test_client
