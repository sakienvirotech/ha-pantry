# Changelog

## 0.6.1

- Fix the Grocy link on a product, which gave a 404 with the Grocy App. Home Assistant now serves App panels at a new address and always opens them at their front page, so the link is now "Open Grocy". A Grocy outside Home Assistant still opens at the product.

## 0.6.0

- On a product, the due date now comes before the stock buttons, as it applies to stock added after it's picked.
- Link from a product to its page in Grocy, to edit or delete it. With the Grocy App, it opens Grocy's panel in Home Assistant.
- Create a unit in Grocy from the new-product form, by name only, and use it straight away.
- Pick up units, locations and groups added in Grocy while HA-Pantry is open, when you switch back to it, or with Reload units.
- Fill in chosen Grocy product userfields, such as a shelf or box, when creating a product, and see them on its page. Name them in the new "Grocy userfields to fill in" setting.

## 0.5.5

- On a new barcode, keep the Grocy product list in a short scrolling box, so the buttons below it stay on screen.

## 0.5.4

- Credit Open Food Facts for lookup data under the Open Database License, and name and link Open Food Facts in picture credits, as its terms ask.
- Credit Open Food Facts for pictures HA-Pantry saved to Grocy, on the product page.
- Link UPCitemdb's terms from its setting.
- HA-Pantry is now licensed under the GNU General Public License v3.0.
- Identify HA-Pantry to Open Food Facts with a contact email, in the form they ask for.

## 0.5.3

- Save the Open Food Facts picture to Grocy when creating a product, unless you untick it. If the picture can't be saved, the product is still created.
- Show a product's Grocy picture on its page.

## 0.5.2

- Install from a prebuilt image instead of building on the device.
- Identify HA-Pantry to Open Food Facts with the project's address.

## 0.5.1

- For an unknown barcode, list Grocy products whose names match the online result, ignoring case and punctuation, so the barcode can be attached with one tap.

## 0.5.0

HA-Pantry is now a front end for Grocy, which stores all data. Products, barcodes, tags and stock from earlier versions are not moved to Grocy.

- Set the Grocy URL and API key in the App's configuration.
- A scanned barcode opens its Grocy product, with buttons to add or remove stock. Added stock is never overdue unless you pick a due date.
- An unknown barcode can be attached to an existing Grocy product, or used to create a new one. The form pre-fills the name in "Name - Brand" form and suggests units matching the pack size.
- Remove tags, search by tag, and the local database. Use Grocy for these.

## 0.4.0

- Add category and location tags, which can be set on a product and renamed or deleted from a new tags page.
- Add search by name, brand, barcode or tag, and filtering by tag.
- Sort the product list without regard to case.

## 0.3.0

- Look up unknown barcodes on Open Food Facts to pre-fill the name, brand and image. Nothing is saved until you confirm, and if the lookup fails you can still enter the details by hand.
- Add an optional UPCitemdb fallback, off by default, in the App's configuration.
- Show a product's image, with attribution, on its page.

## 0.2.0

- Replace the scanner test panel with the scan flow: a known barcode opens its product, and an unknown one offers to add a product or link the barcode to an existing one.
- Add product brand, barcodes, stock add and remove, editing and deleting.
- Pressing Enter in a form no longer saves it, so a scan that lands in a text box can't save the digits.

## 0.1.2

- Raise the scan gap limit to 100 ms, because Bluetooth scanners are slower than USB.

## 0.1.1

- Add a scanner test panel showing focus state, captured barcodes and timing.

## 0.1.0

- Initial walking skeleton: sidebar panel through Ingress, backed by SQLite.
