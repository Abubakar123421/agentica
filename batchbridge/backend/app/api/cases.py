import asyncio
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.audit import add_audit
from app.database import get_db
from app.dependencies import current_user, require_roles
from app.models import (
    AgentRun,
    Approval,
    AuditEvent,
    Case,
    Escalation,
    Inspection,
    Proposal,
    RetailerReview,
    User,
)
from app.schemas import (
    AnalysisStartResponse,
    ApprovalRequest,
    CaseSummary,
    OfficerReportCreate,
    RetailerReviewRequest,
    StatusUpdate,
)
from app.security import token_hash
from app.services.investigation import (
    execute_investigation,
    queue_investigation,
    resume_investigation,
)

router = APIRouter(prefix="/cases", tags=["cases"])


def _can_view_case(db: Session, user: User, case: Case) -> bool:
    if user.role == "importer_investigator":
        return True
    if user.role == "retailer_safety_manager":
        return case.retailer_id == user.organization_id or bool(
            db.scalar(
                select(
                    exists().where(
                        Inspection.case_id == case.id,
                        Inspection.retailer_id == user.organization_id,
                    )
                )
            )
        )
    return False


def _get_authorized_case(db: Session, user: User, case_id: str) -> Case:
    case = db.get(Case, case_id)
    if not case or not _can_view_case(db, user, case):
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("", response_model=list[CaseSummary])
def list_cases(user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Case).order_by(Case.created_at.desc())
    if user.role == "retailer_safety_manager":
        assigned_case_ids = select(Inspection.case_id).where(
            Inspection.retailer_id == user.organization_id
        )
        query = query.where(
            (Case.retailer_id == user.organization_id) | Case.id.in_(assigned_case_ids)
        )
    elif user.role != "importer_investigator":
        raise HTTPException(status_code=403, detail="Role not permitted")
    return db.scalars(query).all()


@router.post("/officer-report", response_model=CaseSummary, status_code=status.HTTP_201_CREATED)
def create_officer_report(
    payload: OfficerReportCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_roles("retailer_safety_manager")),
    db: Session = Depends(get_db),
):
    raw_tracking = secrets.token_urlsafe(24)
    case = Case(
        public_id=f"BB-{secrets.token_hex(5).upper()}",
        tracking_token_hash=token_hash(raw_tracking),
        source="retailer_officer",
        retailer_id=user.organization_id,
        product_name=payload.product_name.strip(),
        batch_number=payload.batch_number.strip() if payload.batch_number else None,
        purchase_date=payload.purchase_date,
        description=payload.description.strip(),
        created_by_user_id=user.id,
    )
    db.add(case)
    db.flush()
    add_audit(db, case.id, "report_created", user.id, {"source": "retailer_officer"})
    run, _ = queue_investigation(db, case.id, "triage", user.id)
    db.commit()
    background_tasks.add_task(execute_investigation, run.id)
    return case


