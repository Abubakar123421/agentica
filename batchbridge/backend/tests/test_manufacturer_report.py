import csv
import io

from app.services.manufacturer_report import manufacturer_report_csv


def test_manufacturer_csv_is_readable_and_escapes_spreadsheet_formulas():
    text = manufacturer_report_csv(
        {
            "case_public_id": "BB-DEMO",
            "product": {
                "name": "Chocolate",
                "sku": "CHOC-100",
                "manufacturer": {"name": "SweetCo GmbH"},
            },
            "batch": {"batch_number": "38", "quantity_received": 10000},
            "distribution_summary": {"quantity_shipped": 3000, "quantity_retained": 7000},
            "distribution": [
                {
                    "shipment_id": "shipment-1",
                    "shipment_reference": "SHIP-38-A",
                    "retailer_name": "CityMart Islamabad",
                    "quantity": 3000,
                    "shipped_at": "2026-10-10T09:00:00",
                }
            ],
            "findings": [
                {
                    "inspection_id": "inspection-1",
                    "retailer_name": "CityMart Islamabad",
                    "finding": "issue_observed",
                    "notes": "=DANGEROUS()",
                    "completed_at": "2026-10-16T12:00:00",
                }
            ],
            "requested_actions": ["Review production records for lot 38."],
        }
    )
    rows = list(csv.DictReader(io.StringIO(text)))

    assert rows[0]["Section"] == "Case"
    assert any(row["Section"] == "Distribution" and row["Quantity"] == "3000" for row in rows)
    finding = next(row for row in rows if row["Section"] == "Retailer finding")
    assert finding["Status"] == "Issue Observed"
    assert finding["Notes"] == "'=DANGEROUS()"
