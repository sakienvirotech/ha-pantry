# ha-pantry

HA-Pantry is a Home Assistant app that makes it quick to get your pantry into [Grocy](https://grocy.info). Grocy does a lot, from stock and shopping lists to recipes, but adding products to it takes many steps. HA-Pantry is a scanner-first front end: plug in a simple Bluetooth or USB barcode scanner and scan.

- If Grocy already knows the barcode, the product opens so you can add or remove stock with a tap.
- If it doesn't, HA-Pantry looks the barcode up online, starting with Open Food Facts, and offers to attach it to a product already in Grocy, or to create a new product with the details filled in.

Everything is stored in Grocy, so recipes, expiry dates, shopping lists and detailed editing all stay there.

## Setup

1. Install Grocy, for example the Grocy App from the Home Assistant Community Apps repository.
2. In Grocy, create an API key under Manage API keys.
3. Install HA-Pantry from this repository, enter the API key in its configuration, and change the Grocy URL if your Grocy isn't the Community App.
