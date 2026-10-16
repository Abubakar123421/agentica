from app.database import SessionLocal
from app.models import Case, RetailerReview
from app.seed import DEMO_COMPLAINTS, seed_demo_data
from sqlalchemy import select


def test_demo_complaints_are_named_and_seeded_once(client):
    with SessionLocal() as db:
        seed_demo_data(db)
        seed_demo_data(db)
        public_ids = [item[0] for item in DEMO_COMPLAINTS]
        cases = db.scalars(select(Case).where(Case.public_id.in_(public_ids))).all()
        reviews = db.scalars(
            select(RetailerReview).where(RetailerReview.case_id.in_([case.id for case in cases]))
        ).all()

    assert len(cases) == 8
    assert len(reviews) == 8
    assert {case.reporter_name for case in cases} == {item[1] for item in DEMO_COMPLAINTS}
    assert all(case.product_name == "SweetCo Alpine Milk Chocolate 100g" for case in cases)
    assert all(case.batch_number == "38" for case in cases)
    assert all(case.status == "under_review" for case in cases)
    assert all(review.decision == "forwarded" for review in reviews)
