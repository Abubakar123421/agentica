import io


def test_shipment_import_is_idempotent_and_validates_product_batch(client, login_user):
    login_user(client, "importer@escalera.demo")
    content = (
        "shipment_reference,sku,batch_number,retailer_code,quantity,shipped_at\n"
        "SHIP-38-A,CHOC-100,38,RETAILER-A,3000,2026-10-10T09:00:00Z\n"
        "SHIP-BAD,CHOC-100,404,RETAILER-A,5,2026-10-10T09:00:00Z\n"
    )
    response = client.post(
        "/api/v1/imports/shipments",
        files={"file": ("shipments.csv", io.BytesIO(content.encode()), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["inserted"] == 0
    assert response.json()["skipped"] == 1
    assert response.json()["errors"][0]["row"] == 3


def test_invalid_login_and_origin_are_rejected(client):
    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": "importer@escalera.demo", "password": "incorrect-password"},
    )
    assert invalid.status_code == 401

    blocked_origin = client.post(
        "/api/v1/reports",
        headers={"Origin": "https://attacker.example"},
        json={"product_name": "Chocolate", "description": "A sufficiently detailed problem."},
    )
    assert blocked_origin.status_code == 403
