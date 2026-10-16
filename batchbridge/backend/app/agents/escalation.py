from typing import Any

from mcp import ClientSession

from app.agents.agentic import run_groq_agent
from app.agents.schemas import EscalationResult
from app.config import get_settings
from app.services.mcp_client import EvidenceMCPClient


async def run_escalation_agent(
    client: EvidenceMCPClient, session: ClientSession, case_id: str
) -> dict[str, Any]:
    if get_settings().agent_mode == "llm":
        return await run_groq_agent("escalation", client, session, case_id)
    case = await client.call("escalation", session, "get_case", {"case_id": case_id})
    trace = await client.call(
        "escalation", session, "get_approved_traceability", {"case_id": case_id}
    )
    if not trace.get("found"):
        raise ValueError("An approved traceability proposal is required")

    batch = trace["batch"]
    product = trace["product"]
    shipments = await client.call(
        "escalation", session, "get_batch_shipments", {"batch_id": batch["id"]}
    )
    distribution = await client.call(
        "escalation", session, "get_distribution_summary", {"batch_id": batch["id"]}
    )
    findings = await client.call(
        "escalation", session, "get_inspection_findings", {"case_id": case_id}
    )
    evidence = await client.call(
        "escalation", session, "get_case_evidence_metadata", {"case_id": case_id}
    )
    timeline = await client.call("escalation", session, "get_case_timeline", {"case_id": case_id})
    completed = [item for item in findings if item["status"] == "completed"]
    if not completed:
        raise ValueError("At least one completed retailer finding is required")

    pending = [item for item in findings if item["status"] != "completed"]
    observed = [item for item in completed if item["finding"] == "issue_observed"]
    no_issue = [item for item in completed if item["finding"] == "no_issue_observed"]
    conflicts = completed if observed and no_issue else []
    missing = [f"retailer_finding:{item['retailer_id']}" for item in pending]
    recommendation = "prepare_manufacturer_escalation" if observed else "continue_monitoring"
    if pending and not observed:
        recommendation = "request_more_retailer_checks"

    packet = {
        "case_public_id": case["public_id"],
        "product": product,
        "batch": batch,
        "distribution": shipments,
        "distribution_summary": distribution,
        "findings": completed,
        "evidence": evidence,
        "timeline": timeline,
        "agent_summary": {
            "completed_inspections": len(completed),
            "pending_inspections": len(pending),
            "conflicting_findings": bool(conflicts),
        },
    }
    ai_assessment = None
    return EscalationResult(
        type="manufacturer_escalation_packet"
        if recommendation == "prepare_manufacturer_escalation"
        else "monitoring",
        case_id=case_id,
        batch_id=batch["id"],
        completed_inspections=len(completed),
        pending_inspections=len(pending),
        findings_summary=completed,
        conflicting_findings=conflicts,
        affected_quantity=distribution["quantity_shipped"],
        checked_quantity=None,
        missing_evidence=missing,
        manufacturer_questions=[
            f"Review production and ingredient records for lot {batch['batch_number']}.",
            "Report any matching complaints or internal quality deviations.",
        ],
        recommendation=recommendation,
        manufacturer_id=product["manufacturer"]["id"],
        manufacturer_packet=packet,
        rationale=[
            "The packet contains the approved batch trace and human retailer findings.",
            "The importer must approve the packet before it is sent.",
        ],
        evidence_references=[
            case_id,
            batch["id"],
            *[item["inspection_id"] for item in completed],
            *[item["id"] for item in evidence],
        ],
        ai_assessment=ai_assessment,
        tool_calls=client.trace,
    ).model_dump() | {"execution_mode": "demo_rules", "model": None}
