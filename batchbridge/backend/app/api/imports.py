import csv
import io
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import Batch, Organization, Product, Shipment, User
from app.schemas import CsvImportResult

router = APIRouter(prefix="/imports", tags=["imports"])
importer_only = require_roles("importer_investigator")


@router.get("/templates/{kind}", response_class=PlainTextResponse)
def download_template(kind: str, _user: User = Depends(importer_only)):
    templates = {
        "batches": (
            "sku,product_name,manufacturer_code,batch_number,quantity_received,expiry_date\n"
        ),
        "shipments": ("shipment_reference,sku,batch_number,retailer_code,quantity,shipped_at\n"),
    }
    if kind not in templates:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Template not found")
    return PlainTextResponse(
        templates[kind],
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'},
    )


async def _rows(file: UploadFile) -> list[dict[str, str]]:
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("CSV exceeds 2 MB")
    text = raw.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


@router.post("/batches", response_model=CsvImportResult)
async def import_batches(
    file: UploadFile = File(...),
    _user: User = Depends(importer_only),
    db: Session = Depends(get_db),
):
    inserted = skipped = 0
    errors: list[dict] = []
    try:
        rows = await _rows(file)
    except (UnicodeDecodeError, ValueError) as exc:
        return CsvImportResult(inserted=0, skipped=0, errors=[{"row": 0, "error": str(exc)}])

    required = {"sku", "product_name", "manufacturer_code", "batch_number", "quantity_received"}
    for index, row in enumerate(rows, start=2):
        try:
            if not required.issubset(row):
                raise ValueError(f"Missing columns: {sorted(required - set(row))}")
            manufacturer = db.scalar(
                select(Organization).where(
                    Organization.code == row["manufacturer_code"].strip(),
                    Organization.type == "manufacturer",
                )
            )
            if not manufacturer:
                raise ValueError("Unknown manufacturer_code")
            product = db.scalar(select(Product).where(Product.sku == row["sku"].strip()))
            if not product:
                product = Product(
                    sku=row["sku"].strip(),
                    name=row["product_name"].strip(),
                    manufacturer_id=manufacturer.id,
                )
                db.add(product)
                db.flush()
            elif product.manufacturer_id != manufacturer.id:
                raise ValueError("SKU belongs to another manufacturer")
            existing = db.scalar(
                select(Batch).where(
                    Batch.product_id == product.id,
                    Batch.batch_number == row["batch_number"].strip(),
                )
            )
            if existing:
                skipped += 1
                continue
            quantity = int(row["quantity_received"])
            if quantity <= 0:
                raise ValueError("quantity_received must be positive")
            expiry = date.fromisoformat(row["expiry_date"]) if row.get("expiry_date") else None
            db.add(
                Batch(
                    product_id=product.id,
                    batch_number=row["batch_number"].strip(),
                    quantity_received=quantity,
                    expiry_date=expiry,
                )
            )
            db.commit()
            inserted += 1
        except (ValueError, IntegrityError) as exc:
            db.rollback()
            errors.append({"row": index, "error": str(exc)})
    return CsvImportResult(inserted=inserted, skipped=skipped, errors=errors)


@router.post("/shipments", response_model=CsvImportResult)
async def import_shipments(
    file: UploadFile = File(...),
    _user: User = Depends(importer_only),
    db: Session = Depends(get_db),
):
    inserted = skipped = 0
    errors: list[dict] = []
    try:
        rows = await _rows(file)
    except (UnicodeDecodeError, ValueError) as exc:
        return CsvImportResult(inserted=0, skipped=0, errors=[{"row": 0, "error": str(exc)}])

    required = {
        "shipment_reference",
        "sku",
        "batch_number",
        "retailer_code",
        "quantity",
        "shipped_at",
    }
    for index, row in enumerate(rows, start=2):
        try:
            if not required.issubset(row):
                raise ValueError(f"Missing columns: {sorted(required - set(row))}")
            reference = row["shipment_reference"].strip()
            if db.scalar(select(Shipment.id).where(Shipment.shipment_reference == reference)):
                skipped += 1
                continue
            product = db.scalar(select(Product).where(Product.sku == row["sku"].strip()))
            if not product:
                raise ValueError("Unknown sku")
            batch = db.scalar(
                select(Batch).where(
                    Batch.product_id == product.id,
                    Batch.batch_number == row["batch_number"].strip(),
                )
            )
            if not batch:
                raise ValueError("Unknown product and batch combination")
            retailer = db.scalar(
                select(Organization).where(
                    Organization.code == row["retailer_code"].strip(),
                    Organization.type == "retailer",
                )
            )
            if not retailer:
                raise ValueError("Unknown retailer_code")
            quantity = int(row["quantity"])
            if quantity <= 0:
                raise ValueError("quantity must be positive")
            shipped_at = datetime.fromisoformat(row["shipped_at"].replace("Z", "+00:00"))
            if shipped_at.tzinfo is None:
                shipped_at = shipped_at.replace(tzinfo=timezone.utc)
            db.add(
                Shipment(
                    shipment_reference=reference,
                    batch_id=batch.id,
                    retailer_id=retailer.id,
                    quantity=quantity,
                    shipped_at=shipped_at,
                )
            )
            db.commit()
            inserted += 1
        except (ValueError, IntegrityError) as exc:
            db.rollback()
            errors.append({"row": index, "error": str(exc)})
    return CsvImportResult(inserted=inserted, skipped=skipped, errors=errors)
