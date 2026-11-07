"""Finds product details for a barcode, to pre-fill the add form.

Nothing here may stop someone adding a product by hand, so every failure ends
in a result the caller can show rather than an exception.
"""
import http.client
import json
import re
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Open Food Facts asks for AppName/Version, ideally with contact details.
USER_AGENT = "HA-Pantry/0.3 (Home Assistant app)"
TIMEOUT_SECONDS = 5
MAX_RESPONSE_BYTES = 2_000_000
MAX_TEXT_LENGTH = 200
MAX_IMAGE_URL_LENGTH = 500
# Only retail product codes, which also keeps the code safe to put in a URL.
RETAIL_CODE = re.compile(r"\d{6,14}")

OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org"
UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup"


class SourceUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Match:
    name: str
    brand: str | None
    image_url: str | None
    source: str
    source_url: str


Fetch = Callable[[str], dict[str, Any] | None]


def fetch_json(url: str) -> dict[str, Any] | None:
    """Returns the decoded response, or None when the source doesn't know the code."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read(MAX_RESPONSE_BYTES))
    except HTTPError as error:
        if error.code == 404:
            return None
        raise SourceUnavailable(f"HTTP {error.code}") from error
    except (URLError, OSError, ValueError, http.client.HTTPException) as error:
        raise SourceUnavailable(str(error)) from error
    if not isinstance(data, dict):
        raise SourceUnavailable("Unexpected response")
    return data


class RateLimit:
    """Sliding window, because going over a source's limit can get the IP banned."""

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()

    def allow(self) -> bool:
        now = self.clock()
        with self.lock:
            while self.calls and now - self.calls[0] >= self.window_seconds:
                self.calls.popleft()
            if len(self.calls) >= self.limit:
                return False
            self.calls.append(now)
            return True


def clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip()[:MAX_TEXT_LENGTH].strip() or None


def clean_image_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.startswith("https://"):
        return None
    return value if len(value) <= MAX_IMAGE_URL_LENGTH else None


class OpenFoodFacts:
    name = "Open Food Facts"
    rate_limit_args = (15, 60)

    @staticmethod
    def search(code: str, fetch: Fetch) -> Match | None:
        data = fetch(
            f"{OPEN_FOOD_FACTS_URL}/api/v3.6/product/{code}.json"
            "?fields=product_name,brands,image_url"
        )
        product = (data or {}).get("product")
        if not isinstance(product, dict):
            return None
        name = clean_text(product.get("product_name"))
        if name is None:
            return None
        return Match(
            name=name,
            brand=clean_text(product.get("brands")),
            image_url=clean_image_url(product.get("image_url")),
            source=OpenFoodFacts.name,
            source_url=f"{OPEN_FOOD_FACTS_URL}/product/{code}",
        )


class UpcItemDb:
    name = "UPCitemdb"
    rate_limit_args = (100, 86400)

    @staticmethod
    def search(code: str, fetch: Fetch) -> Match | None:
        data = fetch(f"{UPCITEMDB_URL}?upc={code}")
        items = (data or {}).get("items")
        if not isinstance(items, list) or not items or not isinstance(items[0], dict):
            return None
        name = clean_text(items[0].get("title"))
        if name is None:
            return None
        # No images: UPCitemdb points at retailers' sites, with no usable licence.
        return Match(
            name=name,
            brand=clean_text(items[0].get("brand")),
            image_url=None,
            source=UpcItemDb.name,
            source_url=f"https://www.upcitemdb.com/upc/{code}",
        )


class ProductLookup:
    def __init__(self, use_upcitemdb: bool = False, fetch: Fetch = fetch_json):
        self.fetch = fetch
        sources = [OpenFoodFacts, UpcItemDb] if use_upcitemdb else [OpenFoodFacts]
        self.sources = [(s, RateLimit(*s.rate_limit_args)) for s in sources]

    def find(self, code: str) -> tuple[Match | None, bool]:
        """Returns the first match, and whether any source couldn't be asked."""
        failed = False
        if not RETAIL_CODE.fullmatch(code):
            return None, failed
        for source, rate_limit in self.sources:
            if not rate_limit.allow():
                failed = True
                continue
            try:
                match = source.search(code, self.fetch)
            except SourceUnavailable:
                failed = True
                continue
            if match:
                return match, failed
        return None, failed
