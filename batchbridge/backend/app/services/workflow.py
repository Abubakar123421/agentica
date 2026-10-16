import json
from typing import Any, Literal, TypedDict

from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.mcp_client import EvidenceMCPClient


class InvestigationState(TypedDict, total=False):
    case_id: str
    case: dict[str, Any]
    products: list[dict[str, Any]]
    selected_product: dict[str, Any] | None
    batch: dict[str, Any] | None
    shipments: list[dict[str, Any]]
    related_reports: list[dict[str, Any]]
    proposal: dict[str, Any]
    human_decision: dict[str, Any]


class AIAssessment(BaseModel):
    risk_summary: str = Field(max_length=600)
    recommended_action: Literal[
        "request_more_information", "send_retailer_checks", "urgent_human_review"
    ]
    unanswered_questions: list[str] = Field(max_length=5)
    confidence: Literal["low", "medium", "high"]


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


async def gather_evidence(state: InvestigationState) -> InvestigationState:
    client = EvidenceMCPClient()
    async with client.session() as session:
        case = await client.call(session, "get_case", {"case_id": state["case_id"]})
        products = await client.call(
            session, "search_products", {"query": case.get("product_name", "")}
        )
        selected = _select_product(case, products)
        batch = None
        shipments: list[dict] = []
        related: list[dict] = []
        if selected and case.get("batch_number"):
            batch = await client.call(
                session,
                "get_batch",
                {"product_id": selected["id"], "batch_number": case["batch_number"]},
            )
            if batch.get("found"):
                shipments = await client.call(
                    session, "get_batch_shipments", {"batch_id": batch["id"]}
                )
                related = await client.call(
                    session,
                    "find_related_reports",
                    {
                        "product_id": selected["id"],
                        "batch_number": case["batch_number"],
                        "exclude_case_id": state["case_id"],
                    },
                )
    return {
        "case": case,
        "products": products,
        "selected_product": selected,
        "batch": batch,
        "shipments": shipments,
        "related_reports": related,
    }


async def _ai_assessment(state: InvestigationState, default_action: str) -> dict | None:
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    evidence = {
        "report": {
            "source": state["case"].get("source"),
            "product_name": state["case"].get("product_name"),
            "batch_number": state["case"].get("batch_number"),
            "description": state["case"].get("description"),
        },
        "matched_product": state.get("selected_product"),
        "batch": state.get("batch"),
        "related_report_count": len(state.get("related_reports", [])),
        "recipient_count": len(state.get("shipments", [])),
        "default_action": default_action,
    }
    prompt = (
        "You are assisting a food safety investigator. Assess only the supplied evidence. "
        "A complaint is suspicion, not proof. Do not declare a batch safe or contaminated. "
        "Do not invent products, batches, retailers, quantities, or lab results. Recommend which "
        "human review should happen next and list the most useful unanswered questions.\n\n"
        f"Evidence:\n{json.dumps(evidence, default=str)}"
    )
    try:
        model = ChatGroq(
            model=settings.groq_model,
            temperature=0,
            api_key=settings.groq_api_key,
            timeout=30,
            max_retries=1,
        ).with_structured_output(AIAssessment)
        result = await model.ainvoke(prompt)
        return result.model_dump() if hasattr(result, "model_dump") else dict(result)
    except Exception as exc:
        return {"unavailable": True, "reason": type(exc).__name__}


async def draft_proposal(state: InvestigationState) -> InvestigationState:
    case = state["case"]
    selected = state.get("selected_product")
    batch = state.get("batch")
    shipments = state.get("shipments", [])
    missing: list[str] = []
    if not case.get("batch_number"):
        missing.append("batch_number")
    if not selected:
        missing.append("confirmed_product_match")
    elif not batch or not batch.get("found"):
        missing.append("known_importer_batch")

    if missing:
        ai_assessment = await _ai_assessment(state, "request_more_information")
        proposal = {
            "type": "request_information",
            "confidence": "low",
            "missing": missing,
            "reason": "The report cannot yet be tied to a unique product and manufacturer lot.",
            "retailers": [],
            "ai_assessment": ai_assessment,
        }
    else:
        ai_assessment = await _ai_assessment(state, "send_retailer_checks")
        proposal = {
            "type": "retailer_inspections",
            "confidence": "high",
            "product": selected,
            "batch": batch,
            "retailers": shipments,
            "related_reports": state.get("related_reports", []),
            "reason": (
                "The complaint product and manufacturer lot match importer records. "
                "Recipients are copied directly from recorded shipments."
            ),
            "ai_assessment": ai_assessment,
        }
    return {"proposal": proposal}


def human_gate(state: InvestigationState) -> InvestigationState:
    decision = interrupt(
        {
            "message": "Importer approval is required before creating retailer tasks.",
            "proposal": state["proposal"],
        }
    )
    return {"human_decision": decision}


def build_investigation_graph():
    builder = StateGraph(InvestigationState)
    builder.add_node("gather_evidence", gather_evidence)
    builder.add_node("draft_proposal", draft_proposal)
    builder.add_node("human_gate", human_gate)
    builder.add_edge(START, "gather_evidence")
    builder.add_edge("gather_evidence", "draft_proposal")
    builder.add_edge("draft_proposal", "human_gate")
    builder.add_edge("human_gate", END)
    return builder.compile(checkpointer=InMemorySaver())


investigation_graph = build_investigation_graph()
