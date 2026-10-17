from types import SimpleNamespace

import pytest
from app.agents import common
from app.agents.escalation import run_escalation_agent
from app.agents.traceability import run_traceability_agent
from app.config import agent_execution_mode


class RecordClient:
    def __init__(self, finding="issue_observed", status="completed"):
        product = {
            "id": "p1",
            "sku": "SKU-1",
            "name": "Test Chocolate",
            "aliases": [],
            "manufacturer": {"id": "m1"},
        }
        batch = {"id": "b1", "found": True, "batch_number": "38", "product_id": "p1"}
        self.records = {
            "get_case": {
                "public_id": "ESC-TEST",
                "product_name": product["name"],
                "batch_number": "38",
            },
            "search_products": [product],
            "get_batch": batch,
            "get_batch_shipments": [{"shipment_id": "s1", "retailer_id": "r1", "quantity": 20}],
            "get_non_recipient_retailers": [],
            "find_related_reports": [],
            "get_approved_traceability": {"found": True, "product": product, "batch": batch},
            "get_distribution_summary": {"quantity_shipped": 20},
            "get_inspection_findings": [
                {"inspection_id": "i1", "retailer_id": "r1", "status": status, "finding": finding}
            ],
            "get_case_evidence_metadata": [],
            "get_case_timeline": [],
        }
        self.trace = []

    async def call(self, stage, session, name, arguments):
        self.trace.append({"tool": name, "success": True})
        return self.records[name]


@pytest.fixture
def forbid_llm(monkeypatch):
    def fail(**kwargs):
        raise AssertionError("Rule-based stages must never construct a model")

    monkeypatch.setattr(common, "ChatGroq", fail)
    monkeypatch.setattr(
        common,
        "get_settings",
        lambda: SimpleNamespace(
            agent_mode="llm",
            groq_api_key=None,
        ),
    )


@pytest.mark.asyncio
async def test_traceability_needs_no_key_and_uses_recorded_recipients(forbid_llm):
    client = RecordClient()
    result = await run_traceability_agent(client, None, "c1")
    assert agent_execution_mode("traceability") == "rules"
    assert result["execution_mode"] == "rules" and result["model"] is None
    assert result["type"] == "retailer_inspections"
    assert result["retailers"] == client.records["get_batch_shipments"]
    client.records["get_case"]["product_name"] = "Test"
    unresolved = await run_traceability_agent(client, None, "c1")
    assert unresolved["type"] == "request_information"
    assert "confirmed_product_match" in unresolved["missing"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "finding,expected",
    [
        ("issue_observed", "manufacturer_escalation_packet"),
        ("no_issue_observed", "monitoring"),
        ("unable_to_assess", "retailer_followup"),
    ],
)
async def test_escalation_needs_no_key_and_follows_human_findings(forbid_llm, finding, expected):
    result = await run_escalation_agent(RecordClient(finding), None, "c1")
    assert agent_execution_mode("escalation") == "rules"
    assert result["execution_mode"] == "rules" and result["model"] is None
    assert result["type"] == expected
    assert result["followup_retailer_ids"] == (["r1"] if expected == "retailer_followup" else [])


@pytest.mark.asyncio
async def test_escalation_rejects_incomplete_retailer_findings_without_key(forbid_llm):
    with pytest.raises(ValueError, match="All assigned supermarkets"):
        await run_escalation_agent(RecordClient(status="pending"), None, "c1")
