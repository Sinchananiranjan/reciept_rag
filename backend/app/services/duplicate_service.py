from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models import Receipt

class DuplicateService:
    def check_duplicate(self, db: Session, user_id: int, file_hash: str, merchant_name: Optional[str], receipt_date: Optional[str], total: Optional[float], current_receipt_id: Optional[int] = None) -> Tuple[bool, Optional[int], Optional[str]]:
        # 1. SHA-256 Exact File Hash Match
        if file_hash:
            query = db.query(Receipt).filter(
                Receipt.user_id == user_id,
                Receipt.file_hash == file_hash
            )
            if current_receipt_id:
                query = query.filter(Receipt.id != current_receipt_id)
            existing_hash = query.first()
            if existing_hash:
                return True, existing_hash.id, f"Identical file hash match with Receipt #{existing_hash.id} ({existing_hash.original_filename})"

        # 2. Metadata Similarity Match (Merchant + Date + Total match)
        if merchant_name and receipt_date and total is not None:
            query = db.query(Receipt).filter(
                Receipt.user_id == user_id,
                Receipt.merchant_name.ilike(merchant_name.strip()),
                Receipt.receipt_date == str(receipt_date).strip(),
                Receipt.total == float(total)
            )
            if current_receipt_id:
                query = query.filter(Receipt.id != current_receipt_id)
            existing_meta = query.first()
            if existing_meta:
                return True, existing_meta.id, f"Matching merchant ('{merchant_name}'), date ('{receipt_date}'), and total (₹{total:.2f}) with Receipt #{existing_meta.id}"

        return False, None, None

duplicate_service = DuplicateService()
