# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Backend, from `ha_pantry/backend/`:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest                                 # all tests
.venv/bin/pytest tests/test_app.py::test_health  # single test
DATA_DIR=./data ALLOWED_CLIENTS='*' .venv/bin/uvicorn app.main:create_app --factory --port 8099
```

Frontend, from `ha_pantry/frontend/`: `npm ci`, then `npm run dev` (proxies `/api` to port 8099), `npm run build` (type-checks and bundles), or `npm test` (`npx vitest run src/scanner.test.ts -t "<name>"` for a single test).

Image, from `ha_pantry/`: `docker build -t ha-pantry:test .`

## Architecture

HA-Pantry ships as a single Home Assistant App (formerly "add-on") for HAOS/Supervised, with its UI in the HA sidebar through Ingress. This repo is also the App repository (`repository.yaml`). `ha_pantry/backend` is FastAPI, SQLAlchemy and Alembic on SQLite at `/data/pantry.db`, and it serves the `ha_pantry/frontend` Preact SPA. The SPA uses the same JSON API a future companion integration would use, so keep all behaviour behind `/api`.

Constraints that are easy to break:

- `backend/` and `frontend/` must stay inside `ha_pantry/`: the Supervisor builds on the device with that folder as the Docker context.
- All frontend URLs must be relative (`api/products`, not `/api/products`), because Ingress serves the app under a dynamic path.
- HA handles login at the Ingress proxy, so the app rejects any client but `172.30.32.2` (`ALLOWED_CLIENTS` overrides this; `*` is for local development only). Uvicorn runs with `--no-proxy-headers` so forwarded headers can't spoof the client address.
- The image uses the HA base image's s6 `/init`, which clears the environment for `CMD` unless `S6_KEEP_ENV=1`, set in the Dockerfile. `init: false` in `config.yaml` is required with these images.
- Migrations run on startup. Every schema change needs an Alembic revision in `backend/migrations/versions/`.
- Follow the current HA contributor docs at contributors.home-assistant.io/apps/: `build.yaml` is deprecated and `BUILD_FROM` is no longer passed.

Decisions for upcoming work:

- Stock is a whole number that changes only through explicit add and remove API actions, and can't go below zero.
- Each tag has a kind, either category or location. Shopping lists group by category tags.
- One product can have several barcodes, so barcodes get their own table.
- Product lookup is a chain: Open Food Facts, an optional configured fallback, then manual entry. Results only pre-fill the form, and lookup failures must never block manual entry.
- The shopping list is a query, not stored data. Items with no price are flagged rather than counted as zero.
- Scans arrive as keystrokes, detected as a fast burst ending in Enter. They only reach the Ingress iframe when it has focus, so prove changes here with a real scanner.

Out of scope for now: companion integration, headless or camera scanning, stock history, expiry dates, multiple pantries.

## Long-term goal: Grocy export and import

Exchanging data with Grocy, in both directions, is planned but not scheduled for the first few releases. Don't build it yet, but don't make design choices that would rule it out. In particular, it lets people move to or from HA-Pantry without re-entering their pantry.

Keep these in mind when changing the data model:

- Barcodes are the natural key for matching products between the two systems, so keep them in their own table and don't assume they are unique to one source.
- Tag kinds map to Grocy's separate concepts for categories and storage locations, so keep every tag's kind accurate.
- Grocy models things HA-Pantry deliberately doesn't, such as quantity units and expiry dates. Decide what happens to that data on import, and don't lose it silently: report what was skipped.
- Stock is deliberately whole numbers, but Grocy quantities may not be. An import should round or flag fractional amounts, and report them.
- Keep import and export behind the API like everything else, and confirm Grocy's current API and data model when this work starts.

## Product intent

HA-Pantry is a Home Assistant app for barcode-driven home pantry stock and shopping management. It is deliberately narrower in scope than Grocy: favour a simple workflow that needs little setup over configurability.

Core workflow, which should stay the centre of the design:

- The user scans a barcode with a plain Bluetooth or USB scanner.
- If the product is already in the pantry, open its details so stock can be added or removed, or the record edited.
- If the product is unknown, run a web search to identify it, pre-fill as much detail as possible, and let the user add it.

Domain concepts:

- **Tags** categorise products. Each is either a product category or a storage location.
- **Search** works by tag, barcode, or product name.
- **Stock count** changes only by adding to or removing from the pantry.
- **Minimum stock quantities** drive the shopping list, which can be grouped by product category.
- **Preferred supplier and price** on a product allow a per-supplier shopping list with an estimated total cost.
