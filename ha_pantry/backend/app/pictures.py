"""Downloads product pictures from Open Food Facts, to save them in Grocy.

Only Open Food Facts' image host is allowed, so a client can't use the App to
fetch addresses on the local network.
"""
import logging
from collections.abc import Callable
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .lookup import USER_AGENT

logger = logging.getLogger(__name__)

ALLOWED_HOST = "images.openfoodfacts.org"
MAX_PICTURE_BYTES = 5_000_000
TIMEOUT_SECONDS = 10


class PictureError(Exception):
    pass


def picture_type(data: bytes) -> str | None:
    """The file extension for a picture, read from its first bytes."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None


MEDIA_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}


def is_allowed(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and parts.hostname == ALLOWED_HOST and not parts.port


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read(MAX_PICTURE_BYTES + 1)
    except (URLError, OSError) as error:
        raise PictureError(f"Download failed: {error}") from error


FetchBytes = Callable[[str], bytes]


def download_picture(url: str, fetch: FetchBytes = fetch_bytes) -> tuple[bytes, str]:
    """Returns the picture and its file extension."""
    if not is_allowed(url):
        raise PictureError(f"Pictures can only come from {ALLOWED_HOST}")
    data = fetch(url)
    if len(data) > MAX_PICTURE_BYTES:
        raise PictureError("Picture is too large")
    extension = picture_type(data)
    if extension is None:
        raise PictureError("Download isn't a picture")
    return data, extension
