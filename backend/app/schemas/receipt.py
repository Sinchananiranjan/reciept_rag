from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class ReceiptItemBase(BaseModel):
    product_name: str
    quantity: float = 1.0
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    sku: Optional[str] = None

class ReceiptItemCreate(ReceiptItemBase):
    pass

class ReceiptItemResponse(ReceiptItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_id: int

class ManualReceiptCreate(BaseModel):
    merchant_name: str
    receipt_date: Optional[str] = None
    receipt_time: Optional[str] = None
    currency: str = "INR"
    category: str = "Other"
    payment_method: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    discount: Optional[float] = None
    total: float
    merchant_address: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    receipt_number: Optional[str] = None
    items: List[ReceiptItemBase] = []

class ReceiptUpdate(BaseModel):
    merchant_name: Optional[str] = None
    merchant_address: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    receipt_date: Optional[str] = None
    receipt_time: Optional[str] = None
    receipt_number: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    items: Optional[List[ReceiptItemBase]] = None

class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    original_filename: str
    file_path: str
    file_hash: Optional[str] = None
    upload_date: datetime
    entry_type: str = "UPLOAD"

    merchant_name: Optional[str] = None
    merchant_address: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    receipt_date: Optional[str] = None
    receipt_time: Optional[str] = None
    receipt_number: Optional[str] = None
    currency: str = "INR"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    discount: Optional[float] = None
    total: Optional[float] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None

    raw_ocr_text: Optional[str] = None
    extracted_json: Optional[str] = None
    validation_notes: Optional[str] = None

    is_duplicate: bool = False
    duplicate_of_id: Optional[int] = None
    processing_status: str

    created_at: datetime
    updated_at: datetime

    items: List[ReceiptItemResponse] = []

class DuplicateWarningResponse(BaseModel):
    is_duplicate: bool
    existing_receipt_id: Optional[int] = None
    reason: Optional[str] = None
