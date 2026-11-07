"""An in-memory stand-in for the parts of Grocy's API that HA-Pantry uses.

Its behaviour copies what a real Grocy 4.7.1 did in testing, including raw
database errors and stock with no date becoming due today.
"""
import base64
import json
import re
from datetime import date
from urllib.parse import parse_qs, unquote, urlsplit


def sql_error(text):
    return 400, {"error_message": f"SQLSTATE[23000]: Integrity constraint violation: 19 {text}"}


class FakeGrocy:
    def __init__(self):
        self.objects = {
            "locations": {2: {"id": 2, "name": "Fridge"}, 3: {"id": 3, "name": "Pantry"}},
            "quantity_units": {
                2: {"id": 2, "name": "Piece"},
                5: {"id": 5, "name": "Can - 225g"},
            },
            "product_groups": {1: {"id": 1, "name": "Grains"}},
            "products": {},
            "product_barcodes": {},
        }
        self.files = {}  # picture file name -> bytes
        self.stock = {}  # product id -> list of (amount, best_before_date)
        self.settings = {"product_presets_location_id": "3"}
        self.next_id = 100
        self.calls = []
        self.fail_with = None

    def add_product(self, name, barcodes=(), stock=0, group_id=None, active=1):
        status, body = self.create(
            "products",
            {
                "name": name,
                "location_id": 3,
                "product_group_id": group_id,
                "qu_id_stock": 2,
                "active": active,
            },
        )
        product_id = int(body["created_object_id"])
        for code in barcodes:
            self.create("product_barcodes", {"product_id": product_id, "barcode": code})
        if stock:
            self.stock[product_id] = [(stock, "2999-12-31")]
        return product_id

    def create(self, entity, body):
        if entity == "products":
            if body.get("location_id") is None:
                return sql_error("NOT NULL constraint failed: products.location_id")
            if any(p["name"] == body["name"] for p in self.objects["products"].values()):
                return sql_error("UNIQUE constraint failed: products.name")
            body = {"active": 1, **body}
        if entity == "product_barcodes":
            codes = [b["barcode"] for b in self.objects["product_barcodes"].values()]
            if body["barcode"] in codes:
                return sql_error("UNIQUE constraint failed: product_barcodes.barcode")
        self.next_id += 1
        self.objects[entity][self.next_id] = {"id": self.next_id, **body}
        return 200, {"created_object_id": str(self.next_id)}

    def amount(self, product_id):
        return sum(amount for amount, _ in self.stock.get(product_id, []))

    def details(self, product_id):
        product = self.objects["products"].get(product_id)
        if product is None:
            return 400, {"error_message": "Product does not exist or is inactive"}
        unit = self.objects["quantity_units"].get(product.get("qu_id_stock"), {})
        location = self.objects["locations"].get(product["location_id"])
        barcodes = [
            b for b in self.objects["product_barcodes"].values()
            if b["product_id"] == product_id
        ]
        return 200, {
            "product": product,
            "stock_amount": self.amount(product_id),
            "quantity_unit_stock": unit,
            "location": location,
            "product_barcodes": barcodes,
        }

    def __call__(self, method, url, body, headers):
        parts = urlsplit(url)
        path = parts.path.removeprefix("/api/")
        is_json = headers.get("Content-Type") == "application/json"
        payload = json.loads(body) if body and is_json else body
        self.calls.append((method, path, payload))
        if self.fail_with:
            return self.fail_with
        if headers.get("GROCY-API-KEY") != "test-key":
            return 401, b'{"error_message":"Unauthorized"}'
        if m := re.fullmatch(r"files/productpictures/(.+)", path):
            file_name = base64.b64decode(unquote(m[1])).decode()
            if method == "PUT":
                self.files[file_name] = payload
                return 204, b""
            if file_name not in self.files:
                return 404, b'{"error_message":"File not found"}'
            return 200, self.files[file_name]
        status, data = self.route(method, path, parts.query, payload)
        return status, b"" if data is None else json.dumps(data).encode()

    def route(self, method, path, query, payload):
        if path == "system/info":
            return 200, {"grocy_version": {"Version": "4.7.1"}}
        if path == "user/settings":
            return 200, self.settings
        if m := re.fullmatch(r"objects/(\w+)", path):
            entity = m[1]
            if method == "POST":
                return self.create(entity, payload)
            rows = list(self.objects[entity].values())
            for condition in parse_qs(query).get("query[]", []):
                field, value = unquote(condition).split("=", 1)
                rows = [r for r in rows if str(r.get(field)) == value]
            return 200, rows
        if m := re.fullmatch(r"objects/(\w+)/(\d+)", path):
            entity, object_id = m[1], int(m[2])
            row = self.objects[entity].get(object_id)
            if method == "PUT":
                row.update(payload)
                return 204, None
            if method == "DELETE":
                self.objects[entity].pop(object_id, None)
                if entity == "products":
                    self.stock.pop(object_id, None)
                    barcodes = self.objects["product_barcodes"]
                    for key in [k for k, b in barcodes.items() if b["product_id"] == object_id]:
                        del barcodes[key]
                return 204, None
            if row is None:
                return 404, {"error_message": "Object not found"}
            return 200, row
        if m := re.fullmatch(r"stock/products/(\d+)", path):
            return self.details(int(m[1]))
        if m := re.fullmatch(r"stock/products/(\d+)/(add|consume)", path):
            product_id = int(m[1])
            if product_id not in self.objects["products"]:
                return 400, {"error_message": "Product does not exist or is inactive"}
            amount = payload["amount"]
            if m[2] == "add":
                due = payload.get("best_before_date") or date.today().isoformat()
                self.stock.setdefault(product_id, []).append((amount, due))
                return 200, [{"amount": amount, "best_before_date": due}]
            if amount > self.amount(product_id):
                return 400, {
                    "error_message": "Amount to be consumed cannot be > current stock amount"
                }
            self.stock[product_id].append((-amount, None))
            return 200, [{"amount": -amount}]
        return 404, {"error_message": f"Fake Grocy has no route for {method} {path}"}
