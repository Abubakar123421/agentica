from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import add_audit
from app.database import get_db
from app.dependencies import require_roles
from app.models import Case, Escalation, Evidence, Inspection, Proposal, User
from app.schemas import EscalationCreate, ManufacturerResponseCreate

router = APIRouter(prefix="/escalations", tags=["manufacturer escalations"])


@router.post("/cases/{case_id}", status_code=status.HTTP_201_CREATED)
def create_escalation(
    case_id: str,
    payload: EscalationCreate,
    user: User = Depends(require_roles("importer_investigator")),
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    existing = db.scalar(select(Escalation).where(Escalation.case_id == case.id))
    if existing:
        return {"id": existing.id, "status": existing.status, "idempotent": True}
    proposal = db.scalar(
        select(Proposal)
        .where(
            Proposal.case_id == case.id,
            Proposal.type == "retailer_inspections",
            Proposal.status == "approved",
        )
        .order_by(Proposal.version.desc())
    )
    if not proposal:
        raise HTTPException(status_code=409, detail="An approved batch proposal is required")
    findings = db.scalars(
        select(Inspection).where(
            Inspection.case_id == case.id,
            Inspection.status == "completed",
        )
    ).all()
    if not findings:
        raise HTTPException(status_code=409, detail="At least one retailer finding is required")
    evidence = db.scalars(select(Evidence).where(Evidence.case_id == case.id)).all()
    product = proposal.payload["product"]
    packet = {
        "case_public_id": case.public_id,
        "product": product,
        "batch": proposal.payload["batch"],
        "distribution": proposal.payload.get("retailers", []),
        "findings": [
            {
                "retailer_id": finding.retailer_id,
                "finding": finding.finding,
                "notes": finding.notes,
                "completed_at": (
                    finding.completed_at.isoformat() if finding.completed_at else None
                ),
            }
            for finding in findings
        ],
        "evidence": [
            {
                "id": item.id,
                "filename": item.filename,
                "content_type": item.content_type,
                "sha256": item.sha256,
            }
            for item in evidence
        ],
        "importer_notes": payload.notes,
    }
    escalation = Escalation(
        case_id=case.id,
        manufacturer_id=product["manufacturer"]["id"],
        packet=packet,
        approved_by_user_id=user.id,
    )
    db.add(escalation)
    case.status = "manufacturer_review"
    db.flush()
    add_audit(
        db,
        case.id,
        "manufacturer_escalation_sent",
        user.id,
        {"escalation_id": escalation.id, "manufacturer_id": escalation.manufacturer_id},
    )
    db.commit()
    return {"id": escalation.id, "status": escalation.status, "idempotent": False}


@router.get("")
def escalation_inbox(
    user: User = Depends(require_roles("manufacturer_reviewer")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Escalation)
        .where(Escalation.manufacturer_id == user.organization_id)
        .order_by(Escalation.created_at.desc())
    ).all()
    return [
        {
            "id": item.id,
            "case_id": item.case_id,
            "packet": item.packet,
            "status": item.status,
            "response": item.response,
            "created_at": item.created_at,
            "responded_at": item.responded_at,
        }
        for item in rows
    ]


@router.post("/{escalation_id}/response")
def respond_to_escalation(
    escalation_id: str,
    payload: ManufacturerResponseCreate,
    user: User = Depends(require_roles("manufacturer_reviewer")),
    db: Session = Depends(get_db),
):
    escalation = db.get(Escalation, escalation_id)
    if not escalation or escalation.manufacturer_id != user.organization_id:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if escalation.status == "responded":
        return {"id": escalation.id, "status": escalation.status, "idempotent": True}
    escalation.status = "responded"
    escalation.response = payload.response
    escalation.responded_by_user_id = user.id
    escalation.responded_at = datetime.now(timezone.utc)
    add_audit(
        db,
        escalation.case_id,
        "manufacturer_response_received",
        user.id,
        {"escalation_id": escalation.id},
    )
    db.commit()
    return {"id": escalation.id, "status": escalation.status, "idempotent": False}
