from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Batch, Product, Shipment

# Fictional identifiers, deliberately distinct from real retail barcodes.
DEMO_BARCODES = {
    "DEMO-CHOC-38": ("CHOC-100", "38"),
    "DEMO-CHOC-39": ("CHOC-100", "39"),
}


def resolve_demo_barcode(db: Session, barcode: str, retailer_id: str) -> dict:
    code = barcode.strip().upper()
    fixture = DEMO_BARCODES.get(code)
    if not fixture:
        raise HTTPException(status_code=404, detail="Unknown demo barcode. Try DEMO-CHOC-38.")
    sku, lot = fixture
    row = db.execute(
        select(Product, Batch)
        .join(Batch, Batch.product_id == Product.id)
        .where(Product.sku == sku, Batch.batch_number == lot)
    ).first()
    if not row:
        raise HTTPException(
            status_code=404, detail="Demo product and batch are not in the catalogue"
        )
    product, batch = row
    if not db.scalar(
        select(Shipment.id).where(
            Shipment.batch_id == batch.id, Shipment.retailer_id == retailer_id
        )
    ):
        raise HTTPException(
            status_code=409, detail="This demo batch was not shipped to your supermarket"
        )
    return {
        "simulated": True,
        "barcode": code,
        "product_id": product.id,
        "product_name": product.name,
        "sku": product.sku,
        "batch_id": batch.id,
        "batch_number": batch.batch_number,
    }
