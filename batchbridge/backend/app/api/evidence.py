import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import add_audit
from app.config import get_settings
from app.database import get_db
from app.dependencies import current_user
from app.models import Case, Escalation, Evidence, Inspection, User
from app.security import token_hash

router = APIRouter(tags=["evidence"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}


async def _read_evidence(file: UploadFile) -> tuple[str, str, bytes, str]:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Evidence must be JPEG, PNG, or PDF")
    content = await file.read(get_settings().max_evidence_bytes + 1)
    if len(content) > get_settings().max_evidence_bytes:
        raise HTTPException(status_code=413, detail="Evidence exceeds 5 MB")
    if not content:
        raise HTTPException(status_code=422, detail="Evidence file is empty")
    filename = Path(file.filename or "evidence").name[:255]
    return filename, content_type, content, hashlib.sha256(content).hexdigest()


@router.post("/reports/{public_id}/evidence", status_code=status.HTTP_201_CREATED)
async def add_public_evidence(
    public_id: str,
    tracking_token: str = Query(min_length=20),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    case = db.scalar(
        select(Case).where(
            Case.public_id == public_id,
            Case.tracking_token_hash == token_hash(tracking_token),
        )
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    filename, content_type, content, sha256 = await _read_evidence(file)
    evidence = Evidence(
        case_id=case.id,
        filename=filename,
        content_type=content_type,
        content=content,
        sha256=sha256,
    )
    db.add(evidence)
    db.flush()
    add_audit(db, case.id, "evidence_added", details={"evidence_id": evidence.id})
    db.commit()
    return {"id": evidence.id, "filename": evidence.filename, "sha256": evidence.sha256}


def _staff_can_access(db: Session, user: User, case: Case) -> bool:
    if user.role == "importer_investigator":
        return True
    if user.role == "retailer_safety_manager":
        if case.retailer_id == user.organization_id:
            return True
        return bool(
            db.scalar(
                select(Inspection.id).where(
                    Inspection.case_id == case.id,
                    Inspection.retailer_id == user.organization_id,
                )
            )
        )
    if user.role == "manufacturer_reviewer":
        return bool(
            db.scalar(
                select(Escalation.id).where(
                    Escalation.case_id == case.id,
                    Escalation.manufacturer_id == user.organization_id,
                )
            )
        )
    return False


@router.post("/cases/{case_id}/evidence", status_code=status.HTTP_201_CREATED)
async def add_staff_evidence(
    case_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)
    if not case or not _staff_can_access(db, user, case):
        raise HTTPException(status_code=404, detail="Case not found")
    filename, content_type, content, sha256 = await _read_evidence(file)
    evidence = Evidence(
        case_id=case.id,
        filename=filename,
        content_type=content_type,
        content=content,
        sha256=sha256,
        uploaded_by_user_id=user.id,
    )
    db.add(evidence)
    db.flush()
    add_audit(
        db, case.id, "evidence_added", user.id, {"evidence_id": evidence.id, "sha256": sha256}
    )
    db.commit()
    return {"id": evidence.id, "filename": evidence.filename, "sha256": evidence.sha256}


@router.get("/evidence/{evidence_id}")
def download_evidence(
    evidence_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    evidence = db.get(Evidence, evidence_id)
    case = db.get(Case, evidence.case_id) if evidence else None
    if not evidence or not case or not _staff_can_access(db, user, case):
        raise HTTPException(status_code=404, detail="Evidence not found")
    safe_name = evidence.filename.replace('"', "")
    return Response(
        content=evidence.content,
        media_type=evidence.content_type,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )
