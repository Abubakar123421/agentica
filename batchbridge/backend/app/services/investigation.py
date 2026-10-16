import asyncio
import secrets
from datetime import datetime, timezone

from langgraph.types import Command
from sqlalchemy import func, select

from app.audit import add_audit
from app.database import SessionLocal
from app.models import AgentRun, Approval, Proposal, RetailerReview
from app.services.workflow import investigation_graph


def queue_investigation(db, case_id: str, agent_type: str, created_by_user_id: str | None):
    active = db.scalar(
        select(AgentRun).where(
            AgentRun.case_id == case_id,
            AgentRun.agent_type == agent_type,
            AgentRun.status.in_(["queued", "running", "awaiting_human"]),
        )
    )
    if active:
        return active, False
    run = AgentRun(
        case_id=case_id,
        agent_type=agent_type,
        thread_id=f"case:{case_id}:{agent_type}:{secrets.token_hex(6)}",
        status="queued",
        created_by_user_id=created_by_user_id,
    )
    db.add(run)
    db.flush()
    add_audit(
        db,
        case_id,
        f"{agent_type}_started",
        created_by_user_id,
        {"run_id": run.id, "agent_type": agent_type},
    )
    return run, True


async def execute_investigation(run_id: str) -> None:
    with SessionLocal() as db:
        run = db.get(AgentRun, run_id)
        if not run or run.status != "queued":
            return
        run.status = "running"
        db.commit()
        case_id = run.case_id
        thread_id = run.thread_id
        agent_type = run.agent_type

    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await asyncio.wait_for(
            investigation_graph.ainvoke(
                {"case_id": case_id, "agent_type": agent_type}, config=config
            ),
            timeout=90,
        )
        proposal_payload = state["proposal"]
        with SessionLocal() as db:
            run = db.get(AgentRun, run_id)
            latest_version = db.scalar(
                select(func.coalesce(func.max(Proposal.version), 0)).where(
                    Proposal.case_id == case_id
                )
            )
            proposal = Proposal(
                case_id=case_id,
                agent_run_id=run_id,
                type=proposal_payload["type"],
                payload=proposal_payload,
                version=int(latest_version or 0) + 1,
            )
            db.add(proposal)
            db.flush()
            run.status = "awaiting_human"
            if agent_type == "triage":
                review = db.scalar(
                    select(RetailerReview)
                    .where(RetailerReview.case_id == case_id)
                    .order_by(RetailerReview.created_at.desc())
                )
                if review:
                    decision = "approved" if review.decision == "forwarded" else "changes_requested"
                    proposal.status = decision
                    run.status = "completed"
                    db.add(
                        Approval(
                            proposal_id=proposal.id,
                            reviewer_id=review.reviewer_id,
                            decision=decision,
                            notes=review.notes,
                        )
                    )
            run.result = proposal_payload
            run.completed_at = datetime.now(timezone.utc)
            add_audit(
                db,
                case_id,
                f"{agent_type}_completed",
                run.created_by_user_id,
                {
                    "run_id": run.id,
                    "agent_type": agent_type,
                    "proposal_id": proposal.id,
                    "proposal_type": proposal.type,
                    "version": proposal.version,
                },
            )
            db.commit()
    except Exception as exc:
        with SessionLocal() as db:
            run = db.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.error = str(exc)[:2000]
                run.completed_at = datetime.now(timezone.utc)
                add_audit(
                    db,
                    run.case_id,
                    f"{run.agent_type}_failed",
                    run.created_by_user_id,
                    {"run_id": run.id, "agent_type": run.agent_type, "error": run.error},
                )
                db.commit()


async def resume_investigation(thread_id: str, decision: str, notes: str | None) -> None:
    """Best-effort graph resume; database approvals remain authoritative across restarts."""
    try:
        await investigation_graph.ainvoke(
            Command(resume={"decision": decision, "notes": notes}),
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception:
        # A process restart can clear the in-memory graph checkpoint. The approval is safely stored
        # and enacted through deterministic database code, so graph resume is observability only.
        return
