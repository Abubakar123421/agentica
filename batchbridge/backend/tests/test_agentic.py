from types import SimpleNamespace

import httpx
import pytest
from app.agents import common
from app.agents.agentic import TraceDecision, finalize_trace, run_groq_agent
from app.agents.common import EvidenceLedger
from groq import BadRequestError, RateLimitError
from langchain_core.messages import AIMessage, ToolMessage


class ScriptedModel:
    def __init__(self, steps):
        self.steps = iter(steps)
        self.messages = []
        self.tool_names = []

    def bind_tools(self, tools, **kwargs):
        self.tool_names = [tool["function"]["name"] for tool in tools]
        return self

    async def ainvoke(self, messages):
        self.messages = list(messages)
        step = next(self.steps)
        if isinstance(step, Exception):
            raise step
        name, args = step
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": name,
                    "args": args,
                    "id": f"call-{len(messages)}",
                    "type": "tool_call",
                }
            ],
        )


class FakeMCP:
    def __init__(self):
        self.trace = []

    async def list_tools(self):
        names = ["get_case", "search_products", "find_related_reports", "get_batch", "unsafe_write"]
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name=name, description=name, inputSchema={"type": "object", "properties": {}}
                )
                for name in names
            ]
        )

    async def call(self, agent_type, session, name, args):
        self.trace.append({"tool": name, "success": True})
        if name == "get_case":
            return {
                "case_id": "c1",
                "product_name": "Choco",
                "batch_number": "38",
                "source": "customer",
                "retailer": {"id": "r1"},
            }
        if name == "search_products":
            return [] if args["query"] == "misspelled" else [{"id": "p1", "name": "Chocolate"}]
        return []


@pytest.mark.asyncio
async def test_rate_limit_and_malformed_tool_json_recover_without_demo_fallback(monkeypatch):
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.groq.com/test"),
        headers={"retry-after": "2"},
    )
    rate_error = RateLimitError("rate limit", response=response, body={})
    malformed = BadRequestError(
        "invalid tool JSON",
        response=httpx.Response(400, request=httpx.Request("POST", "https://api.groq.com/test")),
        body={"error": {"code": "tool_use_failed"}},
    )
    final = {
        "summary": "Product identity is unresolved; request a clearer label photo.",
        "rationale": ["The catalogue search did not return a product."],
        "confidence": "low",
        "recommendation": "request_information",
        "missing_fields": ["product_identity"],
    }
    model = ScriptedModel(
        [
            rate_error,
            ("get_case", {"case_id": "c1"}),
            ("search_products", {"query": "misspelled"}),
            malformed,
            ("submit_decision", final),
        ]
    )
    delays = []

    async def no_wait(delay):
        delays.append(delay)

    monkeypatch.setattr(common.asyncio, "sleep", no_wait)
    monkeypatch.setattr(
        common,
        "get_settings",
        lambda: SimpleNamespace(groq_api_key="test-only", groq_model="test-model"),
    )
    monkeypatch.setattr(common, "ChatGroq", lambda **kwargs: model)
    mcp = FakeMCP()
    result = await run_groq_agent("triage", mcp, mcp, "c1")
    assert result["execution_mode"] == "llm"
    assert delays == [2]
    assert any("invalid JSON" in str(message.content) for message in model.messages)


