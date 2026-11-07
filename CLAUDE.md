# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Backend, from `ha_pantry/backend/`:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest                                 # all tests
.venv/bin/pytest tests/test_app.py::test_health  # single test
DATA_DIR=./data ALLOWED_CLIENTS='*' GROCY_URL=... GROCY_API_KEY=... .venv/bin/uvicorn app.main:create_app --factory --port 8099
```

Tests use `tests/fake_grocy.py`, an in-memory Grocy that copies the real API's behaviour. When the real Grocy behaves differently, change the fake to match.

Frontend, from `ha_pantry/frontend/`: `npm ci`, then `npm run dev` (proxies `/api` to port 8099), `npm run build` (type-checks and bundles), or `npm test` (`npx vitest run src/scanner.test.ts -t "<name>"` for a single test).

Image, from `ha_pantry/`: `docker build -t ha-pantry:test .`

Releases: `.github/workflows/builder.yaml` tests every push and pull request. On `main` it publishes `ghcr.io/sakienvirotech/ha-pantry` for the `version` in `config.yaml`, skipping versions already published, so bump `version` (and `CHANGELOG.md`) for every release and never reuse one. Because `config.yaml` sets `image`, the Supervisor pulls that image instead of building, and installs fail until the workflow has finished. Pushing workflow changes needs a GitHub token with the `workflow` scope.

## Architecture

HA-Pantry ships as a single Home Assistant App (formerly "add-on") for HAOS/Supervised, with its UI in the HA sidebar through Ingress. This repo is also the App repository (`repository.yaml`). Grocy stores all pantry data, and HA-Pantry keeps no database of its own. `ha_pantry/backend` is FastAPI. It talks to Grocy's REST API (`app/grocy.py`) with an API key from the App options, so the key never reaches the browser, and it serves the `ha_pantry/frontend` Preact SPA. Keep all behaviour behind `/api`.

Constraints that are easy to break:

- `backend/` and `frontend/` must stay inside `ha_pantry/`: the Supervisor builds on the device with that folder as the Docker context.
- All frontend URLs must be relative (`api/products`, not `/api/products`), because Ingress serves the app under a dynamic path.
- HA handles login at the Ingress proxy, so the app rejects any client but `172.30.32.2` (`ALLOWED_CLIENTS` overrides this; `*` is for local development only). Uvicorn runs with `--no-proxy-headers` so forwarded headers can't spoof the client address.
- The image uses the HA base image's s6 `/init`, which clears the environment for `CMD` unless `S6_KEEP_ENV=1`, set in the Dockerfile. `init: false` in `config.yaml` is required with these images.
- Grocy returns some errors as raw SQL. `app/grocy.py` turns known ones into plain messages and hides the rest, so add new cases there.
- Grocy rejects a product without `location_id` and all four `qu_id_*` units, and stock added without `best_before_date` becomes due today. HA-Pantry sends `2999-12-31`, Grocy's "never overdue", unless the user picks a date.
- Follow the current HA contributor docs at contributors.home-assistant.io/apps/: `build.yaml` is deprecated and `BUILD_FROM` is no longer passed.

Decisions:

- HA-Pantry only makes it quick to get things into Grocy: scanning, attaching barcodes, creating products and adding or removing stock. Detailed editing, deleting, recipes, expiry tracking and shopping lists stay in Grocy's own UI.
- A new product needs only a name, unit, location and an optional product group. The unit list puts units matching the online pack size first, as units in this household's Grocy are pack sizes such as "Can - 440g". Creating units stays in Grocy.
- A scan opens the product and waits for a tap, so a double scan can't change stock.
- Product lookup is a chain: Open Food Facts, an optional configured fallback, then manual entry. Results only pre-fill the form, and lookup failures must never block manual entry. Names follow the household's "Name - Brand" pattern.
- Scans arrive as keystrokes, detected as a fast burst ending in Enter. They only reach the Ingress iframe when it has focus, so prove changes here with a real scanner.

The standalone version, with its own SQLite database, tags, suppliers and shopping lists, is kept for reference on the `standalone-step-6` branch and in the history up to 0.4.0.

Out of scope for now: companion integration, headless or camera scanning, multiple Grocy instances, product pictures in Grocy.

## Product intent

HA-Pantry is a scanner-first front end for Grocy, as a Home Assistant app. Grocy is powerful, but adding products to it is slow. HA-Pantry makes the common jobs a scan and a tap, and leaves everything else to Grocy.

Core workflow, which should stay the centre of the design:

- The user scans a barcode with a plain Bluetooth or USB scanner, usually on a tablet.
- If Grocy knows the barcode, open the product so stock can be added or removed.
- If not, look it up online and offer two paths: attach the barcode to a product already in Grocy, which is common because many existing products have no barcode yet, or create a new product pre-filled from the lookup.
