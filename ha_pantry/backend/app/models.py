from sqlalchemy import CheckConstraint, Column, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


product_tags = Table(
    "product_tags",
    Base.metadata,
    Column(
        "product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_products_quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(default=0, server_default="0")
    image_url: Mapped[str | None] = mapped_column(String(500))

    barcodes: Mapped[list["Barcode"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="Barcode.id",
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary=product_tags,
        back_populates="products",
        passive_deletes=True,
        lazy="selectin",
        order_by="Tag.name",
    )


class Barcode(Base):
    __tablename__ = "barcodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )

    product: Mapped[Product] = relationship(back_populates="barcodes")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint("kind IN ('category', 'location')", name="ck_tags_kind"),
        UniqueConstraint("name", "kind", name="uq_tags_name_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100, collation="NOCASE"))
    kind: Mapped[str] = mapped_column(String(20))

    products: Mapped[list[Product]] = relationship(
        secondary=product_tags, back_populates="tags", passive_deletes=True
    )
