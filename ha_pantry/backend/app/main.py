import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .db import create_db_engine, run_migrations

INGRESS_PROXY = "172.30.32.2"
DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def create_app(
    data_dir: Path | None = None,
    allowed_clients: str | None = None,
    static_dir: Path = DEFAULT_STATIC_DIR,
) -> FastAPI:
    data_dir = data_dir or Path(os.environ.get("DATA_DIR", "/data"))
    allowed = allowed_clients or os.environ.get("ALLOWED_CLIENTS", INGRESS_PROXY)
    allowed_hosts = {host.strip() for host in allowed.split(",")}

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = create_db_engine(data_dir)
        run_migrations(app.state.engine)
        yield
        app.state.engine.dispose()

    app = FastAPI(title="HA-Pantry", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def restrict_clients(request: Request, call_next):
        # Home Assistant authenticates users at the Ingress proxy, so any other
        # client would bypass login. "*" is for local development only.
        client = request.client.host if request.client else None
        if "*" not in allowed_hosts and client not in allowed_hosts:
            return PlainTextResponse("Forbidden", status_code=403)
        return await call_next(request)

    app.include_router(router)
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
