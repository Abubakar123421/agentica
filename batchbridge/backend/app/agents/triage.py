from typing import Any

from mcp import ClientSession

from app.agents.agentic import run_groq_agent
from app.agents.schemas import TriageResult
from app.config import get_settings
from app.services.mcp_client import EvidenceMCPClient


def _select_product(case: dict, products: list[dict]) -> dict | None:
    query = case["product_name"].strip().lower()
    for product in products:
        known_names = {
            product["name"].lower(),
            product["sku"].lower(),
            *(alias.lower() for alias in product.get("aliases", [])),
        }
        if query in known_names:
            return product
    return products[0] if len(products) == 1 else None


async def run_triage_agent(
    client: EvidenceMCPClient, session: ClientSession, case_id: str
) -> dict[str, Any]:
    if get_settings().agent_mode == "llm":
        return await run_groq_agent("triage", client, session, case_id)
    case = await client.call("triage", session, "get_case", {"case_id": case_id})
    products = await client.call(
        "triage", session, "search_products", {"query": case.get("product_name", "")}
    )
    selected = _select_product(case, products)
    related: list[dict] = []
    if selected and case.get("batch_number"):
        related = await client.call(
            "triage",
            session,
            "find_related_reports",
            {
                "product_id": selected["id"],
                "batch_number": case["batch_number"],
                "exclude_case_id": case_id,
            },
        )

    missing: list[str] = []
    questions: list[str] = []
    if not selected:
        missing.append("confirmed_product_match")
        questions.append("Please provide a clear photo of the product name and barcode.")
    if not case.get("batch_number"):
        missing.append("batch_number")
        questions.append("Please provide a photo of the manufacturer lot or batch number.")
    if not case.get("retailer"):
        missing.append("purchase_retailer")
        questions.append("Which retailer and location sold the product?")

    if missing:
        recommendation = "request_information"
        confidence = "low"
    elif case.get("source") == "customer":
        recommendation = "retailer_review"
        confidence = "high" if selected else "medium"
    else:
        recommendation = "forward_to_importer"
        confidence = "high" if selected else "medium"

    rationale = ["The report was normalized against the importer product catalogue."]
    if related:
        rationale.append(f"Found {len(related)} related report(s) for the same product and lot.")
    if missing:
        rationale.append("Missing fields prevent reliable product and batch traceability.")

    ai_assessment = None
    return TriageResult(
        case_id=case_id,
        possible_product_ids=[product["id"] for product in products],
        reported_batch_number=case.get("batch_number"),
        related_case_ids=[item["case_id"] for item in related],
        missing_fields=missing,
        follow_up_questions=questions,
        recommendation=recommendation,
        confidence=confidence,
        rationale=rationale,
        evidence_references=[case_id, *[item["case_id"] for item in related]],
        ai_assessment=ai_assessment,
        tool_calls=client.trace,
    ).model_dump() | {"execution_mode": "demo_rules", "model": None}
