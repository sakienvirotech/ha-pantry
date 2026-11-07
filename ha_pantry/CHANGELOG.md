# Changelog

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
