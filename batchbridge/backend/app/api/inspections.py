from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import add_audit
from app.database import get_db
from app.dependencies import require_roles
from app.models import Case, Inspection, User
from app.schemas import FindingRequest

router = APIRouter(prefix="/inspections", tags=["retailer inspections"])
retailer_only = require_roles("retailer_safety_manager")


@router.get("")
def inspection_inbox(user: User = Depends(retailer_only), db: Session = Depends(get_db)):
    inspections = db.scalars(
        select(Inspection)
        .where(Inspection.retailer_id == user.organization_id)
        .order_by(Inspection.created_at.desc())
    ).all()
    cases = {
        case.id: case
        for case in db.scalars(
            select(Case).where(Case.id.in_([item.case_id for item in inspections]))
        ).all()
    }
    return [
        {
            "id": item.id,
            "case_id": item.case_id,
            "case_public_id": cases[item.case_id].public_id,
            "product_name": cases[item.case_id].product_name,
            "batch_number": cases[item.case_id].batch_number,
            "status": item.status,
            "finding": item.finding,
            "notes": item.notes,
            "created_at": item.created_at,
            "completed_at": item.completed_at,
        }
        for item in inspections
    ]


@router.post("/{inspection_id}/finding")
def submit_finding(
    inspection_id: str,
    payload: FindingRequest,
    user: User = Depends(retailer_only),
    db: Session = Depends(get_db),
):
    inspection = db.get(Inspection, inspection_id)
    if not inspection or inspection.retailer_id != user.organization_id:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if inspection.status == "completed":
        return {"id": inspection.id, "status": inspection.status, "idempotent": True}
    inspection.status = "completed"
    inspection.finding = payload.finding
    inspection.notes = payload.notes
    inspection.reviewed_by_user_id = user.id
    inspection.completed_at = datetime.now(timezone.utc)
    case = db.get(Case, inspection.case_id)
    if payload.finding == "issue_observed" and case.safety_verdict == "unconfirmed":
        case.safety_verdict = "suspected"
    add_audit(
        db,
        case.id,
        "retailer_finding_submitted",
        user.id,
        {
            "inspection_id": inspection.id,
            "finding": payload.finding,
            "notes": payload.notes,
        },
    )
    db.commit()
    return {"id": inspection.id, "status": inspection.status, "idempotent": False}
