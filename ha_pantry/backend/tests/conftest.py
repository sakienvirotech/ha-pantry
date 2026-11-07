from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.grocy import Grocy
from app.main import create_app
from fake_grocy import FakeGrocy


@pytest.fixture
def grocy() -> FakeGrocy:
    return FakeGrocy()


@pytest.fixture
def client(tmp_path: Path, grocy: FakeGrocy):
    app = create_app(data_dir=tmp_path, allowed_clients="testclient")
    app.state.grocy = Grocy("http://grocy", "test-key", transport=grocy)
    with TestClient(app) as test_client:
        yield test_client
