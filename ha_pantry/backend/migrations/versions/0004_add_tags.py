"""Add tags

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100, collation="NOCASE"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.CheckConstraint("kind IN ('category', 'location')", name="ck_tags_kind"),
        sa.UniqueConstraint("name", "kind", name="uq_tags_name_kind"),
    )
    op.create_table(
        "product_tags",
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_product_tags_tag_id", "product_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_product_tags_tag_id", table_name="product_tags")
    op.drop_table("product_tags")
    op.drop_table("tags")
