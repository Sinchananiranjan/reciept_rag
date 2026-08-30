from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import User, Receipt
from app.schemas.receipt import ReceiptResponse
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/search", tags=["Search"])

@router.get("", response_model=List[ReceiptResponse])
def search_receipts(
    q: Optional[str] = Query(None, description="Natural text or keyword search"),
    category: Optional[str] = None,
    merchant: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Receipt).filter(Receipt.user_id == current_user.id)

    if category:
        query = query.filter(Receipt.category.ilike(f"%{category}%"))
    if merchant:
        query = query.filter(Receipt.merchant_name.ilike(f"%{merchant}%"))
    if min_amount is not None:
        query = query.filter(Receipt.total >= min_amount)
    if max_amount is not None:
        query = query.filter(Receipt.total <= max_amount)

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            (Receipt.merchant_name.ilike(search_term)) |
            (Receipt.raw_ocr_text.ilike(search_term)) |
            (Receipt.category.ilike(search_term)) |
            (Receipt.receipt_number.ilike(search_term)) |
            (Receipt.payment_method.ilike(search_term))
        )

    receipts = query.order_by(Receipt.created_at.desc()).all()
    return receipts
