# ha-pantry

HA-Pantry is a Home Assistant app that makes it quick to get your pantry into [Grocy](https://grocy.info). Grocy does a lot, from stock and shopping lists to recipes, but adding products to it takes many steps. HA-Pantry is a scanner-first front end: plug in a simple Bluetooth or USB barcode scanner and scan.

- If Grocy already knows the barcode, the product opens so you can add or remove stock with a tap.
- If it doesn't, HA-Pantry looks the barcode up online, starting with Open Food Facts, and offers to attach it to a product already in Grocy, or to create a new product with the details filled in.

Everything is stored in Grocy, so recipes, expiry dates, shopping lists and detailed editing all stay there.

## Setup

1. Install Grocy, for example the Grocy App from the Home Assistant Community Apps repository.
2. In Grocy, create an API key under Manage API keys.
3. In Home Assistant, add `https://github.com/sakienvirotech/ha-pantry` as an App repository and install HA-Pantry. Enter the API key in its configuration, and change the Grocy URL if your Grocy isn't the Community App.
4. Optionally, list Grocy product userfields to fill in when creating a product, such as `shelf` or `box`, under "Grocy userfields to fill in". Use each field's name from Grocy's Userfields page, not its caption.

## Tested on

HA-Pantry 0.5.5 was tested in November 2026 on Home Assistant OS on a Raspberry Pi 4 (aarch64), with the Grocy Community App 0.26.5. The amd64 image is built and published, but hasn't been tried on a device yet.

| Area | Result |
|---|---|
| Scanning with a USB scanner on a laptop | Passed. Every code read correctly, including rapid scans |
| Scanning with a Bluetooth scanner on an Android tablet | Passed. The on-screen keyboard stays closed |
| Opening a known product and adding or removing stock | Passed |
| Looking up an unknown barcode, attaching it to an existing product, and creating a new product | Passed |
| Saving Open Food Facts pictures to Grocy | Passed |
| Backing up and restoring HA-Pantry on its own | Passed. Its settings came back unchanged |
| A non-admin Home Assistant user using the panel | Passed |
| Refusing visitors who aren't logged in to Home Assistant | Passed. Direct requests get 403 Forbidden, even with forged forwarding headers, and the panel's address shows Home Assistant's login page |

Things to know:

- HA-Pantry recognises a scan as keystrokes arriving less than 100 ms apart. The Bluetooth scanner tested had gaps of up to 66 ms. A slower scanner's codes would be treated as typing.
- If the tablet's on-screen keyboard is open, a scan types its digits into the text box that has focus.
- HA-Pantry keeps no data of its own, so its backup holds only its settings. Your pantry is in Grocy, so include Grocy in your backups.

## Data sources

Product lookups use [Open Food Facts](https://world.openfoodfacts.org). Its data is available under the [Open Database License](https://opendatacommons.org/licenses/odbl/1.0/), and its product pictures under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). HA-Pantry credits Open Food Facts wherever it shows that data or a picture. Open Food Facts is provided as is, and its accuracy isn't guaranteed: check details before saving them, and don't rely on them for allergies or medical needs. The licence covers only the photo itself, and packaging can show trademarks and designs owned by others.

HA-Pantry makes one lookup per scan and at most 15 a minute, within Open Food Facts' limits for apps. Pictures saved to your Grocy stay in your own database and aren't shared.

An optional fallback, off by default, sends barcodes Open Food Facts doesn't know to [UPCitemdb](https://www.upcitemdb.com), under its [terms of service](https://devs.upcitemdb.com/termsofservice). Its free service allows 100 lookups a day.

## Licence

HA-Pantry is free software under the [GNU General Public License v3.0](LICENSE).
