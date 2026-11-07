"""A small client for the Grocy REST API, which stores all pantry data.

Grocy's errors are turned into messages a person can act on, because some
of them are raw database errors.
"""
import http.client
import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 20_000_000

NOT_SET_UP = "Grocy isn't set up. Add its URL and API key in the App's configuration."
UNREACHABLE = "Can't reach Grocy. Check that it's running, and its URL in the App's configuration."
BAD_KEY = "Grocy rejected the API key. Check it in the App's configuration."
UNEXPECTED = "Grocy sent a response HA-Pantry doesn't understand."
REJECTED = "Grocy rejected the change."

# Raw database errors Grocy is known to return, as (text, status, message).
KNOWN_ERRORS = [
    (
        "UNIQUE constraint failed: product_barcodes.barcode",
        409,
        "That barcode is already on a product in Grocy.",
    ),
    (
        "UNIQUE constraint failed: products.name",
        409,
        "Grocy already has a product with that name.",
    ),
]


class GrocyError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


Transport = Callable[[str, str, bytes | None, dict[str, str]], tuple[int, bytes]]


def urllib_transport(
    method: str, url: str, body: bytes | None, headers: dict[str, str]
) -> tuple[int, bytes]:
    request = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read(MAX_RESPONSE_BYTES)
    except HTTPError as error:
        return error.code, error.read(MAX_RESPONSE_BYTES)
    except (URLError, OSError, http.client.HTTPException) as error:
        logger.warning("Grocy request failed: %s", error)
        raise GrocyError(502, UNREACHABLE) from error


def error_for(status: int, data: Any) -> GrocyError:
    message = data.get("error_message") if isinstance(data, dict) else None
    if status == 401:
        return GrocyError(502, BAD_KEY)
    if status >= 500 or not isinstance(message, str):
        logger.warning("Grocy returned HTTP %s: %s", status, data)
        return GrocyError(502, UNEXPECTED)
    for text, mapped_status, friendly in KNOWN_ERRORS:
        if text in message:
            return GrocyError(mapped_status, friendly)
    if "SQLSTATE" in message:
        logger.warning("Grocy rejected a change: %s", message)
        return GrocyError(400, REJECTED)
    return GrocyError(404 if status == 404 else 400, message)


def query(field: str, value: str | int) -> str:
    """Builds Grocy's filter parameter, an exact match on one field."""
    return "query%5B%5D=" + quote(f"{field}={value}", safe="")


class Grocy:
    def __init__(self, url: str, api_key: str, transport: Transport = urllib_transport):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.transport = transport

    def request(self, method: str, path: str, body: dict | None = None) -> Any:
        if not self.url or not self.api_key:
            raise GrocyError(503, NOT_SET_UP)
        headers = {"GROCY-API-KEY": self.api_key, "Accept": "application/json"}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        status, raw = self.transport(method, f"{self.url}/api/{path}", payload, headers)
        try:
            data = json.loads(raw) if raw.strip() else None
        except ValueError:
            logger.warning("Grocy returned HTTP %s with a body that isn't JSON", status)
            raise GrocyError(502, UNEXPECTED) from None
        if status >= 400:
            raise error_for(status, data)
        return data

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, body: dict) -> Any:
        return self.request("POST", path, body)

    def delete(self, path: str) -> None:
        self.request("DELETE", path)
