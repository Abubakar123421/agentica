from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_user
from app.models import Batch, Organization, Product, Shipment, User

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/retailers")
def retailers(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Organization).where(Organization.type == "retailer").order_by(Organization.name)
    ).all()
    return [{"code": row.code, "name": row.name} for row in rows]


@router.get("/products")
def products(_user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Product, Organization)
        .join(Organization, Organization.id == Product.manufacturer_id)
        .order_by(Product.name)
    ).all()
    return [
        {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "manufacturer": {"code": manufacturer.code, "name": manufacturer.name},
        }
        for product, manufacturer in rows
    ]


@router.get("/batches")
def batches(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "importer_investigator":
        raise HTTPException(status_code=403, detail="Role not permitted")
    rows = db.execute(
        select(Batch, Product)
        .join(Product, Product.id == Batch.product_id)
        .order_by(Product.sku, Batch.batch_number)
    ).all()
    return [
        {
            "id": batch.id,
            "sku": product.sku,
            "product_name": product.name,
            "batch_number": batch.batch_number,
            "quantity_received": batch.quantity_received,
            "expiry_date": batch.expiry_date,
        }
        for batch, product in rows
    ]


@router.get("/shipments")
def shipments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "importer_investigator":
        raise HTTPException(status_code=403, detail="Role not permitted")
    rows = db.execute(
        select(Shipment, Batch, Product, Organization)
        .join(Batch, Batch.id == Shipment.batch_id)
        .join(Product, Product.id == Batch.product_id)
        .join(Organization, Organization.id == Shipment.retailer_id)
        .order_by(Shipment.shipped_at.desc())
    ).all()
    return [
        {
            "id": shipment.id,
            "shipment_reference": shipment.shipment_reference,
            "sku": product.sku,
            "batch_number": batch.batch_number,
            "retailer_code": retailer.code,
            "retailer_name": retailer.name,
            "quantity": shipment.quantity,
            "shipped_at": shipment.shipped_at,
        }
        for shipment, batch, product, retailer in rows
    ]
