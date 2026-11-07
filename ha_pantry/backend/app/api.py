from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .grocy import Grocy, GrocyError, query
from .lookup import ProductLookup

router = APIRouter(prefix="/api")

# Grocy's "never overdue" date. Leaving the date out would make stock due today.
NEVER_DUE = date(2999, 12, 31)
SEARCH_LIMIT = 50


def get_grocy(request: Request) -> Grocy:
    return request.app.state.grocy


GrocyDep = Annotated[Grocy, Depends(get_grocy)]
ProductName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
BarcodeValue = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]


class WriteModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductCreate(WriteModel):
    name: ProductName
    unit_id: int
    location_id: int
    group_id: int | None = None
    barcode: BarcodeValue | None = None


class BarcodeCreate(WriteModel):
    code: BarcodeValue


class StockAdd(WriteModel):
    amount: int = Field(default=1, ge=1, le=9999)
    best_before_date: date | None = None


class StockRemove(WriteModel):
    amount: int = Field(default=1, ge=1, le=9999)


class Named(BaseModel):
    id: int
    name: str


class BarcodeRead(BaseModel):
    id: int
    code: str


class ProductView(BaseModel):
    id: int
    name: str
    # Whole numbers here, but Grocy allows fractions.
    stock_amount: int | float
    unit: str
    location: str | None
    group: str | None
    barcodes: list[BarcodeRead]


class Setup(BaseModel):
    locations: list[Named]
    units: list[Named]
    groups: list[Named]
    default_location_id: int | None


class Status(BaseModel):
    connected: bool
    message: str | None = None
    grocy_version: str | None = None


class LookupMatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    brand: str | None
    image_url: str | None
    quantity: str | None
    source: str
    source_url: str


class LookupResult(BaseModel):
    match: LookupMatch | None
    # A source couldn't be asked, so no match doesn't prove the product is unlisted.
    failed: bool


def named(rows: list[dict[str, Any]]) -> list[Named]:
    items = [Named(id=int(row["id"]), name=str(row["name"]).strip()) for row in rows]
    return sorted(items, key=lambda item: item.name.casefold())


def product_view(grocy: Grocy, product_id: int) -> ProductView:
    details = grocy.get(f"stock/products/{product_id}")
    product = details["product"]
    group = None
    if product.get("product_group_id"):
        group = grocy.get(f"objects/product_groups/{product['product_group_id']}")["name"]
    return ProductView(
        id=int(product["id"]),
        name=product["name"],
        stock_amount=details.get("stock_amount") or 0,
        unit=(details.get("quantity_unit_stock") or {}).get("name", ""),
        location=(details.get("location") or {}).get("name"),
        group=group,
        barcodes=[
            BarcodeRead(id=int(row["id"]), code=row["barcode"])
            for row in details.get("product_barcodes") or []
        ],
    )


def barcode_owner(grocy: Grocy, code: str) -> int | None:
    rows = grocy.get(f"objects/product_barcodes?{query('barcode', code)}")
    return int(rows[0]["product_id"]) if rows else None


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/status", response_model=Status)
def status(grocy: GrocyDep):
    try:
        info = grocy.get("system/info")
    except GrocyError as error:
        return Status(connected=False, message=error.message)
    version = (info.get("grocy_version") or {}).get("Version")
    return Status(connected=True, grocy_version=version)


@router.get("/setup", response_model=Setup)
def setup(grocy: GrocyDep):
    locations = named(grocy.get("objects/locations"))
    preset = grocy.get("user/settings").get("product_presets_location_id")
    try:
        default_location_id = int(preset)
    except (TypeError, ValueError):
        default_location_id = None
    if default_location_id not in {location.id for location in locations}:
        default_location_id = None
    return Setup(
        locations=locations,
        units=named(grocy.get("objects/quantity_units")),
        groups=named(grocy.get("objects/product_groups")),
        default_location_id=default_location_id,
    )


@router.get("/products", response_model=list[Named])
def search_products(grocy: GrocyDep, q: str = ""):
    # Filtered here, so matching ignores case for every alphabet.
    terms = q.casefold().split()
    products = [
        product
        for product in named([p for p in grocy.get("objects/products") if p.get("active", 1)])
        if all(term in product.name.casefold() for term in terms)
    ]
    return products[:SEARCH_LIMIT]


@router.post("/products", response_model=ProductView, status_code=201)
def create_product(body: ProductCreate, grocy: GrocyDep):
    created = grocy.post(
        "objects/products",
        {
            "name": body.name,
            "location_id": body.location_id,
            "product_group_id": body.group_id,
            "qu_id_purchase": body.unit_id,
            "qu_id_stock": body.unit_id,
            "qu_id_consume": body.unit_id,
            "qu_id_price": body.unit_id,
        },
    )
    product_id = int(created["created_object_id"])
    if body.barcode:
        try:
            grocy.post(
                "objects/product_barcodes",
                {"product_id": product_id, "barcode": body.barcode},
            )
        except GrocyError:
            # Don't leave a product behind that the scan can never find.
            grocy.delete(f"objects/products/{product_id}")
            raise
    return product_view(grocy, product_id)


@router.get("/products/{product_id}", response_model=ProductView)
def get_product(product_id: int, grocy: GrocyDep):
    return product_view(grocy, product_id)


@router.post("/products/{product_id}/stock/add", response_model=ProductView)
def add_stock(product_id: int, grocy: GrocyDep, body: StockAdd = StockAdd()):
    grocy.post(
        f"stock/products/{product_id}/add",
        {
            "amount": body.amount,
            "best_before_date": (body.best_before_date or NEVER_DUE).isoformat(),
            "transaction_type": "purchase",
        },
    )
    return product_view(grocy, product_id)


@router.post("/products/{product_id}/stock/remove", response_model=ProductView)
def remove_stock(product_id: int, grocy: GrocyDep, body: StockRemove = StockRemove()):
    grocy.post(
        f"stock/products/{product_id}/consume",
        {"amount": body.amount, "transaction_type": "consume", "spoiled": False},
    )
    return product_view(grocy, product_id)


@router.post(
    "/products/{product_id}/barcodes", response_model=ProductView, status_code=201
)
def add_barcode(product_id: int, body: BarcodeCreate, grocy: GrocyDep):
    grocy.post(
        "objects/product_barcodes", {"product_id": product_id, "barcode": body.code}
    )
    return product_view(grocy, product_id)


@router.delete(
    "/products/{product_id}/barcodes/{barcode_id}", response_model=ProductView
)
def remove_barcode(product_id: int, barcode_id: int, grocy: GrocyDep):
    barcode = grocy.get(f"objects/product_barcodes/{barcode_id}")
    if not barcode or int(barcode["product_id"]) != product_id:
        raise GrocyError(404, "Barcode not found.")
    grocy.delete(f"objects/product_barcodes/{barcode_id}")
    return product_view(grocy, product_id)


# A :path converter, because Code 128 barcodes can contain slashes.
@router.get("/barcodes/{code:path}", response_model=ProductView)
def get_product_by_barcode(code: str, grocy: GrocyDep):
    product_id = barcode_owner(grocy, code)
    if product_id is None:
        raise GrocyError(404, "Barcode not found.")
    return product_view(grocy, product_id)


# Plain def on purpose: FastAPI runs it in a thread, as lookups wait on the network.
@router.get("/lookup/{code:path}", response_model=LookupResult)
def lookup_barcode(code: str, request: Request):
    lookup: ProductLookup = request.app.state.lookup
    match, failed = lookup.find(code)
    return LookupResult(
        match=LookupMatch.model_validate(match) if match else None, failed=failed
    )
