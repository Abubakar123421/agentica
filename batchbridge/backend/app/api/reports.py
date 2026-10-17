import hashlib
import secrets
from datetime import date

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.evidence import _read_evidence
from app.audit import add_audit
from app.config import get_settings
from app.database import get_db
from app.models import Case, Evidence, Organization
from app.schemas import ReportCreate, ReportCreated, TrackingView
from app.security import token_hash
from app.services.investigation import execute_investigation, queue_investigation

router = APIRouter(tags=["public reports"])


def _public_id() -> str:
    return f"ESC-{secrets.token_hex(5).upper()}"


@router.post("/reports", response_model=ReportCreated, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return _store_report(payload, background_tasks, db)


def _store_report(
    payload: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session,
    photos: list[tuple[str, str, bytes, str]] | None = None,
):
    retailer_id = None
    if payload.retailer_code:
        retailer = db.scalar(
            select(Organization).where(
                Organization.code == payload.retailer_code,
                Organization.type == "retailer",
            )
        )
        if not retailer:
            raise HTTPException(status_code=422, detail="Unknown retailer code")
        retailer_id = retailer.id

    tracking_token = secrets.token_urlsafe(24)
    case = Case(
        public_id=_public_id(),
        tracking_token_hash=token_hash(tracking_token),
        source="customer_photo" if photos else "customer",
        reporter_name=payload.reporter_name,
        reporter_email=str(payload.reporter_email) if payload.reporter_email else None,
        retailer_id=retailer_id,
        product_name=payload.product_name.strip(),
        batch_number=payload.batch_number.strip() if payload.batch_number else None,
        purchase_date=payload.purchase_date,
        description=payload.description.strip(),
    )
    db.add(case)
    db.flush()
    add_audit(db, case.id, "report_created", details={"source": case.source})
    for filename, content_type, content, sha256 in photos or []:
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
    if not photos:
        run, _ = queue_investigation(db, case.id, "triage", None)
        background_tasks.add_task(execute_investigation, run.id)
    db.commit()
    return ReportCreated(
        case_id=case.public_id,
        tracking_token=tracking_token,
        tracking_url=f"{get_settings().app_base_url}/track/{tracking_token}",
        status=case.status,
    )


@router.post("/reports/photo", response_model=ReportCreated, status_code=status.HTTP_201_CREATED)
async def create_photo_report(
    background_tasks: BackgroundTasks,
    retailer_code: str = Form(min_length=1, max_length=40),
    description: str = Form(min_length=10, max_length=5000),
    files: list[UploadFile] = File(...),
    reporter_name: str | None = Form(default=None, max_length=120),
    reporter_email: EmailStr | None = Form(default=None),
    purchase_date: date | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if not 1 <= len(files) <= 3:
        raise HTTPException(status_code=422, detail="Upload between one and three product photos")
    photos = []
    for file in files:
        if file.content_type not in {"image/jpeg", "image/png"}:
            raise HTTPException(status_code=415, detail="Product photos must be JPEG or PNG")
        photos.append(await _read_evidence(file))
    payload = ReportCreate(
        retailer_code=retailer_code,
        description=description,
        reporter_name=reporter_name,
        reporter_email=reporter_email,
        purchase_date=purchase_date,
        product_name="Awaiting officer verification",
    )
    return _store_report(payload, background_tasks, db, photos)


@router.get("/tracking/{tracking_token}", response_model=TrackingView)
def track_report(tracking_token: str, db: Session = Depends(get_db)):
    case = db.scalar(select(Case).where(Case.tracking_token_hash == token_hash(tracking_token)))
    if not case:
        # Burn comparable work for invalid tokens before returning.
        hashlib.sha256(tracking_token.encode()).hexdigest()
        raise HTTPException(status_code=404, detail="Case not found")
    return TrackingView(
        case_id=case.public_id,
        product_name=case.product_name,
        status=case.status,
        safety_verdict=case.safety_verdict,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
