import time

import pytest
from app.database import SessionLocal
from app.models import Approval, Proposal
from sqlalchemy import select


def wait_run(client, path, run_id):
    for _ in range(100):
        result = client.get(f"{path}/analysis/{run_id}").json()
        if result["status"] in {"awaiting_human", "failed"}:
            assert result["status"] == "awaiting_human", result
            return result
        time.sleep(0.05)
    raise AssertionError("Agent did not complete")


def new_case(client, login_user):
    created = client.post(
        "/api/v1/reports",
        json={
            "product_name": "SweetCo Alpine Milk Chocolate 100g",
            "batch_number": "38",
            "retailer_code": "RETAILER-A",
            "description": "Fictional package issue for workflow testing.",
        },
    )
    assert created.status_code == 201
    login_user(client, "importer@escalera.demo")
    case = next(
        row
        for row in client.get("/api/v1/cases").json()
        if row["public_id"] == created.json()["case_id"]
    )
    return f"/api/v1/cases/{case['id']}"


def test_new_triage_does_not_inherit_old_human_review(client, login_user):
    path = new_case(client, login_user)
    client.post("/api/v1/auth/logout")
    login_user(client, "retailer-a@escalera.demo")
    assert (
        client.post(
            f"{path}/retailer-review",
            json={
                "decision": "forwarded",
                "notes": "Fictional packaging reviewed by officer.",
            },
        ).status_code
        == 200
    )
    client.post("/api/v1/auth/logout")
    login_user(client, "importer@escalera.demo")
    first = client.get(path).json()["proposals"][0]
    assert first["status"] == "pending"
    decision = {"proposal_id": first["id"], "decision": "approved"}
    assert client.post(f"{path}/approvals", json=decision).status_code == 200
    assert client.post(f"{path}/approvals", json=decision).json()["idempotent"]
    assert (
        client.post(f"{path}/approvals", json=decision | {"decision": "rejected"}).status_code
        == 409
    )
    started = client.post(f"{path}/triage")
    result = wait_run(client, path, started.json()["run_id"])
    with SessionLocal() as db:
        proposal = db.get(Proposal, result["proposal_id"])
        assert proposal.status == "pending"
        assert db.scalar(select(Approval.id).where(Approval.proposal_id == proposal.id)) is None
    assert client.post(f"{path}/analysis").status_code == 409
    assert client.get(path).json()["workflow"]["traceability"]["can_run"] is False


def test_information_change_invalidates_pending_proposal_and_rerun_replaces_it(client, login_user):
    path = new_case(client, login_user)
    old = client.get(path).json()["proposals"][0]
    assert (
        client.post(
            f"{path}/information",
            json={
                "notes": "Fictional clarification: packaging was sealed when opened.",
            },
        ).status_code
        == 200
    )
    approval = client.post(
        f"{path}/approvals",
        json={
            "proposal_id": old["id"],
            "decision": "approved",
        },
    )
    assert approval.status_code == 409
    assert "older inputs" in approval.json()["detail"]
    started = client.post(f"{path}/triage")
    result = wait_run(client, path, started.json()["run_id"])
    assert result["proposal_id"] != old["id"]
    detail = client.get(path).json()
    assert (
        next(row for row in detail["proposals"] if row["id"] == old["id"])["status"] == "superseded"
    )
    assert detail["proposals"][0]["review_block_reason"] is None


def test_operational_status_and_manufacturer_endpoint_cannot_skip_approvals(client, login_user):
    path = new_case(client, login_user)
    for status in ("retailer_checks", "manufacturer_review", "closed"):
        assert client.patch(f"{path}/status", json={"status": status}).status_code == 409
    assert (
        client.patch(
            f"{path}/status",
            json={
                "status": "under_review",
                "safety_verdict": "confirmed",
                "notes": "No evidence yet.",
            },
        ).status_code
        == 409
    )
    case_id = path.rsplit("/", 1)[1]
    assert client.post(f"/api/v1/escalations/cases/{case_id}", json={}).status_code == 409


@pytest.mark.parametrize("action", ["retailer_followup", "monitoring"])
def test_non_manufacturer_recommendations_never_dispatch_packet(
    client, login_user, monkeypatch, action
):
    from app.agents import AGENT_RUNNERS
    from app.agents.escalation import run_escalation_agent

    path = new_case(client, login_user)
    client.post("/api/v1/auth/logout")
    login_user(client, "retailer-a@escalera.demo")
    client.post(
        f"{path}/retailer-review", json={"decision": "forwarded", "notes": "Fixture reviewed."}
    )
    client.post("/api/v1/auth/logout")
    login_user(client, "importer@escalera.demo")
    triage = client.get(path).json()["proposals"][0]
    assert (
        client.post(
            f"{path}/approvals", json={"proposal_id": triage["id"], "decision": "approved"}
        ).status_code
        == 200
    )
    started = client.post(f"{path}/analysis")
    trace = wait_run(client, path, started.json()["run_id"])
    assert (
        client.post(
            f"{path}/approvals", json={"proposal_id": trace["proposal_id"], "decision": "approved"}
        ).status_code
        == 200
    )
    case_id = path.rsplit("/", 1)[1]
    for letter in ("a", "b", "c"):
        client.post("/api/v1/auth/logout")
        login_user(client, f"retailer-{letter}@escalera.demo")
        inspection = next(
            row for row in client.get("/api/v1/inspections").json() if row["case_id"] == case_id
        )
        assert (
            client.post(
                f"/api/v1/inspections/{inspection['id']}/finding",
                json={
                    "finding": "unable_to_assess",
                    "notes": "Fictional assessment requires more evidence.",
                },
            ).status_code
            == 200
        )
    client.post("/api/v1/auth/logout")
    login_user(client, "importer@escalera.demo")

    async def proposed_action(mcp, session, selected_case):
        result = await run_escalation_agent(mcp, session, selected_case)
        result["type"] = action
        result["recommendation"] = (
            "request_more_retailer_checks"
            if action == "retailer_followup"
            else "continue_monitoring"
        )
        result["followup_retailer_ids"] = (
            [trace["result"]["retailers"][0]["retailer_id"]]
            if action == "retailer_followup"
            else []
        )
        return result

    monkeypatch.setitem(AGENT_RUNNERS, "escalation", proposed_action)
    started = client.post(f"{path}/escalation-analysis")
    result = wait_run(client, path, started.json()["run_id"])
    assert (
        client.post(
            f"{path}/approvals", json={"proposal_id": result["proposal_id"], "decision": "approved"}
        ).status_code
        == 200
    )
    detail = client.get(path).json()
    assert detail["case"]["status"] != "manufacturer_review"
    assert sum(row["status"] == "pending" for row in detail["inspections"]) == (
        1 if action == "retailer_followup" else 0
    )
    client.post("/api/v1/auth/logout")
    login_user(client, "manufacturer@escalera.demo")
    assert not any(row["case_id"] == case_id for row in client.get("/api/v1/escalations").json())


def test_information_after_approval_explains_why_traceability_is_locked(client, login_user):
    path = new_case(client, login_user)
    proposal = client.get(path).json()["proposals"][0]
    assert (
        client.post(
            f"{path}/approvals",
            json={
                "proposal_id": proposal["id"],
                "decision": "approved",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{path}/information",
            json={
                "notes": "New fictional investigation detail saved after approval.",
            },
        ).status_code
        == 200
    )
    gate = client.get(path).json()["workflow"]["traceability"]
    assert gate["can_run"] is False
    assert "Case information changed after triage" in gate["blocked_reason"]
    assert client.post(f"{path}/analysis").status_code == 409
