import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .grocy import Grocy, GrocyError
from .lookup import ProductLookup
from .pictures import fetch_bytes

logger = logging.getLogger(__name__)

INGRESS_PROXY = "172.30.32.2"
# The Grocy App from the Home Assistant Community Apps repository.
DEFAULT_GROCY_URL = "http://a0d7b954-grocy"
DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def load_options(data_dir: Path) -> dict:
    """Reads the App options, which the Supervisor writes to the data folder."""
    try:
        return json.loads((data_dir / "options.json").read_text())
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        logger.exception("Ignoring unreadable App options")
        return {}


def userfield_names(options: dict) -> list[str]:
    """Product userfields to show, from the App options or, for development, PRODUCT_USERFIELDS."""
    names = options.get("product_userfields")
    if names is None:
        names = os.environ.get("PRODUCT_USERFIELDS", "").split(",")
    seen = []
    for name in names:
        name = str(name).strip()
        if name and name not in seen:
            seen.append(name)
    return seen


def create_app(
    data_dir: Path | None = None,
    allowed_clients: str | None = None,
    static_dir: Path = DEFAULT_STATIC_DIR,
) -> FastAPI:
    data_dir = data_dir or Path(os.environ.get("DATA_DIR", "/data"))
    allowed = allowed_clients or os.environ.get("ALLOWED_CLIENTS", INGRESS_PROXY)
    allowed_hosts = {host.strip() for host in allowed.split(",")}

    app = FastAPI(title="HA-Pantry", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def restrict_clients(request: Request, call_next):
        # Home Assistant authenticates users at the Ingress proxy, so any other
        # client would bypass login. "*" is for local development only.
        client = request.client.host if request.client else None
        if "*" not in allowed_hosts and client not in allowed_hosts:
            return PlainTextResponse("Forbidden", status_code=403)
        return await call_next(request)

    @app.exception_handler(GrocyError)
    async def grocy_error(_request: Request, error: GrocyError):
        return JSONResponse({"detail": error.message}, status_code=error.status)

    options = load_options(data_dir)
    # Environment variables are for local development, outside Home Assistant.
    app.state.grocy = Grocy(
        options.get("grocy_url") or os.environ.get("GROCY_URL", DEFAULT_GROCY_URL),
        options.get("grocy_api_key") or os.environ.get("GROCY_API_KEY", ""),
    )
    app.state.lookup = ProductLookup(
        use_upcitemdb=bool(options.get("upcitemdb_fallback"))
    )
    app.state.fetch_picture = fetch_bytes
    app.state.product_userfields = userfield_names(options)
    app.include_router(router)
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
