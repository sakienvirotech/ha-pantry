"""Add product brand and stock, and barcodes

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("brand", sa.String(200), nullable=True))
        batch.add_column(
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_check_constraint(
            "ck_products_quantity_non_negative", "quantity >= 0"
        )

    op.create_table(
        "barcodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("ix_barcodes_product_id", "barcodes", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_barcodes_product_id", table_name="barcodes")
    op.drop_table("barcodes")
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("ck_products_quantity_non_negative", type_="check")
        batch.drop_column("quantity")
        batch.drop_column("brand")
