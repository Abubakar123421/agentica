import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(30), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(40), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    manufacturer_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProductAlias(Base):
    __tablename__ = "product_aliases"
    __table_args__ = (UniqueConstraint("product_id", "alias", name="uq_product_alias"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(200), index=True)


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (UniqueConstraint("product_id", "batch_number", name="uq_product_batch"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    batch_number: Mapped[str] = mapped_column(String(100), index=True)
    quantity_received: Mapped[int] = mapped_column(Integer)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    shipment_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), index=True)
    retailer_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    shipped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    public_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    tracking_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(30), index=True)
    reporter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reporter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retailer_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    product_name: Mapped[str] = mapped_column(String(200), index=True)
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="new_report", index=True)
    safety_verdict: Mapped[str] = mapped_column(String(40), default="unconfirmed", index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    uploaded_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    thread_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (UniqueConstraint("case_id", "version", name="uq_case_proposal_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), unique=True, index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    decision: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetailerReview(Base):
    __tablename__ = "retailer_reviews"
    __table_args__ = (UniqueConstraint("case_id", "retailer_id", name="uq_case_retailer_review"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    retailer_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    decision: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Inspection(Base):
    __tablename__ = "inspections"
    __table_args__ = (
        UniqueConstraint("case_id", "retailer_id", name="uq_case_retailer_inspection"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    retailer_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    assigned_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    finding: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), unique=True, index=True)
    manufacturer_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    packet: Mapped[dict[str, Any]] = mapped_column(JsonType)
    status: Mapped[str] = mapped_column(String(30), default="sent", index=True)
    approved_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