@router.get("/{case_id}")
def case_detail(case_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    case = _get_authorized_case(db, user, case_id)
    proposals = db.scalars(
        select(Proposal).where(Proposal.case_id == case.id).order_by(Proposal.version.desc())
    ).all()
    inspections = db.scalars(
        select(Inspection).where(Inspection.case_id == case.id).order_by(Inspection.created_at)
    ).all()
    timeline = db.scalars(
        select(AuditEvent).where(AuditEvent.case_id == case.id).order_by(AuditEvent.created_at)
    ).all()
    agent_runs = db.scalars(
        select(AgentRun).where(AgentRun.case_id == case.id).order_by(AgentRun.created_at)
    ).all()
    result = {
        "case": CaseSummary.model_validate(case).model_dump(mode="json"),
        "description": case.description,
        "purchase_date": case.purchase_date,
        "proposals": [
            {
                "id": item.id,
                "type": item.type,
                "payload": item.payload,
                "status": item.status,
                "version": item.version,
                "created_at": item.created_at,
            }
            for item in proposals
        ],
        "inspections": [
            {
                "id": item.id,
                "retailer_id": item.retailer_id,
                "status": item.status,
                "finding": item.finding,
                "notes": item.notes,
                "created_at": item.created_at,
                "completed_at": item.completed_at,
            }
            for item in inspections
        ],
        "timeline": [
            {
                "id": item.id,
                "event_type": item.event_type,
                "actor_user_id": item.actor_user_id,
                "details": item.details,
                "created_at": item.created_at,
            }
            for item in timeline
        ],
        "agent_runs": [
            {
                "id": item.id,
                "agent_type": item.agent_type,
                "status": item.status,
                "result": item.result,
                "error": item.error,
                "created_at": item.created_at,
                "completed_at": item.completed_at,
            }
            for item in agent_runs
        ],
    }
    if user.role == "importer_investigator":
        result["reporter"] = {"name": case.reporter_name, "email": case.reporter_email}
    return result


@router.post("/{case_id}/retailer-review")
def review_customer_case(
    case_id: str,
    payload: RetailerReviewRequest,
    user: User = Depends(require_roles("retailer_safety_manager")),
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)
    if not case or case.retailer_id != user.organization_id:
        raise HTTPException(status_code=404, detail="Case not found")
    existing = db.scalar(
        select(RetailerReview).where(
            RetailerReview.case_id == case.id,
            RetailerReview.retailer_id == user.organization_id,
        )
    )
    if existing:
        return {
            "id": existing.id,
            "decision": existing.decision,
            "idempotent": True,
        }
    review = RetailerReview(
        case_id=case.id,
        retailer_id=user.organization_id,
        reviewer_id=user.id,
        decision=payload.decision,
        notes=payload.notes,
    )
    db.add(review)
    if payload.decision == "forwarded":
        case.status = "under_review"
    elif payload.decision == "needs_customer_information":
        case.status = "waiting_for_information"
    db.flush()
    triage_proposal = db.scalar(
        select(Proposal)
        .join(AgentRun, AgentRun.id == Proposal.agent_run_id)
        .where(
            Proposal.case_id == case.id,
            Proposal.status == "pending",
            AgentRun.agent_type == "triage",
        )
        .order_by(Proposal.version.desc())
    )
    if triage_proposal and not db.scalar(
        select(Approval).where(Approval.proposal_id == triage_proposal.id)
    ):
        triage_decision = "approved" if payload.decision == "forwarded" else "changes_requested"
        db.add(
            Approval(
                proposal_id=triage_proposal.id,
                reviewer_id=user.id,
                decision=triage_decision,
                notes=payload.notes,
            )
        )
        triage_proposal.status = triage_decision
        triage_run = db.get(AgentRun, triage_proposal.agent_run_id)
        triage_run.status = "completed"
    add_audit(
        db,
        case.id,
        "retailer_review_submitted",
        user.id,
        {
            "review_id": review.id,
            "decision": review.decision,
            "notes": review.notes,
            "forwarded_to_importer": review.decision == "forwarded",
        },
    )
    db.commit()
    return {"id": review.id, "decision": review.decision, "idempotent": False}


@router.patch("/{case_id}/status", response_model=CaseSummary)
def update_case_status(
    case_id: str,
    payload: StatusUpdate,
    user: User = Depends(require_roles("importer_investigator")),
    db: Session = Depends(get_db),
):
    case = _get_authorized_case(db, user, case_id)
    old_status = case.status
    case.status = payload.status
    if payload.safety_verdict:
        case.safety_verdict = payload.safety_verdict
    add_audit(
        db,
        case.id,
        "case_status_changed",
        user.id,
        {"from": old_status, "to": case.status, "safety_verdict": case.safety_verdict},
    )
    db.commit()
    return case


async def _start_agent(
    db: Session,
    case: Case,
    agent_type: str,
    user: User,
) -> AnalysisStartResponse:
    run, created = queue_investigation(db, case.id, agent_type, user.id)
    if agent_type == "traceability":
        case.status = "under_review"
    db.commit()
    if created:
        asyncio.create_task(execute_investigation(run.id))
    return AnalysisStartResponse(run_id=run.id, status=run.status, agent_type=agent_type)


@router.post("/{case_id}/triage", response_model=AnalysisStartResponse, status_code=202)
async def start_triage(
    case_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    case = _get_authorized_case(db, user, case_id)
    if user.role not in {"retailer_safety_manager", "importer_investigator"}:
        raise HTTPException(status_code=403, detail="Role not permitted")
    return await _start_agent(db, case, "triage", user)


@router.post("/{case_id}/analysis", response_model=AnalysisStartResponse, status_code=202)
async def start_analysis(
    case_id: str,
    user: User = Depends(require_roles("importer_investigator")),
    db: Session = Depends(get_db),
):
    case = _get_authorized_case(db, user, case_id)
    retailer_forwarded = db.scalar(
        select(RetailerReview.id).where(
            RetailerReview.case_id == case.id,
            RetailerReview.decision == "forwarded",
        )
    )
    approved_triage = db.scalar(
        select(Proposal.id)
        .join(AgentRun, AgentRun.id == Proposal.agent_run_id)
        .join(Approval, Approval.proposal_id == Proposal.id)
        .where(
            Proposal.case_id == case.id,
            AgentRun.agent_type == "triage",
            Approval.decision == "approved",
        )
    )
    if not retailer_forwarded and not approved_triage:
        raise HTTPException(
            status_code=409,
            detail="Retailer triage approval is required before traceability",
        )
    return await _start_agent(db, case, "traceability", user)


@router.post(
    "/{case_id}/escalation-analysis", response_model=AnalysisStartResponse, status_code=202
)
async def start_escalation_analysis(
    case_id: str,
    user: User = Depends(require_roles("importer_investigator")),
    db: Session = Depends(get_db),
):
    case = _get_authorized_case(db, user, case_id)
    approved_trace = db.scalar(
        select(Proposal.id).where(
            Proposal.case_id == case.id,
            Proposal.type == "retailer_inspections",
            Proposal.status == "approved",
        )
    )
    if not approved_trace:
        raise HTTPException(status_code=409, detail="An approved batch proposal is required")
    completed_finding = db.scalar(
        select(Inspection.id).where(
            Inspection.case_id == case.id,
            Inspection.status == "completed",
        )
    )
    if not completed_finding:
        raise HTTPException(status_code=409, detail="At least one retailer finding is required")
    return await _start_agent(db, case, "escalation", user)


@router.get("/{case_id}/analysis/{run_id}")
def get_analysis(
    case_id: str,
    run_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    case = _get_authorized_case(db, user, case_id)
    run = db.get(AgentRun, run_id)
    if not run or run.case_id != case.id:
        raise HTTPException(status_code=404, detail="Run not found")
    proposal = db.scalar(select(Proposal).where(Proposal.agent_run_id == run.id))
    return {
        "id": run.id,
        "agent_type": run.agent_type,
        "status": run.status,
        "result": run.result,
        "error": run.error,
        "proposal_id": proposal.id if proposal else None,
    }


@router.post("/{case_id}/approvals")
async def decide_proposal(
    case_id: str,
    payload: ApprovalRequest,
    user: User = Depends(require_roles("importer_investigator")),
    db: Session = Depends(get_db),
):
    case = _get_authorized_case(db, user, case_id)
    proposal = db.get(Proposal, payload.proposal_id)
    if not proposal or proposal.case_id != case.id:
        raise HTTPException(status_code=404, detail="Proposal not found")
    existing = db.scalar(select(Approval).where(Approval.proposal_id == proposal.id))
    if existing:
        return {"approval_id": existing.id, "decision": existing.decision, "idempotent": True}

    approval = Approval(
        proposal_id=proposal.id,
        reviewer_id=user.id,
        decision=payload.decision,
        notes=payload.notes,
    )
    db.add(approval)
    proposal.status = payload.decision
    if payload.decision == "approved" and proposal.type == "retailer_inspections":
        for shipment in proposal.payload.get("retailers", []):
            retailer_id = shipment["retailer_id"]
            exists_already = db.scalar(
                select(Inspection.id).where(
                    Inspection.case_id == case.id,
                    Inspection.retailer_id == retailer_id,
                )
            )
            if not exists_already:
                db.add(
                    Inspection(
                        case_id=case.id,
                        retailer_id=retailer_id,
                        assigned_by_user_id=user.id,
                    )
                )
        case.status = "retailer_checks"
    elif payload.decision == "approved" and proposal.type == "request_information":
        case.status = "waiting_for_information"
    elif payload.decision == "approved" and proposal.type == "triage_recommendation":
        recommendation = proposal.payload["recommendation"]
        case.status = (
            "waiting_for_information"
            if recommendation == "request_information"
            else "under_review"
        )
    elif payload.decision == "approved" and proposal.type == "manufacturer_escalation_packet":
        existing_escalation = db.scalar(
            select(Escalation).where(Escalation.case_id == case.id)
        )
        if not existing_escalation:
            packet = dict(proposal.payload["manufacturer_packet"])
            if payload.notes:
                packet["importer_notes"] = payload.notes
            escalation = Escalation(
                case_id=case.id,
                manufacturer_id=proposal.payload["manufacturer_id"],
                packet=packet,
                approved_by_user_id=user.id,
            )
            db.add(escalation)
            db.flush()
            add_audit(
                db,
                case.id,
                "manufacturer_escalation_sent",
                user.id,
                {
                    "escalation_id": escalation.id,
                    "manufacturer_id": escalation.manufacturer_id,
                    "proposal_id": proposal.id,
                },
            )
        case.status = "manufacturer_review"
    else:
        case.status = "under_review"
    add_audit(
        db,
        case.id,
        "proposal_reviewed",
        user.id,
        {"proposal_id": proposal.id, "decision": payload.decision, "notes": payload.notes},
    )
    db.commit()
    run = db.get(AgentRun, proposal.agent_run_id)
    run.status = "completed"
    db.commit()
    await resume_investigation(run.thread_id, payload.decision, payload.notes)
    return {"approval_id": approval.id, "decision": approval.decision, "idempotent": False}
