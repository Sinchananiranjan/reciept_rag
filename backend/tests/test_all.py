import pytest
import io
import os
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db

# Setup test SQLite database in-memory
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_receiptrag.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def create_user_and_login(email: str, password: str = "password123"):
    res_reg = client.post("/api/auth/register", json={"email": email, "password": password, "full_name": "Test User"})
    assert res_reg.status_code == 201
    
    res_login = client.post("/api/auth/login", data={"username": email, "password": password})
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, res_reg.json()["user"]["id"]

def test_auth_flow():
    headers, user_id = create_user_and_login("user1@example.com")
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "user1@example.com"

def test_no_fake_demo_data_on_unreadable_file():
    """Verify that unreadable files yield empty OCR text and NEEDS_REVIEW status without injecting fake receipt data."""
    headers, user_id = create_user_and_login("real_user@example.com")
    
    # Upload binary unreadable file bytes
    file_bytes = b"\x00\x01\x02\x03\x04\x05"
    file = ("blank.jpg", io.BytesIO(file_bytes), "image/jpeg")

    res_upload = client.post("/api/receipts/upload", files={"files": file}, headers=headers)
    assert res_upload.status_code == 201
    receipt_data = res_upload.json()[0]
    receipt_id = receipt_data["id"]

    res_details = client.get(f"/api/receipts/{receipt_id}", headers=headers)
    assert res_details.status_code == 200
    r = res_details.json()

    # Must NEVER contain fake demo strings
    assert "Sample Mart" not in (r.get("merchant_name") or "")
    assert "Organic Milk" not in (r.get("raw_ocr_text") or "")
    assert r["merchant_name"] is None or r["merchant_name"] == ""

def test_manual_receipt_creation():
    """Verify manual receipt entry endpoint without file upload."""
    headers, user_id = create_user_and_login("manual_user@example.com")

    manual_payload = {
        "merchant_name": "Apollo Pharmacy",
        "receipt_date": "2026-08-20",
        "currency": "INR",
        "category": "Healthcare",
        "payment_method": "UPI",
        "subtotal": 450.00,
        "tax": 50.00,
        "discount": 0.00,
        "total": 500.00,
        "items": [
            {"product_name": "Vitamin C Tablets", "quantity": 2, "unit_price": 250.00, "total_price": 500.00}
        ]
    }

    res = client.post("/api/receipts/manual", json=manual_payload, headers=headers)
    assert res.status_code == 201
    r = res.json()
    assert r["merchant_name"] == "Apollo Pharmacy"
    assert r["total"] == 500.00
    assert r["entry_type"] == "MANUAL"
    assert len(r["items"]) == 1

def test_monthly_and_yearly_analytics():
    """Verify monthly and yearly analytics aggregations derived from real user receipts."""
    headers, user_id = create_user_and_login("analytics_user@example.com")

    # Create 2 manual receipts
    client.post("/api/receipts/manual", json={"merchant_name": "DMart", "total": 1200.00, "category": "Groceries"}, headers=headers)
    client.post("/api/receipts/manual", json={"merchant_name": "Zara", "total": 3500.00, "category": "Clothing"}, headers=headers)

    res_overview = client.get("/api/analytics/overview", headers=headers)
    assert res_overview.status_code == 200
    data = res_overview.json()

    assert data["summary"]["total_spending"] == 4700.00
    assert data["summary"]["total_receipts"] == 2
    assert len(data["monthly_analytics"]) >= 1
    assert len(data["yearly_analytics"]) >= 1

def test_real_receipt_extraction_quality():
    """Root-cause regression test: uploads a real receipt image (not synthetic
    text) and verifies OCR->extraction produces correct merchant/date/total
    AND every line item with a real quantity/unit price/total price — this
    guards against the exact bugs previously found: quantities silently
    defaulting to 1 because of trailing OCR table-border noise, and currency
    being misdetected as USD from a stray '$' glyph."""
    headers, user_id = create_user_and_login("real_ocr_user@example.com")

    sample_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "01ef37322647487fbfa4227448b46f91.png")
    assert os.path.exists(sample_path), "Sample receipt fixture is missing"

    with open(sample_path, "rb") as f:
        file = ("receipt.png", io.BytesIO(f.read()), "image/png")
        res_upload = client.post("/api/receipts/upload", files={"files": file}, headers=headers)
    assert res_upload.status_code == 201
    receipt_id = res_upload.json()[0]["id"]

    r = client.get(f"/api/receipts/{receipt_id}", headers=headers).json()
    assert r["processing_status"] == "COMPLETED"
    assert r["merchant_name"], "Merchant name must be extracted from real OCR text"
    assert r["receipt_date"], "Receipt date must be extracted"
    assert r["total"] is not None and r["total"] > 0
    assert r["currency"] == "INR", "Must not misdetect currency as USD from OCR noise"

    items = r["items"]
    assert len(items) >= 10, "Every line item on the receipt must be extracted"
    # No item should have a fabricated ₹0.00 price when OCR clearly shows a price
    assert all(it["unit_price"] is None or it["unit_price"] > 0 for it in items)
    assert all(it["total_price"] is None or it["total_price"] > 0 for it in items)

    milk_item = next((it for it in items if "milk" in it["product_name"].lower()), None)
    assert milk_item is not None, "Milk line item must be present"
    # This receipt's OCR text shows "2 56.00 112.00" for milk -- quantity must
    # be read as 2, not silently default to 1 because of trailing noise.
    assert milk_item["quantity"] == 2.0
    assert milk_item["unit_price"] == 56.0
    assert milk_item["total_price"] == 112.0

    # Preview must be served back for an uploaded (non-manual) receipt
    basename = r["file_path"].split("/")[-1].split("\\")[-1]
    preview = client.get(f"/uploads/{basename}")
    assert preview.status_code == 200