@pytest.mark.asyncio
async def test_model_selects_tools_retries_search_and_corrects_unsupported_identity(monkeypatch):
    final = {
        "summary": "The label is unclear; ask for a sharper packaging photo.",
        "rationale": ["Catalogue candidate exists, but visual identity needs clarification."],
        "confidence": "low",
        "follow_up_questions": ["Can you send a sharper label photo?"],
        "selected_product_id": "p1",
        "missing_fields": ["clear_packaging_photo"],
        "recommendation": "request_information",
    }
    model = ScriptedModel(
        [
            ("get_batch", {}),  # Not allowed for triage; never reaches MCP.
            ("get_case", {"case_id": "c1"}),
            ("search_products", {"query": "misspelled"}),
            ("search_products", {"query": "Chocolate"}),
            (
                "find_related_reports",
                {"product_id": "p1", "batch_number": "38", "exclude_case_id": "c1"},
            ),
            ("submit_decision", {**final, "selected_product_id": "invented"}),
            ("submit_decision", final),
        ]
    )
    monkeypatch.setattr(
        common,
        "get_settings",
        lambda: SimpleNamespace(groq_api_key="test-only", groq_model="test-model"),
    )
    monkeypatch.setattr(common, "ChatGroq", lambda **kwargs: model)
    mcp = FakeMCP()
    result = await run_groq_agent("triage", mcp, mcp, "c1")
    assert result["execution_mode"] == "llm"
    assert (
        result["recommendation"] == "request_information"
    )  # The model chose this, despite filled fields.
    assert result["ai_assessment"]["summary"] == final["summary"]
    assert [row["tool"] for row in mcp.trace].count("search_products") == 2
    assert "get_batch" not in model.tool_names and "unsafe_write" not in model.tool_names
    assert any(
        isinstance(message, ToolMessage) and "Selected product" in message.content
        for message in model.messages
    )


def test_trace_proposal_uses_canonical_shipments_and_rejects_unread_or_wrong_lots():
    ledger = EvidenceLedger("c1")
    product = {"id": "p1", "name": "Chocolate"}
    batch = {"id": "b1", "product_id": "p1", "batch_number": "38", "found": True}
    ledger.records = [
        ("get_case", {"case_id": "c1"}, {"batch_number": "38"}),
        ("search_products", {"query": "Chocolate"}, [product]),
        ("get_batch", {"product_id": "p1", "batch_number": "38"}, batch),
    ]
    decision = TraceDecision(
        summary="The reported lot matches the retrieved importer batch.",
        rationale=["Importer batch record matches product and lot."],
        confidence="high",
        selected_product_id="p1",
        selected_batch_id="b1",
        proposal_type="retailer_inspections",
        match_method="exact_name",
    )
    with pytest.raises(ValueError, match="get_batch_shipments"):
        finalize_trace(decision, ledger)
    recipients = [{"shipment_id": "s1", "retailer_id": "r1", "quantity": 50}]
    ledger.records.extend(
        [
            ("get_batch_shipments", {"batch_id": "b1"}, recipients),
            ("get_non_recipient_retailers", {"batch_id": "b1"}, []),
            ("find_related_reports", {"product_id": "p1", "batch_number": "38"}, []),
        ]
    )
    assert finalize_trace(decision, ledger)["retailers"] == recipients
    decision.proposal_type = "request_information"
    with pytest.raises(ValueError, match="concrete missing traceability fact"):
        finalize_trace(decision, ledger)
    decision.proposal_type = "retailer_inspections"
    with pytest.raises(ValueError, match="current case ID"):
        ledger.validate_call("get_case", {"case_id": "another-case"})
    with pytest.raises(ValueError, match="do not invent a lot"):
        ledger.validate_call("get_batch", {"product_id": "p1", "batch_number": "39"})
    with pytest.raises(ValueError, match="Resolve the exact batch"):
        ledger.validate_call("get_batch_shipments", {"batch_id": "invented"})


@pytest.mark.asyncio
async def test_model_failure_and_missing_key_do_not_fall_back(monkeypatch):
    settings = SimpleNamespace(groq_api_key="test-only", groq_model="test-model")
    monkeypatch.setattr(common, "get_settings", lambda: settings)

    class FailedModel:
        def bind_tools(self, *args, **kwargs):
            return self

        async def ainvoke(self, messages):
            raise RuntimeError("Sensitive provider error must not be exposed")

    monkeypatch.setattr(common, "ChatGroq", lambda **kwargs: FailedModel())
    mcp = FakeMCP()
    with pytest.raises(RuntimeError, match="No fallback was used") as error:
        await run_groq_agent("triage", mcp, mcp, "c1")
    assert "Sensitive" not in str(error.value)
    settings.groq_api_key = None
    with pytest.raises(RuntimeError, match="GROQ_API_KEY is missing"):
        await run_groq_agent("triage", mcp, mcp, "c1")


