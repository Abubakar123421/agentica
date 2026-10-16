from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Batch, Organization, Product, ProductAlias, Shipment, User
from app.security import hash_password

DEMO_ORGANIZATIONS = [
    ("IMPORTER-PK", "Pak Continental Imports", "importer"),
    ("RETAILER-A", "CityMart Islamabad", "retailer"),
    ("RETAILER-B", "FreshBasket Rawalpindi", "retailer"),
    ("RETAILER-C", "Family Grocer Lahore", "retailer"),
    ("RETAILER-D", "Value Market Karachi", "retailer"),
    ("SWEETCO-DE", "SweetCo GmbH", "manufacturer"),
]


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(Organization.id).limit(1)):
        return

    organizations: dict[str, Organization] = {}
    for code, name, org_type in DEMO_ORGANIZATIONS:
        org = Organization(code=code, name=name, type=org_type)
        db.add(org)
        organizations[code] = org
    db.flush()

    password_hash = hash_password(get_settings().demo_password)
    users = [
        ("importer@batchbridge.demo", "Ayesha Khan", "importer_investigator", "IMPORTER-PK"),
        ("retailer-a@batchbridge.demo", "Ali Raza", "retailer_safety_manager", "RETAILER-A"),
        ("retailer-b@batchbridge.demo", "Sara Ahmed", "retailer_safety_manager", "RETAILER-B"),
        ("retailer-c@batchbridge.demo", "Hamza Malik", "retailer_safety_manager", "RETAILER-C"),
        ("manufacturer@batchbridge.demo", "Lea Fischer", "manufacturer_reviewer", "SWEETCO-DE"),
    ]
    for email, name, role, org_code in users:
        db.add(
            User(
                email=email,
                display_name=name,
                password_hash=password_hash,
                role=role,
                organization_id=organizations[org_code].id,
            )
        )

    product = Product(
        sku="CHOC-100",
        name="SweetCo Alpine Milk Chocolate 100g",
        manufacturer_id=organizations["SWEETCO-DE"].id,
    )
    db.add(product)
    db.flush()
    for alias in ["Sweet Co Milk Chocolate", "Alpine Chocolate", "SweetCo Choco Bar"]:
        db.add(ProductAlias(product_id=product.id, alias=alias))

    batch_38 = Batch(
        product_id=product.id,
        batch_number="38",
        quantity_received=10_000,
        expiry_date=date(2027, 8, 31),
    )
    batch_39 = Batch(
        product_id=product.id,
        batch_number="39",
        quantity_received=2_000,
        expiry_date=date(2027, 9, 30),
    )
    db.add_all([batch_38, batch_39])
    db.flush()

    shipped_at = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    for reference, batch, retailer_code, quantity in [
        ("SHIP-38-A", batch_38, "RETAILER-A", 3_000),
        ("SHIP-38-B", batch_38, "RETAILER-B", 2_000),
        ("SHIP-38-C", batch_38, "RETAILER-C", 1_000),
        ("SHIP-39-D", batch_39, "RETAILER-D", 1_000),
    ]:
        db.add(
            Shipment(
                shipment_reference=reference,
                batch_id=batch.id,
                retailer_id=organizations[retailer_code].id,
                quantity=quantity,
                shipped_at=shipped_at,
            )
        )
    db.commit()
