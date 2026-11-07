# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Pre-implementation: the repository contains only `README.md`. There is no source code, build tooling, or test setup yet, and no language or framework has been chosen. Add the build, lint, and test commands and the architecture overview here once they exist.

## Product intent

HA-Pantry is a Home Assistant app for barcode-driven home pantry stock and shopping management. It is deliberately narrower in scope than Grocy: favour a simple workflow that needs little setup over configurability.

Core workflow, which should stay the centre of the design:

- The user scans a barcode with a plain Bluetooth or USB scanner.
- If the product is already in the pantry, open its details so stock can be added or removed, or the record edited.
- If the product is unknown, run a web search to identify it, pre-fill as much detail as possible, and let the user add it.

Domain concepts:

- **Tags** categorise products. They cover both product groupings and storage locations.
- **Search** works by tag, barcode, or product name.
- **Stock count** changes only by adding to or removing from the pantry.
- **Minimum stock quantities** drive the shopping list, which can be grouped by product category.
- **Preferred supplier and price** on a product allow a per-supplier shopping list with an estimated total cost.