@pytest.mark.parametrize(
    "recommendation,expected_type,targets",
    [
        ("prepare_manufacturer_escalation", "manufacturer_escalation_packet", []),
        ("continue_monitoring", "monitoring", []),
        ("request_more_retailer_checks", "retailer_followup", ["r1"]),
    ],
)
def test_escalation_action_matches_model_recommendation(recommendation, expected_type, targets):
    from app.agents.agentic import EscalationDecision, finalize_escalation

    ledger = EvidenceLedger("c1")
    ledger.records = [
        ("get_case", {"case_id": "c1"}, {"public_id": "BB-TEST"}),
        (
            "get_approved_traceability",
            {"case_id": "c1"},
            {
                "found": True,
                "product": {"manufacturer": {"id": "m1"}},
                "batch": {"id": "b1"},
            },
        ),
        ("get_batch_shipments", {"batch_id": "b1"}, [{"retailer_id": "r1"}]),
        ("get_distribution_summary", {"batch_id": "b1"}, {"quantity_shipped": 50}),
        (
            "get_inspection_findings",
            {"case_id": "c1"},
            [
                {
                    "inspection_id": "i1",
                    "retailer_id": "r1",
                    "status": "completed",
                    "finding": "unable_to_assess",
                }
            ],
        ),
        ("get_case_evidence_metadata", {"case_id": "c1"}, []),
        ("get_case_timeline", {"case_id": "c1"}, []),
    ]
    decision = EscalationDecision(
        summary="Human supermarket findings need further assessment.",
        rationale=["The officer recorded an inconclusive finding."],
        confidence="medium",
        recommendation=recommendation,
        manufacturer_questions=["Review production records?"],
        followup_retailer_ids=targets,
    )
    result = finalize_escalation(decision, ledger)
    assert result["type"] == expected_type
    if targets:
        decision.followup_retailer_ids = ["invented-retailer"]
        with pytest.raises(ValueError, match="verified shipment recipients"):
            finalize_escalation(decision, ledger)
    ledger.records[4][2][0]["status"] = "pending"
    with pytest.raises(ValueError, match="All assigned supermarkets"):
        finalize_escalation(decision, ledger)


@pytest.mark.asyncio
async def test_long_quota_cooldown_fails_promptly_with_provider_retry_time(monkeypatch):
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.groq.com/test"),
        headers={"retry-after": "526"},
    )
    model = ScriptedModel([RateLimitError("quota exhausted", response=response, body={})])
    delays = []

    async def no_wait(delay):
        delays.append(delay)

    monkeypatch.setattr(common.asyncio, "sleep", no_wait)
    with pytest.raises(common.AgentRateLimitError, match="Retry after 527 seconds"):
        await common.invoke_with_rate_limit_retry(model, [])
    assert delays == []


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["triage", "traceability", "escalation"])
@pytest.mark.parametrize("dedicated", [False, True])
async def test_each_agent_uses_only_assigned_key_or_shared_default(monkeypatch, stage, dedicated):
    settings = SimpleNamespace(
        groq_api_key="test-shared",
        groq_model="test-model",
        groq_triage_api_key=None,
        groq_traceability_api_key=None,
        groq_escalation_api_key=None,
    )
    if dedicated:
        for name in ("triage", "traceability", "escalation"):
            setattr(settings, f"groq_{name}_api_key", f"test-{name}")
    captured = {}

    def capture_model(**kwargs):
        captured.update(kwargs)
        raise ValueError("Stop before making any provider request")

    monkeypatch.setattr(common, "get_settings", lambda: settings)
    monkeypatch.setattr(common, "ChatGroq", capture_model)
    mcp = FakeMCP()
    with pytest.raises(RuntimeError, match="model configuration failed"):
        await run_groq_agent(stage, mcp, mcp, "c1")
    assert captured["api_key"] == (f"test-{stage}" if dedicated else "test-shared")
