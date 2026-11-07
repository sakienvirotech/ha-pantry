from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .lookup import ProductLookup
from .models import Barcode, Product

router = APIRouter(prefix="/api")

BARCODE_TAKEN = "That barcode is already in use."


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
ProductName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Brand = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
ImageUrl = Annotated[str, StringConstraints(max_length=500, pattern=r"^https://")]
BarcodeValue = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]


class WriteModel(BaseModel):
    # Rejecting unknown fields stops a client from setting quantity on a product.
    model_config = ConfigDict(extra="forbid")


class ProductUpdate(WriteModel):
    name: ProductName
    brand: Brand | None = None
    image_url: ImageUrl | None = None


class ProductCreate(ProductUpdate):
    barcodes: list[BarcodeValue] = []


class BarcodeCreate(WriteModel):
    code: BarcodeValue


class StockChange(WriteModel):
    amount: int = Field(default=1, ge=1, le=9999)


class BarcodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str | None
    quantity: int
    image_url: str | None
    barcodes: list[BarcodeRead]


class LookupMatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    brand: str | None
    image_url: str | None
    source: str
    source_url: str


class LookupResult(BaseModel):
    match: LookupMatch | None
    # A source couldn't be asked, so no match doesn't prove the product is unlisted.
    failed: bool


def get_product_or_404(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found.")
    return product


def commit_barcodes(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, BARCODE_TAKEN) from None


def change_stock(session: Session, product_id: int, delta: int) -> Product:
    # A single conditional UPDATE, so concurrent changes can't lose counts.
    result = session.execute(
        update(Product)
        .where(Product.id == product_id, Product.quantity + delta >= 0)
        .values(quantity=Product.quantity + delta)
    )
    session.commit()
    product = get_product_or_404(session, product_id)
    if result.rowcount == 0:
        raise HTTPException(409, "There isn't enough stock to remove.")
    return product


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/products", response_model=list[ProductRead])
def list_products(session: SessionDep):
    return session.scalars(select(Product).order_by(Product.name)).all()


@router.post("/products", response_model=ProductRead, status_code=201)
def create_product(body: ProductCreate, session: SessionDep):
    product = Product(
        name=body.name,
        brand=body.brand or None,
        image_url=body.image_url,
        barcodes=[Barcode(code=code) for code in dict.fromkeys(body.barcodes)],
    )
    session.add(product)
    commit_barcodes(session)
    return product


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, session: SessionDep):
    return get_product_or_404(session, product_id)


@router.put("/products/{product_id}", response_model=ProductRead)
def update_product(product_id: int, body: ProductUpdate, session: SessionDep):
    product = get_product_or_404(session, product_id)
    product.name = body.name
    product.brand = body.brand or None
    product.image_url = body.image_url
    session.commit()
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, session: SessionDep) -> None:
    session.delete(get_product_or_404(session, product_id))
    session.commit()


@router.post("/products/{product_id}/stock/add", response_model=ProductRead)
def add_stock(
    product_id: int, session: SessionDep, body: StockChange = StockChange()
):
    return change_stock(session, product_id, body.amount)


@router.post("/products/{product_id}/stock/remove", response_model=ProductRead)
def remove_stock(
    product_id: int, session: SessionDep, body: StockChange = StockChange()
):
    return change_stock(session, product_id, -body.amount)


@router.post(
    "/products/{product_id}/barcodes", response_model=ProductRead, status_code=201
)
def add_barcode(product_id: int, body: BarcodeCreate, session: SessionDep):
    product = get_product_or_404(session, product_id)
    product.barcodes.append(Barcode(code=body.code))
    commit_barcodes(session)
    return product


@router.delete(
    "/products/{product_id}/barcodes/{barcode_id}", response_model=ProductRead
)
def remove_barcode(product_id: int, barcode_id: int, session: SessionDep):
    product = get_product_or_404(session, product_id)
    barcode = session.get(Barcode, barcode_id)
    if barcode is None or barcode.product_id != product_id:
        raise HTTPException(404, "Barcode not found.")
    product.barcodes.remove(barcode)
    session.commit()
    return product


# Plain def on purpose: FastAPI runs it in a thread, as lookups wait on the network.
@router.get("/lookup/{code:path}", response_model=LookupResult)
def lookup_barcode(code: str, request: Request):
    lookup: ProductLookup = request.app.state.lookup
    match, failed = lookup.find(code)
    return LookupResult(
        match=LookupMatch.model_validate(match) if match else None, failed=failed
    )


# A :path converter, because Code 128 barcodes can contain slashes.
@router.get("/barcodes/{code:path}", response_model=ProductRead)
def get_product_by_barcode(code: str, session: SessionDep):
    barcode = session.scalar(select(Barcode).where(Barcode.code == code))
    if barcode is None:
        raise HTTPException(404, "Barcode not found.")
    return barcode.product
