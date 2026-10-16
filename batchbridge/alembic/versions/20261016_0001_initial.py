"""Initial BatchBridge schema.

Revision ID: 20261016_0001
Revises:
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261016_0001"
down_revision = None
branch_labels = None
depends_on = None


JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _id() -> sa.Column:
    return sa.Column("id", sa.String(36), primary_key=True, nullable=False)


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)


def _index(table: str, column: str, *, unique: bool = False) -> None:
    op.create_index(f"ix_{table}_{column}", table, [column], unique=unique)


def upgrade() -> None:
    op.create_table(
        "organizations",
        _id(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        _created_at(),
    )
    _index("organizations", "code", unique=True)
    _index("organizations", "type")

    op.create_table(
        "products",
        _id(),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "manufacturer_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        _created_at(),
    )
    _index("products", "manufacturer_id")
    _index("products", "name")
    _index("products", "sku", unique=True)

    op.create_table(
        "users",
        _id(),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        _created_at(),
    )
    _index("users", "email", unique=True)
    _index("users", "organization_id")
    _index("users", "role")

    op.create_table(
        "batches",
        _id(),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("batch_number", sa.String(100), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("product_id", "batch_number", name="uq_product_batch"),
    )
    _index("batches", "batch_number")
    _index("batches", "product_id")

    op.create_table(
        "cases",
        _id(),
        sa.Column("public_id", sa.String(24), nullable=False),
        sa.Column("tracking_token_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("reporter_name", sa.String(120), nullable=True),
        sa.Column("reporter_email", sa.String(255), nullable=True),
        sa.Column(
            "retailer_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("batch_number", sa.String(100), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("safety_verdict", sa.String(40), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        _created_at(),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column, unique in [
        ("batch_number", False),
        ("created_by_user_id", False),
        ("product_name", False),
        ("public_id", True),
        ("retailer_id", False),
        ("safety_verdict", False),
        ("source", False),
        ("status", False),
        ("tracking_token_hash", True),
    ]:
        _index("cases", column, unique=unique)

    op.create_table(
        "product_aliases",
        _id(),
        sa.Column(
            "product_id",
            sa.String(36),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(200), nullable=False),
        sa.UniqueConstraint("product_id", "alias", name="uq_product_alias"),
    )
    _index("product_aliases", "alias")
    _index("product_aliases", "product_id")

    op.create_table(
        "user_sessions",
        _id(),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        _created_at(),
    )
    _index("user_sessions", "expires_at")
    _index("user_sessions", "token_hash", unique=True)
    _index("user_sessions", "user_id")

    op.create_table(
        "agent_runs",
        _id(),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("thread_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("result", JSON_TYPE, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        _created_at(),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    _index("agent_runs", "case_id")
    _index("agent_runs", "status")
    _index("agent_runs", "thread_id", unique=True)

    op.create_table(
        "audit_events",
        _id(),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("details", JSON_TYPE, nullable=False),
        _created_at(),
    )
    _index("audit_events", "case_id")
    _index("audit_events", "created_at")
    _index("audit_events", "event_type")

    op.create_table(
        "escalations",
        _id(),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column(
            "manufacturer_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("packet", JSON_TYPE, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column(
            "approved_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column(
            "responded_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        _created_at(),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    _index("escalations", "case_id", unique=True)
    _index("escalations", "manufacturer_id")
    _index("escalations", "status")

    op.create_table(
        "evidence",
        _id(),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "uploaded_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        _created_at(),
    )
    _index("evidence", "case_id")
    _index("evidence", "sha256")

    op.create_table(
        "inspections",
        _id(),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column(
            "retailer_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("finding", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        _created_at(),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("case_id", "retailer_id", name="uq_case_retailer_inspection"),
    )
    _index("inspections", "case_id")
    _index("inspections", "retailer_id")
    _index("inspections", "status")

    op.create_table(
        "retailer_reviews",
        _id(),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column(
            "retailer_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        _created_at(),
        sa.UniqueConstraint("case_id", "retailer_id", name="uq_case_retailer_review"),
    )
    _index("retailer_reviews", "case_id")
    _index("retailer_reviews", "retailer_id")
    _index("retailer_reviews", "reviewer_id")

    op.create_table(
        "shipments",
        _id(),
        sa.Column("shipment_reference", sa.String(100), nullable=False),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("batches.id"), nullable=False),
        sa.Column(
            "retailer_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=False),
    )
    _index("shipments", "batch_id")
    _index("shipments", "retailer_id")
    _index("shipments", "shipment_reference", unique=True)
    _index("shipments", "shipped_at")

    op.create_table(
        "proposals",
        _id(),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column(
            "agent_run_id",
            sa.String(36),
            sa.ForeignKey("agent_runs.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("payload", JSON_TYPE, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        _created_at(),
        sa.UniqueConstraint("case_id", "version", name="uq_case_proposal_version"),
    )
    _index("proposals", "case_id")
    _index("proposals", "status")

    op.create_table(
        "approvals",
        _id(),
        sa.Column(
            "proposal_id",
            sa.String(36),
            sa.ForeignKey("proposals.id"),
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        _created_at(),
    )
    _index("approvals", "proposal_id", unique=True)
    _index("approvals", "reviewer_id")


def downgrade() -> None:
    for table in [
        "approvals",
        "proposals",
        "shipments",
        "retailer_reviews",
        "inspections",
        "evidence",
        "escalations",
        "audit_events",
        "agent_runs",
        "user_sessions",
        "product_aliases",
        "cases",
        "batches",
        "users",
        "products",
        "organizations",
    ]:
        op.drop_table(table)
