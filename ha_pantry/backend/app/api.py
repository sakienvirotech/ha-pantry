from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Product

router = APIRouter(prefix="/api")


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
ProductName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class ProductCreate(BaseModel):
    name: ProductName


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/products", response_model=list[ProductRead])
def list_products(session: SessionDep):
    return session.scalars(select(Product).order_by(Product.name)).all()


@router.post("/products", response_model=ProductRead, status_code=201)
def create_product(body: ProductCreate, session: SessionDep):
    product = Product(name=body.name)
    session.add(product)
    session.commit()
    return product
