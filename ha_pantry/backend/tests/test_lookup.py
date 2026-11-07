from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient

from app import lookup as lookup_module
from app.lookup import ProductLookup, RateLimit, SourceUnavailable, fetch_json
from app.main import create_app

CODE = "9300675024235"
OFF_HIT = {
    "product": {
        "product_name": " Rolled oats ",
        "brands": "Uncle Tobys",
        "image_url": "https://images.openfoodfacts.org/oats.jpg",
        "quantity": "500 g",
    }
}
UPC_HIT = {
    "items": [
        {"title": "Oats", "brand": "Acme", "images": ["https://shop.example/a.jpg"]}
    ]
}


class FakeSources:
    def __init__(self, off=None, upc=None):
        self.responses = {"openfoodfacts": off, "upcitemdb": upc}
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        key = "openfoodfacts" if "openfoodfacts" in url else "upcitemdb"
        response = self.responses[key]
        if isinstance(response, Exception):
            raise response
        return response


def test_open_food_facts_match():
    match, failed = ProductLookup(fetch=FakeSources(off=OFF_HIT)).find(CODE)
    assert match.name == "Rolled oats"
    assert match.brand == "Uncle Tobys"
    assert match.image_url == OFF_HIT["product"]["image_url"]
    assert match.quantity == "500 g"
    assert match.source == "Open Food Facts"
    assert failed is False


def test_fallback_is_off_by_default():
    sources = FakeSources(upc=UPC_HIT)
    assert ProductLookup(fetch=sources).find(CODE) == (None, False)
    assert len(sources.urls) == 1


def test_fallback_used_when_there_is_no_match():
    sources = FakeSources(upc=UPC_HIT)
    match, failed = ProductLookup(use_upcitemdb=True, fetch=sources).find(CODE)
    assert match.source == "UPCitemdb"
    assert match.brand == "Acme"
    assert match.image_url is None
    assert failed is False


def test_fallback_not_asked_after_a_match():
    sources = FakeSources(off=OFF_HIT, upc=UPC_HIT)
    ProductLookup(use_upcitemdb=True, fetch=sources).find(CODE)
    assert len(sources.urls) == 1


def test_fallback_still_used_when_first_source_fails():
    sources = FakeSources(off=SourceUnavailable("down"), upc=UPC_HIT)
    match, failed = ProductLookup(use_upcitemdb=True, fetch=sources).find(CODE)
    assert match.source == "UPCitemdb"
    assert failed is True


def test_failure_is_reported_not_raised():
    sources = FakeSources(off=SourceUnavailable("down"))
    assert ProductLookup(fetch=sources).find(CODE) == (None, True)


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"product": None},
        {"product": {"brands": "Only a brand"}},
        {"product": {"product_name": "   "}},
        {"product": {"product_name": 5}},
    ],
)
def test_product_without_a_name_is_no_match(response):
    assert ProductLookup(fetch=FakeSources(off=response)).find(CODE) == (None, False)


def test_unusable_image_is_dropped():
    response = {"product": {"product_name": "Oats", "image_url": "http://x/a.jpg"}}
    match, _ = ProductLookup(fetch=FakeSources(off=response)).find(CODE)
    assert match.image_url is None


def test_long_name_is_cut_to_fit():
    response = {"product": {"product_name": "x" * 500}}
    match, _ = ProductLookup(fetch=FakeSources(off=response)).find(CODE)
    assert len(match.name) == 200


@pytest.mark.parametrize("code", ["ABC123", "123", "1" * 15, "123456/../x", "12345?a"])
def test_non_retail_codes_are_never_sent(code):
    sources = FakeSources(off=OFF_HIT)
    assert ProductLookup(fetch=sources).find(code) == (None, False)
    assert sources.urls == []


def test_rate_limit_window():
    now = [0.0]
    limit = RateLimit(2, 60, clock=lambda: now[0])
    assert limit.allow() and limit.allow()
    assert not limit.allow()
    now[0] = 60.0
    assert limit.allow()


def test_rate_limit_stops_requests_and_reports_failure():
    sources = FakeSources(off=OFF_HIT)
    product_lookup = ProductLookup(fetch=sources)
    for _ in range(15):
        product_lookup.find(CODE)
    assert product_lookup.find(CODE) == (None, True)
    assert len(sources.urls) == 15


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, _limit):
        return self.body


def http_error(status):
    return HTTPError("https://x", status, "error", None, None)


def raise_error(error):
    def urlopen(*args, **kwargs):
        raise error

    return urlopen


def test_fetch_treats_404_as_unknown(monkeypatch):
    monkeypatch.setattr(lookup_module, "urlopen", raise_error(http_error(404)))
    assert fetch_json("https://x") is None


@pytest.mark.parametrize(
    "error", [http_error(429), http_error(503), URLError("no route"), TimeoutError()]
)
def test_fetch_failures_become_source_unavailable(monkeypatch, error):
    monkeypatch.setattr(lookup_module, "urlopen", raise_error(error))
    with pytest.raises(SourceUnavailable):
        fetch_json("https://x")


@pytest.mark.parametrize("body", [b"<html>busy</html>", b"[1, 2]"])
def test_fetch_rejects_unexpected_bodies(monkeypatch, body):
    monkeypatch.setattr(
        lookup_module, "urlopen", lambda *args, **kwargs: FakeResponse(body)
    )
    with pytest.raises(SourceUnavailable):
        fetch_json("https://x")


def test_lookup_endpoint_match(client):
    client.app.state.lookup = ProductLookup(fetch=FakeSources(off=OFF_HIT))
    body = client.get(f"/api/lookup/{CODE}").json()
    assert body["failed"] is False
    assert body["match"]["name"] == "Rolled oats"
    assert body["match"]["source_url"].endswith(f"/product/{CODE}")


def test_lookup_endpoint_failure_is_still_ok(client):
    sources = FakeSources(off=SourceUnavailable("down"))
    client.app.state.lookup = ProductLookup(fetch=sources)
    response = client.get(f"/api/lookup/{CODE}")
    assert response.status_code == 200
    assert response.json() == {"match": None, "failed": True}


@pytest.mark.parametrize(
    "options, sources",
    [
        (None, 1),
        ("{}", 1),
        ('{"upcitemdb_fallback": false}', 1),
        ('{"upcitemdb_fallback": true}', 2),
        ("not json", 1),
    ],
)
def test_fallback_option(tmp_path: Path, options, sources):
    if options is not None:
        (tmp_path / "options.json").write_text(options)
    app = create_app(data_dir=tmp_path, allowed_clients="testclient")
    with TestClient(app):
        assert len(app.state.lookup.sources) == sources
