from typing import Any

from mcp import ClientSession

from app.agents.schemas import EscalationResult
from app.services.mcp_client import EvidenceMCPClient


async def run_escalation_agent(
    client: EvidenceMCPClient, session: ClientSession, case_id: str
) -> dict[str, Any]:
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
    expected = {row["retailer_id"] for row in shipments}
    if not expected or expected - {row["retailer_id"] for row in completed}:
        raise ValueError("All assigned supermarkets must submit findings before escalation")

    pending = [item for item in findings if item["status"] != "completed"]
    observed = [item for item in completed if item["finding"] == "issue_observed"]
    no_issue = [item for item in completed if item["finding"] == "no_issue_observed"]
    conflicts = completed if observed and no_issue else []
    missing = [f"retailer_finding:{item['retailer_id']}" for item in pending]
    recommendation = "prepare_manufacturer_escalation" if observed else "continue_monitoring"
    followup_ids = [row["retailer_id"] for row in completed if row["finding"] == "unable_to_assess"]
    if followup_ids and not observed:
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
        type={
            "prepare_manufacturer_escalation": "manufacturer_escalation_packet",
            "request_more_retailer_checks": "retailer_followup",
            "continue_monitoring": "monitoring",
        }[recommendation],
        followup_retailer_ids=followup_ids
        if recommendation == "request_more_retailer_checks"
        else [],
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
    ).model_dump() | {"execution_mode": "rules", "model": None}
