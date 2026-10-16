from typing import Any

from mcp import ClientSession

from app.agents.schemas import TraceabilityResult
from app.services.mcp_client import EvidenceMCPClient


def _match_product(case: dict, products: list[dict]) -> tuple[dict | None, str]:
    query = case["product_name"].strip().lower()
    for product in products:
        if query == product["sku"].lower():
            return product, "exact_sku"
        if query == product["name"].lower():
            return product, "exact_name"
        if query in {alias.lower() for alias in product.get("aliases", [])}:
            return product, "known_alias"
    return None, "unresolved"


async def run_traceability_agent(
    client: EvidenceMCPClient, session: ClientSession, case_id: str
) -> dict[str, Any]:
    case = await client.call("traceability", session, "get_case", {"case_id": case_id})
    products = await client.call(
        "traceability", session, "search_products", {"query": case.get("product_name", "")}
    )
    selected, match_method = _match_product(case, products)
    batch = None
    shipments: list[dict] = []
    excluded_retailers: list[dict] = []
    related: list[dict] = []
    if selected and case.get("batch_number"):
        batch = await client.call(
            "traceability",
            session,
            "get_batch",
            {"product_id": selected["id"], "batch_number": case["batch_number"]},
        )
        if batch.get("found"):
            shipments = await client.call(
                "traceability", session, "get_batch_shipments", {"batch_id": batch["id"]}
            )
            excluded_retailers = await client.call(
                "traceability",
                session,
                "get_non_recipient_retailers",
                {"batch_id": batch["id"]},
            )
            related = await client.call(
                "traceability",
                session,
                "find_related_reports",
                {
                    "product_id": selected["id"],
                    "batch_number": case["batch_number"],
                    "exclude_case_id": case_id,
                },
            )

    missing: list[str] = []
    if not case.get("batch_number"):
        missing.append("batch_number")
    if not selected:
        missing.append("confirmed_product_match")
    elif not batch or not batch.get("found"):
        missing.append("known_importer_batch")

    if batch and batch.get("found") and not shipments:
        missing.append("recorded_shipments")

    proposal_type = "request_information" if missing else "retailer_inspections"
    confidence = "low" if missing else ("medium" if match_method == "known_alias" else "high")
    rationale = (
        ["The report cannot yet be tied to a unique product and manufacturer lot."]
        if missing
        else [
            "The product and manufacturer lot match importer records.",
            "Every proposed retailer was copied from an exact batch shipment record.",
        ]
    )
    ai_assessment = None
    return TraceabilityResult(
        type=proposal_type,
        case_id=case_id,
        matched_product_id=selected["id"] if selected else None,
        matched_batch_id=batch["id"] if batch and batch.get("found") else None,
        match_method=match_method,
        confidence=confidence,
        product=selected,
        batch=batch,
        retailers=shipments,
        excluded_retailers=excluded_retailers,
        related_reports=related,
        missing=missing,
        rationale=rationale,
        evidence_references=[
            case_id,
            *([selected["id"]] if selected else []),
            *([batch["id"]] if batch and batch.get("found") else []),
            *[shipment["shipment_id"] for shipment in shipments],
        ],
        ai_assessment=ai_assessment,
        tool_calls=client.trace,
    ).model_dump() | {"execution_mode": "rules", "model": None}
