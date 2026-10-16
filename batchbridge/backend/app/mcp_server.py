"""Read-only MCP tools used by the BatchBridge investigation workflow."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, or_, select

from app.database import SessionLocal
from app.models import (
    Approval,
    AuditEvent,
    Batch,
    Case,
    Evidence,
    Inspection,
    Organization,
    Product,
    ProductAlias,
    RetailerReview,
    Shipment,
)
from app.services.case_workflow import approved_latest, shipment_plan_current

mcp = FastMCP(
    "BatchBridge Evidence Server",
    instructions="Read-only evidence tools. Returned identifiers must be preserved exactly.",
)


@mcp.tool()
def get_case(case_id: str) -> dict:
    """Get one complaint without reporter contact details."""
    with SessionLocal() as db:
        case = db.get(Case, case_id)
        if not case:
            return {"found": False, "case_id": case_id}
        retailer = db.get(Organization, case.retailer_id) if case.retailer_id else None
        return {
            "found": True,
            "case_id": case.id,
            "public_id": case.public_id,
            "source": case.source,
            "retailer_review": (
                review.decision
                if (
                    review := db.scalar(
                        select(RetailerReview).where(RetailerReview.case_id == case.id)
                    )
                )
                else None
            ),
            "product_name": case.product_name,
            "batch_number": case.batch_number,
            "description": case.description,
            "retailer": (
                {"id": retailer.id, "code": retailer.code, "name": retailer.name}
                if retailer
                else None
            ),
            "status": case.status,
        }


@mcp.tool()
def search_products(query: str) -> list[dict]:
    """Find catalogue products by SKU, name, or known supplier alias."""
    cleaned = query.strip().lower()
    if not cleaned:
        return []
    like = f"%{cleaned}%"
    with SessionLocal() as db:
        rows = db.execute(
            select(Product, Organization)
            .join(Organization, Organization.id == Product.manufacturer_id)
            .outerjoin(ProductAlias, ProductAlias.product_id == Product.id)
            .where(
                or_(
                    func.lower(Product.sku).like(like),
                    func.lower(Product.name).like(like),
                    func.lower(ProductAlias.alias).like(like),
                )
            )
            .distinct()
            .limit(10)
        ).all()
        results = []
        for product, manufacturer in rows:
            aliases = db.scalars(
                select(ProductAlias.alias).where(ProductAlias.product_id == product.id)
            ).all()
            results.append(
                {
                    "id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "aliases": list(aliases),
                    "manufacturer": {
                        "id": manufacturer.id,
                        "code": manufacturer.code,
                        "name": manufacturer.name,
                    },
                }
            )
        return results


@mcp.tool()
def get_batch(product_id: str, batch_number: str) -> dict:
    """Resolve a batch using both product identity and manufacturer lot number."""
    with SessionLocal() as db:
        row = db.execute(
            select(Batch, Product)
            .join(Product, Product.id == Batch.product_id)
            .where(Batch.product_id == product_id, Batch.batch_number == batch_number)
        ).first()
        if not row:
            return {"found": False, "product_id": product_id, "batch_number": batch_number}
        batch, product = row
        shipped = db.scalar(
            select(func.coalesce(func.sum(Shipment.quantity), 0)).where(
                Shipment.batch_id == batch.id
            )
        )
        return {
            "found": True,
            "id": batch.id,
            "product_id": product.id,
            "sku": product.sku,
            "product_name": product.name,
            "batch_number": batch.batch_number,
            "quantity_received": batch.quantity_received,
            "quantity_shipped": int(shipped or 0),
            "quantity_retained": batch.quantity_received - int(shipped or 0),
            "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
        }


@mcp.tool()
def find_related_reports(product_id: str, batch_number: str, exclude_case_id: str) -> list[dict]:
    """Find other reports that deterministically match the same catalogue product and lot."""
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            return []
        names = [product.name.lower()]
        names.extend(
            db.scalars(
                select(ProductAlias.alias).where(ProductAlias.product_id == product_id)
            ).all()
        )
        cases = db.scalars(
            select(Case).where(
                Case.id != exclude_case_id,
                Case.batch_number == batch_number,
                func.lower(Case.product_name).in_([name.lower() for name in names]),
            )
        ).all()
        return [
            {
                "case_id": case.id,
                "public_id": case.public_id,
                "source": case.source,
                "retailer_review": (
                    review.decision
                    if (
                        review := db.scalar(
                            select(RetailerReview).where(RetailerReview.case_id == case.id)
                        )
                    )
                    else None
                ),
                "status": case.status,
                "created_at": case.created_at.isoformat(),
            }
            for case in cases
        ]


@mcp.tool()
def get_batch_shipments(batch_id: str) -> list[dict]:
    """Return exact recipients and quantities from importer shipment records."""
    with SessionLocal() as db:
        rows = db.execute(
            select(Shipment, Organization)
            .join(Organization, Organization.id == Shipment.retailer_id)
            .where(Shipment.batch_id == batch_id)
            .order_by(Organization.code)
        ).all()
        return [
            {
                "shipment_id": shipment.id,
                "shipment_reference": shipment.shipment_reference,
                "retailer_id": retailer.id,
                "retailer_code": retailer.code,
                "retailer_name": retailer.name,
                "quantity": shipment.quantity,
                "shipped_at": shipment.shipped_at.isoformat(),
            }
            for shipment, retailer in rows
        ]


@mcp.tool()
def get_non_recipient_retailers(batch_id: str) -> list[dict]:
    """List retailers excluded because no shipment for the exact batch exists."""
    with SessionLocal() as db:
        recipient_ids = select(Shipment.retailer_id).where(Shipment.batch_id == batch_id)
        retailers = db.scalars(
            select(Organization)
            .where(
                Organization.type == "retailer",
                Organization.id.not_in(recipient_ids),
            )
            .order_by(Organization.code)
        ).all()
        return [
            {
                "retailer_id": retailer.id,
                "retailer_code": retailer.code,
                "retailer_name": retailer.name,
                "reason": "No shipment record exists for this exact product and batch.",
            }
            for retailer in retailers
        ]


@mcp.tool()
def get_inspection_findings(case_id: str) -> list[dict]:
    """Return submitted retailer findings for a case."""
    with SessionLocal() as db:
        rows = db.execute(
            select(Inspection, Organization)
            .join(Organization, Organization.id == Inspection.retailer_id)
            .where(Inspection.case_id == case_id)
            .order_by(Organization.code)
        ).all()
        return [
            {
                "inspection_id": inspection.id,
                "retailer_id": retailer.id,
                "retailer_code": retailer.code,
                "retailer_name": retailer.name,
                "status": inspection.status,
                "finding": inspection.finding,
                "notes": inspection.notes,
                "completed_at": (
                    inspection.completed_at.isoformat() if inspection.completed_at else None
                ),
            }
            for inspection, retailer in rows
        ]


@mcp.tool()
def get_approved_traceability(case_id: str) -> dict:
    """Return the latest human-approved product and batch trace for a case."""
    with SessionLocal() as db:
        case = db.get(Case, case_id)
        proposal = approved_latest(db, case, "traceability") if case else None
        if (
            not proposal
            or not approved_latest(db, case, "triage")
            or not shipment_plan_current(db, case, proposal)
        ):
            return {"found": False, "case_id": case_id}
        approval = db.scalar(select(Approval).where(Approval.proposal_id == proposal.id))
        return {
            "found": True,
            "proposal_id": proposal.id,
            "proposal_version": proposal.version,
            "approved_at": approval.created_at.isoformat(),
            "product": proposal.payload["product"],
            "batch": proposal.payload["batch"],
        }


@mcp.tool()
def get_case_evidence_metadata(case_id: str) -> list[dict]:
    """Return evidence provenance without returning file content or reporter details."""
    with SessionLocal() as db:
        rows = db.scalars(
            select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.created_at)
        ).all()
        return [
            {
                "id": item.id,
                "filename": item.filename,
                "content_type": item.content_type,
                "sha256": item.sha256,
                "source": "staff" if item.uploaded_by_user_id else "customer",
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ]


@mcp.tool()
def get_case_timeline(case_id: str) -> list[dict]:
    """Return event provenance without actor contact details."""
    with SessionLocal() as db:
        rows = db.scalars(
            select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at)
        ).all()
        return [
            {
                "id": item.id,
                "event_type": item.event_type,
                "actor_user_id": item.actor_user_id,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ]


@mcp.tool()
def get_distribution_summary(batch_id: str) -> dict:
    """Calculate received, shipped, retained, and recipient totals for an exact batch."""
    with SessionLocal() as db:
        batch = db.get(Batch, batch_id)
        if not batch:
            return {"found": False, "batch_id": batch_id}
        quantity_shipped, recipient_count = db.execute(
            select(
                func.coalesce(func.sum(Shipment.quantity), 0),
                func.count(func.distinct(Shipment.retailer_id)),
            ).where(Shipment.batch_id == batch_id)
        ).one()
        shipped = int(quantity_shipped or 0)
        return {
            "found": True,
            "batch_id": batch.id,
            "quantity_received": batch.quantity_received,
            "quantity_shipped": shipped,
            "quantity_retained": batch.quantity_received - shipped,
            "recipient_count": int(recipient_count or 0),
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
