"""Add product media, order snapshots and simulated checkout receipts.

Revision ID: 91bb428af032
Revises: e47fda0400ac
"""
from alembic import op
import sqlalchemy as sa

revision = "91bb428af032"
down_revision = "e47fda0400ac"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("sku", sa.String(60), nullable=True))
    op.add_column("products", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("products", sa.Column("image_alt", sa.String(200), nullable=True))
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.add_column("orders", sa.Column("shipping_address", sa.JSON(), nullable=True))
    op.add_column("orders", sa.Column("inventory_reserved", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("order_items", sa.Column("size", sa.String(40), nullable=True))
    op.add_column("order_items", sa.Column("image_url", sa.String(500), nullable=True))
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=True, unique=True),
        sa.Column("reference", sa.String(50), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('approved','declined','refunded')", name="valid_simulated_payment_status"),
        sa.CheckConstraint("amount_cents >= 0", name="nonnegative_payment_amount"),
    )
    op.create_index("ix_payment_attempts_user_id", "payment_attempts", ["user_id"])


def downgrade():
    op.drop_table("payment_attempts")
    op.drop_column("order_items", "image_url")
    op.drop_column("order_items", "size")
    op.drop_column("orders", "inventory_reserved")
    op.drop_column("orders", "shipping_address")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_column("products", "image_alt")
    op.drop_column("products", "image_url")
    op.drop_column("products", "sku")
