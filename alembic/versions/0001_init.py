"""initial schema

Revision ID: 0001_init
Revises: 
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    account_status = sa.Enum("AVAILABLE", "RENTED", "EXPIRED", "DISABLED", name="accountstatus")
    order_status = sa.Enum(
        "PENDING_PHOTO",
        "PHOTO_APPROVED",
        "PHOTO_REJECTED",
        "CREDS_SENT",
        "ACTIVE",
        "COMPLETED",
        "CANCELLED",
        name="orderstatus",
    )
    account_status.create(op.get_bind(), checkfirst=True)
    order_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("funpay_order_id", sa.String(length=64), nullable=False),
        sa.Column("funpay_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("buyer_nickname", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("rental_minutes", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", order_status, nullable=False),
        sa.Column("review_added", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("extra_time_given", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_bonus_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("photo_file_id", sa.String(length=255), nullable=True),
        sa.Column("photo_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_orders_funpay_order_id"), "orders", ["funpay_order_id"], unique=True)
    op.create_index(op.f("ix_orders_funpay_chat_id"), "orders", ["funpay_chat_id"], unique=False)
    op.create_index(op.f("ix_orders_buyer_nickname"), "orders", ["buyer_nickname"], unique=False)

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("steam_login", sa.String(length=255), nullable=False),
        sa.Column("steam_password_encrypted", sa.Text(), nullable=False),
        sa.Column("faceit_login", sa.String(length=255), nullable=True),
        sa.Column("faceit_password_encrypted", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("email_password_encrypted", sa.Text(), nullable=False),
        sa.Column("email_imap_host", sa.String(length=255), nullable=False),
        sa.Column("email_imap_port", sa.Integer(), nullable=False),
        sa.Column("status", account_status, nullable=False),
        sa.Column("current_order_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["current_order_id"], ["orders.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_accounts_title"), "accounts", ["title"], unique=True)
    op.create_index(op.f("ix_accounts_steam_login"), "accounts", ["steam_login"], unique=True)
    op.create_index(op.f("ix_accounts_email"), "accounts", ["email"], unique=False)
    op.create_index(op.f("ix_accounts_status"), "accounts", ["status"], unique=False)

    op.create_foreign_key("fk_orders_account_id_accounts", "orders", "accounts", ["account_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "order_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_order_logs_order_id"), "order_logs", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_logs_source"), "order_logs", ["source"], unique=False)
    op.create_index(op.f("ix_order_logs_action"), "order_logs", ["action"], unique=False)


def downgrade() -> None:
    op.drop_table("order_logs")
    op.drop_table("accounts")
    op.drop_table("orders")
    sa.Enum(name="orderstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="accountstatus").drop(op.get_bind(), checkfirst=True)