from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import add_audit
from app.database import get_db
from app.dependencies import require_roles
from app.models import Case, Escalation, User
from app.schemas import EscalationCreate, ManufacturerResponseCreate
from app.services.manufacturer_report import manufacturer_report_csv

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
    raise HTTPException(
        status_code=409,
        detail="Approve the latest manufacturer proposal through case approvals",
    )


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


@router.get("/{escalation_id}/report.csv")
def download_manufacturer_report(
    escalation_id: str,
    user: User = Depends(require_roles("importer_investigator", "manufacturer_reviewer")),
    db: Session = Depends(get_db),
):
    escalation = db.get(Escalation, escalation_id)
    if not escalation or (
        user.role == "manufacturer_reviewer"
        and escalation.manufacturer_id != user.organization_id
    ):
        raise HTTPException(status_code=404, detail="Escalation not found")
    public_id = str(escalation.packet.get("case_public_id") or escalation.case_id)
    filename = f"Escalera-{public_id}-manufacturer-report.csv"
    return Response(
        content="\ufeff" + manufacturer_report_csv(escalation.packet),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
