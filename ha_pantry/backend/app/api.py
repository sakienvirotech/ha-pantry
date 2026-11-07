from collections.abc import Iterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import collate, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .lookup import ProductLookup
from .models import Barcode, Product, Tag, product_tags

router = APIRouter(prefix="/api")

BARCODE_TAKEN = "That barcode is already in use."
TAG_TAKEN = "That tag already exists."


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


TagName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
TagKind = Literal["category", "location"]


class WriteModel(BaseModel):
    # Rejecting unknown fields stops a client from setting quantity on a product.
    model_config = ConfigDict(extra="forbid")


class ProductUpdate(WriteModel):
    name: ProductName
    brand: Brand | None = None
    image_url: ImageUrl | None = None
    tag_ids: list[int] = []


class ProductCreate(ProductUpdate):
    barcodes: list[BarcodeValue] = []


class BarcodeCreate(WriteModel):
    code: BarcodeValue


class TagUpdate(WriteModel):
    name: TagName


class TagCreate(TagUpdate):
    kind: TagKind


class StockChange(WriteModel):
    amount: int = Field(default=1, ge=1, le=9999)


class BarcodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: TagKind


class TagSummary(TagRead):
    product_count: int


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str | None
    quantity: int
    image_url: str | None
    barcodes: list[BarcodeRead]
    tags: list[TagRead]


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


def commit_unique(session: Session, conflict: str) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, conflict) from None


def get_tag_or_404(session: Session, tag_id: int) -> Tag:
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(404, "Tag not found.")
    return tag


def load_tags(session: Session, tag_ids: list[int]) -> list[Tag]:
    unique_ids = set(tag_ids)
    tags = session.scalars(select(Tag).where(Tag.id.in_(unique_ids))).all()
    if len(tags) != len(unique_ids):
        raise HTTPException(422, "That tag no longer exists.")
    return list(tags)


def matches_term(term: str):
    """One search word can match a product's name, brand, barcode or tag."""
    return or_(
        Product.name.icontains(term, autoescape=True),
        Product.brand.icontains(term, autoescape=True),
        Product.barcodes.any(Barcode.code.icontains(term, autoescape=True)),
        Product.tags.any(Tag.name.icontains(term, autoescape=True)),
    )


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
def list_products(
    session: SessionDep,
    q: str = "",
    tag: Annotated[list[int], Query()] = [],
):
    query = select(Product).order_by(collate(Product.name, "NOCASE"))
    for term in q.split():
        query = query.where(matches_term(term))
    for tag_id in tag:
        query = query.where(Product.tags.any(Tag.id == tag_id))
    return session.scalars(query).all()


@router.post("/products", response_model=ProductRead, status_code=201)
def create_product(body: ProductCreate, session: SessionDep):
    product = Product(
        name=body.name,
        brand=body.brand or None,
        image_url=body.image_url,
        barcodes=[Barcode(code=code) for code in dict.fromkeys(body.barcodes)],
        tags=load_tags(session, body.tag_ids),
    )
    session.add(product)
    commit_unique(session, BARCODE_TAKEN)
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
    product.tags = load_tags(session, body.tag_ids)
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
    commit_unique(session, BARCODE_TAKEN)
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


@router.get("/tags", response_model=list[TagSummary])
def list_tags(session: SessionDep):
    rows = session.execute(
        select(Tag, func.count(product_tags.c.product_id))
        .outerjoin(product_tags)
        .group_by(Tag.id)
        .order_by(Tag.kind, Tag.name)
    )
    return [
        TagSummary(id=tag.id, name=tag.name, kind=tag.kind, product_count=count)
        for tag, count in rows
    ]


@router.post("/tags", response_model=TagRead, status_code=201)
def create_tag(body: TagCreate, session: SessionDep):
    tag = Tag(name=body.name, kind=body.kind)
    session.add(tag)
    commit_unique(session, TAG_TAKEN)
    return tag


@router.put("/tags/{tag_id}", response_model=TagRead)
def rename_tag(tag_id: int, body: TagUpdate, session: SessionDep):
    tag = get_tag_or_404(session, tag_id)
    tag.name = body.name
    commit_unique(session, TAG_TAKEN)
    return tag


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: int, session: SessionDep) -> None:
    session.delete(get_tag_or_404(session, tag_id))
    session.commit()


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