def test_rag_item_level_precision_no_double_counting():
    """A store-level question must sum whole receipt totals, but an
    item-level question must sum ONLY the matching line items -- and must
    keep distinct product variants separate rather than merging them."""
    headers, user_id = create_user_and_login("rag_precision_user@example.com")

    client.post("/api/receipts/manual", json={
        "merchant_name": "DMart", "receipt_date": "2026-08-05", "category": "Groceries", "total": 500.0,
        "items": [
            {"product_name": "Regular Milk 1L", "quantity": 2, "unit_price": 56.0, "total_price": 112.0},
            {"product_name": "Bread", "quantity": 1, "unit_price": 40.0, "total_price": 40.0},
        ]
    }, headers=headers)
    client.post("/api/receipts/manual", json={
        "merchant_name": "More Supermarket", "receipt_date": "2026-08-12", "category": "Groceries", "total": 300.0,
        "items": [
            {"product_name": "Almond Milk 1L", "quantity": 1, "unit_price": 180.0, "total_price": 180.0},
        ]
    }, headers=headers)

    import datetime as dt
    import app.services.query_analyzer as qa_module
    real_date = qa_module.date

    class FakeDate(dt.date):
        @classmethod
        def today(cls):
            return dt.date(2026, 8, 25)

    qa_module.date = FakeDate
    try:
        res = client.post("/api/chat", json={"question": "How much did I spend on milk this month?"}, headers=headers)
        assert res.status_code == 200
        body = res.json()
        # Item-level total must be 112 + 180 = 292, NEVER the whole-receipt
        # totals (500 + 300 = 800).
        assert "292" in body["answer"]
        assert "800" not in body["answer"]
        assert body["breakdown"] is not None
        product_names = {row[0] for row in body["breakdown"]["rows"]}
        assert "Regular Milk 1L" in product_names
        assert "Almond Milk 1L" in product_names
        assert len(body["breakdown"]["rows"]) == 2, "Variants must not be merged into one row"
    finally:
        qa_module.date = real_date


def test_analytics_arbitrary_period_selection():
    """The month/year picker must allow ANY period, not just ones with data --
    a period with no receipts returns a clean has_data=False, not an error or
    fabricated numbers."""
    headers, user_id = create_user_and_login("period_user@example.com")
    client.post("/api/receipts/manual", json={"merchant_name": "DMart", "receipt_date": "2026-08-10", "total": 200.0}, headers=headers)

    populated = client.get("/api/analytics/monthly", params={"year": 2026, "month": 8}, headers=headers).json()
    assert populated["has_data"] is True
    assert populated["total_spending"] == 200.0

    empty = client.get("/api/analytics/monthly", params={"year": 2019, "month": 1}, headers=headers).json()
    assert empty["has_data"] is False
    assert empty["total_spending"] == 0.0
    assert empty["categories"] == []

    empty_year = client.get("/api/analytics/yearly", params={"year": 2040}, headers=headers).json()
    assert empty_year["has_data"] is False



    """CRITICAL TEST: User A must never access User B's receipts or search results."""
    headers_a, user_a_id = create_user_and_login("usera@example.com")
    headers_b, user_b_id = create_user_and_login("userb@example.com")

    # User A creates a receipt
    client.post("/api/receipts/manual", json={"merchant_name": "User A Store", "total": 999.00}, headers=headers_a)

    # User B list receipts -> Empty list
    res_list_b = client.get("/api/receipts", headers=headers_b)
    assert res_list_b.status_code == 200
    assert len(res_list_b.json()) == 0

    # User B RAG query -> Returns no matching receipts
    res_rag_b = client.post("/api/chat", json={"question": "What did I buy at User A Store?"}, headers=headers_b)
    assert res_rag_b.status_code == 200
    assert "couldn't find a matching receipt" in res_rag_b.json()["answer"].lower()
    assert len(res_rag_b.json()["sources"]) == 0


def test_all_real_receipt_fixtures_extract_rows():
    """Every real image fixture must produce OCR text and structured line rows.
    This is deliberately a broad smoke test: no receipt image should silently
    become an empty metadata form when OCR is available."""
    from app.services.ocr_service import ocr_service
    from app.services.extraction_service import extraction_service

    uploads = os.path.join(os.path.dirname(__file__), "..", "uploads")
    images = [
        os.path.join(uploads, name)
        for name in os.listdir(uploads)
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".heic"))
    ]
    assert images, "No real receipt images found"

    failures = []
    for path in images:
        raw, confidence, available = ocr_service.extract_text_from_file(path)
        if not available or len(raw.strip()) < 20:
            failures.append((os.path.basename(path), "OCR empty"))
            continue
        data = extraction_service.extract_structured_data(raw)
        if not data.get("items"):
            failures.append((os.path.basename(path), "no line items", raw[:250]))
        if not data.get("merchant_name") and not data.get("total"):
            failures.append((os.path.basename(path), "no useful structured fields"))

    assert not failures, f"Receipt extraction failures: {failures}"
