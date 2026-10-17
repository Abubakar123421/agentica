import base64
import time

from app.database import SessionLocal
from app.models import Case, Evidence
from sqlalchemy import func, select

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB9kAAAAASUVORK5CYII="
)


def test_photo_report_officer_verification_and_trace(client, login_user):
    created = client.post(
        "/api/v1/reports/photo",
        data={"retailer_code": "RETAILER-A", "description": "The chocolate smells unusual."},
        files=[("files", ("packaging.png", PNG, "image/png"))],
    )
    assert created.status_code == 201, created.text
    report = created.json()
    assert client.get(f"/api/v1/tracking/{report['tracking_token']}").json()["product_name"] == (
        "Awaiting officer verification"
    )
    login_user(client, "importer@escalera.demo")
    case = next(
        row for row in client.get("/api/v1/cases").json() if row["public_id"] == report["case_id"]
    )
    path = f"/api/v1/cases/{case['id']}"
    assert client.post(f"{path}/analysis").status_code == 409
    assert client.post(f"{path}/demo-barcode", json={"barcode": "DEMO-CHOC-38"}).status_code == 403
    client.post("/api/v1/auth/logout")

    login_user(client, "retailer-b@escalera.demo")
    assert client.get(path).status_code == 404
    assert client.post(f"{path}/demo-barcode", json={"barcode": "DEMO-CHOC-38"}).status_code == 404
    client.post("/api/v1/auth/logout")

    login_user(client, "retailer-a@escalera.demo")
    detail = client.get(path).json()
    assert not detail["agent_runs"]  # Photo intake waits for a human identity check.
    photo = detail["evidence"][0]
    assert client.get(photo["url"]).content == PNG
    assert client.post(f"{path}/demo-barcode", json={"barcode": "UNKNOWN"}).status_code == 404
    assert client.post(f"{path}/demo-barcode", json={"barcode": "DEMO-CHOC-39"}).status_code == 409
    forward = {"decision": "forwarded", "notes": "Packaging and demo match reviewed."}
    assert client.post(f"{path}/retailer-review", json=forward).status_code == 409
    hold = client.post(
        f"{path}/retailer-review",
        json={"decision": "needs_customer_information", "notes": "Need a clearer photo."},
    )
    assert hold.status_code == 200
    assert client.get(path).json()["case"]["status"] == "waiting_for_information"
    match = client.post(f"{path}/demo-barcode", json={"barcode": "demo-choc-38"})
    assert match.status_code == 200
    assert match.json()["simulated"] is True
    assert match.json()["batch_number"] == "38"
    assert client.get(path).json()["case"]["batch_number"] is None  # Preview is read-only.
    forward["demo_barcode"] = "DEMO-CHOC-38"
    response = client.post(f"{path}/retailer-review", json=forward)
    assert response.status_code == 200, response.text
    assert client.post(f"{path}/retailer-review", json=forward).json()["idempotent"] is True
    detail = client.get(path).json()
    assert detail["case"]["batch_number"] == "38"
    assert detail["case"]["safety_verdict"] == "unconfirmed"
    assert detail["demo_verification"]["sku"] == "CHOC-100"
    assert sum(event["event_type"] == "demo_barcode_verified" for event in detail["timeline"]) == 1
    triage = next(run for run in detail["agent_runs"] if run["agent_type"] == "triage")
    assert triage["result"]["reported_batch_number"] == "38"
    client.post("/api/v1/auth/logout")

    login_user(client, "importer@escalera.demo")
    assert client.post(f"{path}/analysis").status_code == 409
    triage_proposal = client.get(path).json()["proposals"][0]
    assert triage_proposal["status"] == "pending"
    assert (
        client.post(
            f"{path}/approvals", json={"proposal_id": triage_proposal["id"], "decision": "approved"}
        ).status_code
        == 200
    )
    started = client.post(f"{path}/analysis")
    assert started.status_code == 202
    for _ in range(100):
        analysis = client.get(f"{path}/analysis/{started.json()['run_id']}").json()
        if analysis["status"] in {"awaiting_human", "failed"}:
            break
        time.sleep(0.05)
    assert analysis["status"] == "awaiting_human", analysis
    assert [row["retailer_code"] for row in analysis["result"]["retailers"]] == [
        "RETAILER-A",
        "RETAILER-B",
        "RETAILER-C",
    ]
    assert client.get(path).json()["demo_verification"]["barcode"] == "DEMO-CHOC-38"
    client.post("/api/v1/auth/logout")
    assert client.get(photo["url"]).status_code == 401


def test_photo_report_validation_is_atomic(client):
    with SessionLocal() as db:
        initial_cases = db.scalar(select(func.count()).select_from(Case))
        initial_photos = db.scalar(select(func.count()).select_from(Evidence))
    data = {"retailer_code": "RETAILER-A", "description": "Unusual smell in the package."}
    assert client.post("/api/v1/reports/photo", data=data).status_code == 422
    invalid = client.post(
        "/api/v1/reports/photo",
        data=data,
        files=[
            ("files", ("photo.png", PNG, "image/png")),
            ("files", ("script.svg", b"<svg/>", "image/svg+xml")),
        ],
    )
    assert invalid.status_code == 415
    too_many = client.post(
        "/api/v1/reports/photo",
        data=data,
        files=[("files", (f"photo-{index}.png", PNG, "image/png")) for index in range(4)],
    )
    assert too_many.status_code == 422
    too_large = client.post(
        "/api/v1/reports/photo",
        data=data,
        files=[
            ("files", ("large.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")),
        ],
    )
    assert too_large.status_code == 413
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Case)) == initial_cases
        assert db.scalar(select(func.count()).select_from(Evidence)) == initial_photos
