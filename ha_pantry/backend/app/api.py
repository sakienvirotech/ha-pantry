import logging
import re
import secrets
from datetime import date
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .grocy import Grocy, GrocyError, query
from .lookup import ProductLookup
from .pictures import MEDIA_TYPES, PictureError, download_picture, picture_type
from .userfields import (
    UserfieldDef,
    UserfieldValue,
    checked_values,
    product_userfields,
    shown_values,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Grocy's "never overdue" date. Leaving the date out would make stock due today.
NEVER_DUE = date(2999, 12, 31)
SEARCH_LIMIT = 50
PICTURE_WIDTH = 600
PICTURE_FAILED = "The product was created, but its picture couldn't be saved to Grocy."
USERFIELDS_FAILED = "The product was created, but Grocy didn't save {fields}."
# Home Assistant names an App's host after its slug, with dashes for underscores:
# the Grocy App with slug a0d7b954_grocy answers at http://a0d7b954-grocy.
APP_HOST = re.compile(r"(?:[0-9a-f]{8}|local|core)-[a-z0-9-]+")
SIMILAR_LIMIT = 5
# Share of words in common, as a Dice coefficient. 0.5 keeps an exact name with
# an extra word or two, and drops products that only share a word like "syrup".
SIMILAR_THRESHOLD = 0.5


def get_grocy(request: Request) -> Grocy:
    return request.app.state.grocy


GrocyDep = Annotated[Grocy, Depends(get_grocy)]


def get_userfield_names(request: Request) -> list[str]:
    return request.app.state.product_userfields


UserfieldNamesDep = Annotated[list[str], Depends(get_userfield_names)]
ProductName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
UnitName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
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
    # An Open Food Facts picture to save to Grocy as the product's picture.
    image_url: str | None = None
    # Values for the userfields named in the App options, by userfield name.
    userfields: dict[str, str | None] = {}


class UnitCreate(WriteModel):
    name: UnitName


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
    # Grocy's file name, which changes whenever the picture does.
    picture: str | None = None
    # Where the browser can edit the product in Grocy's own UI.
    edit_url: str | None = None
    # The configured userfields that have a value.
    userfields: list[UserfieldValue] = []
    # Set when the main change worked but a lesser part of it didn't.
    warning: str | None = None


class Setup(BaseModel):
    locations: list[Named]
    units: list[Named]
    groups: list[Named]
    default_location_id: int | None
    userfields: list[UserfieldDef]


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


def words(text: str) -> set[str]:
    """Lower-case words, ignoring punctuation, so "Syrup - Woolworths" matches "syrup, Woolworths"."""
    return set(re.findall(r"\w+", text.casefold()))


def similarity(a: set[str], b: set[str]) -> float:
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def active_products(grocy: Grocy) -> list[Named]:
    return named([p for p in grocy.get("objects/products") if p.get("active", 1)])


def grocy_edit_url(grocy_url: str, product_id: int) -> str:
    """The product's page in Grocy, for the browser rather than the backend.

    The Grocy App's own address only works inside Home Assistant, so it links
    to the App's panel instead, which Home Assistant opens through Ingress.
    """
    parts = urlsplit(grocy_url)
    host = parts.hostname or ""
    if APP_HOST.fullmatch(host) and parts.port in (None, 80) and parts.path in ("", "/"):
        return f"/hassio/ingress/{host.replace('-', '_')}/product/{product_id}"
    return f"{grocy_url.rstrip('/')}/product/{product_id}"


def product_view(grocy: Grocy, product_id: int, userfield_names: list[str]) -> ProductView:
    details = grocy.get(f"stock/products/{product_id}")
    product = details["product"]
    group = None
    if product.get("product_group_id"):
        group = grocy.get(f"objects/product_groups/{product['product_group_id']}")["name"]
    userfields = []
    fields = product_userfields(grocy, userfield_names)
    if fields:
        userfields = shown_values(fields, grocy.get(f"userfields/products/{product_id}"))
    return ProductView(
        id=int(product["id"]),
        name=product["name"],
        stock_amount=details.get("stock_amount") or 0,
        unit=(details.get("quantity_unit_stock") or {}).get("name", ""),
        location=(details.get("location") or {}).get("name"),
        group=group,
        picture=product.get("picture_file_name") or None,
        barcodes=[
            BarcodeRead(id=int(row["id"]), code=row["barcode"])
            for row in details.get("product_barcodes") or []
        ],
        edit_url=grocy_edit_url(grocy.url, int(product["id"])),
        userfields=userfields,
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
def setup(grocy: GrocyDep, userfield_names: UserfieldNamesDep):
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
        userfields=product_userfields(grocy, userfield_names),
    )


@router.post("/units", response_model=Named, status_code=201)
def create_unit(body: UnitCreate, grocy: GrocyDep):
    """A unit by name only. Plurals and conversions are set up in Grocy."""
    wanted = body.name.casefold()
    for unit in grocy.get("objects/quantity_units"):
        if str(unit["name"]).strip().casefold() == wanted:
            raise GrocyError(409, f"Grocy already has a unit called {str(unit['name']).strip()}.")
    # These units are pack sizes like "Can - 440g", the same in the plural.
    created = grocy.post(
        "objects/quantity_units", {"name": body.name, "name_plural": body.name}
    )
    return Named(id=int(created["created_object_id"]), name=body.name)


@router.get("/products", response_model=list[Named])
def search_products(grocy: GrocyDep, q: str = ""):
    # Filtered here, so matching ignores case for every alphabet.
    terms = q.casefold().split()
    products = [
        product
        for product in active_products(grocy)
        if all(term in product.name.casefold() for term in terms)
    ]
    return products[:SEARCH_LIMIT]


# Not under /products, where it would clash with /products/{product_id}.
@router.get("/similar-products", response_model=list[Named])
def similar_products(grocy: GrocyDep, name: str):
    """Products whose names share most of their words with a lookup result."""
    wanted = words(name)
    scored = [
        (similarity(wanted, words(product.name)), product)
        for product in active_products(grocy)
    ]
    matches = [(score, p) for score, p in scored if score >= SIMILAR_THRESHOLD]
    matches.sort(key=lambda item: -item[0])
    return [product for _, product in matches[:SIMILAR_LIMIT]]


@router.post("/products", response_model=ProductView, status_code=201)
def create_product(
    body: ProductCreate,
    grocy: GrocyDep,
    request: Request,
    userfield_names: UserfieldNamesDep,
):
    # Checked before anything is created, so a bad value leaves nothing behind.
    fields = product_userfields(grocy, userfield_names)
    userfield_values = checked_values(fields, body.userfields)
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
    warning = None
    if body.image_url:
        try:
            save_picture(grocy, request, product_id, body.image_url)
        except (GrocyError, PictureError) as error:
            # A missing picture isn't worth losing the product over.
            logger.warning("Couldn't save the picture for product %s: %s", product_id, error)
            warning = PICTURE_FAILED
    if userfield_values:
        try:
            grocy.put(f"userfields/products/{product_id}", userfield_values)
        except GrocyError as error:
            logger.warning("Couldn't save userfields for product %s: %s", product_id, error)
            captions = [f.caption for f in fields if f.name in userfield_values]
            failed = USERFIELDS_FAILED.format(fields=" or ".join(captions))
            warning = f"{warning} {failed}" if warning else failed
    view = product_view(grocy, product_id, userfield_names)
    view.warning = warning
    return view


def save_picture(grocy: Grocy, request: Request, product_id: int, url: str) -> None:
    data, extension = download_picture(url, request.app.state.fetch_picture)
    file_name = f"ha-pantry-{product_id}-{secrets.token_hex(4)}.{extension}"
    grocy.upload_picture(file_name, data)
    grocy.put(f"objects/products/{product_id}", {"picture_file_name": file_name})


@router.get("/products/{product_id}/picture")
def get_picture(product_id: int, grocy: GrocyDep):
    file_name = grocy.get(f"objects/products/{product_id}").get("picture_file_name")
    if not file_name:
        raise GrocyError(404, "This product has no picture.")
    data = grocy.download_picture(file_name, PICTURE_WIDTH)
    extension = picture_type(data)
    if extension is None:
        raise GrocyError(502, "Grocy's picture for this product isn't a picture.")
    # The page asks for the picture with its file name, which changes with it.
    return Response(
        data,
        media_type=MEDIA_TYPES[extension],
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.get("/products/{product_id}", response_model=ProductView)
def get_product(product_id: int, grocy: GrocyDep, userfield_names: UserfieldNamesDep):
    return product_view(grocy, product_id, userfield_names)


@router.post("/products/{product_id}/stock/add", response_model=ProductView)
def add_stock(
    product_id: int,
    grocy: GrocyDep,
    userfield_names: UserfieldNamesDep,
    body: StockAdd = StockAdd(),
):
    grocy.post(
        f"stock/products/{product_id}/add",
        {
            "amount": body.amount,
            "best_before_date": (body.best_before_date or NEVER_DUE).isoformat(),
            "transaction_type": "purchase",
        },
    )
    return product_view(grocy, product_id, userfield_names)


@router.post("/products/{product_id}/stock/remove", response_model=ProductView)
def remove_stock(
    product_id: int,
    grocy: GrocyDep,
    userfield_names: UserfieldNamesDep,
    body: StockRemove = StockRemove(),
):
    grocy.post(
        f"stock/products/{product_id}/consume",
        {"amount": body.amount, "transaction_type": "consume", "spoiled": False},
    )
    return product_view(grocy, product_id, userfield_names)


@router.post(
    "/products/{product_id}/barcodes", response_model=ProductView, status_code=201
)
def add_barcode(
    product_id: int, body: BarcodeCreate, grocy: GrocyDep, userfield_names: UserfieldNamesDep
):
    grocy.post(
        "objects/product_barcodes", {"product_id": product_id, "barcode": body.code}
    )
    return product_view(grocy, product_id, userfield_names)


@router.delete(
    "/products/{product_id}/barcodes/{barcode_id}", response_model=ProductView
)
def remove_barcode(
    product_id: int, barcode_id: int, grocy: GrocyDep, userfield_names: UserfieldNamesDep
):
    barcode = grocy.get(f"objects/product_barcodes/{barcode_id}")
    if not barcode or int(barcode["product_id"]) != product_id:
        raise GrocyError(404, "Barcode not found.")
    grocy.delete(f"objects/product_barcodes/{barcode_id}")
    return product_view(grocy, product_id, userfield_names)


# A :path converter, because Code 128 barcodes can contain slashes.
@router.get("/barcodes/{code:path}", response_model=ProductView)
def get_product_by_barcode(code: str, grocy: GrocyDep, userfield_names: UserfieldNamesDep):
    product_id = barcode_owner(grocy, code)
    if product_id is None:
        raise GrocyError(404, "Barcode not found.")
    return product_view(grocy, product_id, userfield_names)


# Plain def on purpose: FastAPI runs it in a thread, as lookups wait on the network.
@router.get("/lookup/{code:path}", response_model=LookupResult)
def lookup_barcode(code: str, request: Request):
    lookup: ProductLookup = request.app.state.lookup
    match, failed = lookup.find(code)
    return LookupResult(
        match=LookupMatch.model_validate(match) if match else None, failed=failed
    )
