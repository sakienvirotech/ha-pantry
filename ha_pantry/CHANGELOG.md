# Changelog

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
