import os
import json
import uuid
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status, Query, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db, SessionLocal
from app.models import User, Receipt, ReceiptItem, OCRResult, ProcessingStatus
from app.schemas.receipt import ReceiptResponse, ReceiptUpdate, ManualReceiptCreate
from app.api.auth import get_current_user
from app.utils.file_utils import validate_file, compute_sha256
from app.services.ocr_service import ocr_service
from app.services.extraction_service import extraction_service
from app.services.categorization_service import categorization_service
from app.services.duplicate_service import duplicate_service
from app.services.embedding_service import embedding_service
from app.rag.chunker import receipt_chunker
from app.rag.vector_store import vector_store

router = APIRouter(prefix="/api/receipts", tags=["Receipts"])


def _active_db_session_factory(request: Request):
    """Resolves the DB session factory that background tasks should use --
    respects app.dependency_overrides[get_db] (used by the test suite) so a
    background task never writes to a different database than the request
    that queued it read/wrote from. Falls back to the real SessionLocal in
    normal (non-overridden) operation, so production behavior is identical
    to before."""
    override = request.app.dependency_overrides.get(get_db)
    if override:
        return lambda: next(override())
    return SessionLocal

def process_receipt_pipeline(receipt_id: int, db_session_factory=None):
    """Background processing pipeline: OCR -> Structured Extraction -> Validation -> Categorization -> Vector Indexing.

    `db_session_factory` lets callers hand in the session-maker actually in
    effect (via FastAPI's dependency_overrides, e.g. in tests) instead of
    hard-coding the production SessionLocal. Production behavior is
    unchanged: when no factory is supplied, it falls back to SessionLocal
    exactly as before."""
    factory = db_session_factory or SessionLocal
    db = factory()
    receipt = None
    try:
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            return

        receipt.processing_status = ProcessingStatus.OCR_PROCESSING
        db.commit()

        # 1. OCR Text Extraction
        raw_text, confidence, is_available = ocr_service.extract_text_from_file(receipt.file_path)
        receipt.raw_ocr_text = raw_text

        ocr_res = db.query(OCRResult).filter(OCRResult.receipt_id == receipt.id).first()
        if not ocr_res:
            ocr_res = OCRResult(receipt_id=receipt.id, raw_text=raw_text or "", confidence_score=confidence)
            db.add(ocr_res)
        else:
            ocr_res.raw_text = raw_text or ""
            ocr_res.confidence_score = confidence

        # Handle OCR Unavailability / Unreadable Image without fake data
        if not is_available or not raw_text.strip():
            receipt.processing_status = ProcessingStatus.NEEDS_REVIEW
            receipt.validation_notes = "Unable to extract reliable text from this receipt image/PDF. Please review or enter details manually."
            db.commit()
            return

        # 2. Structured Extraction
        receipt.processing_status = ProcessingStatus.EXTRACTING
        db.commit()

        extracted = extraction_service.extract_structured_data(raw_text, image_path=receipt.file_path)
        receipt.extracted_json = json.dumps(extracted)

        receipt.merchant_name = extracted.get("merchant_name")
        receipt.merchant_address = extracted.get("merchant_address")
        receipt.phone = extracted.get("phone")
        receipt.gstin = extracted.get("gstin")

        receipt.receipt_date = extracted.get("receipt_date")
        receipt.receipt_time = extracted.get("receipt_time")
        receipt.receipt_number = extracted.get("receipt_number") or extracted.get("invoice_number")
        receipt.currency = extracted.get("currency") or "INR"

        receipt.subtotal = extracted.get("subtotal")
        receipt.tax = extracted.get("tax")
        receipt.cgst = extracted.get("cgst")
        receipt.sgst = extracted.get("sgst")
        receipt.igst = extracted.get("igst")
        receipt.discount = extracted.get("discount")
        receipt.total = extracted.get("total")
        receipt.payment_method = extracted.get("payment_method")

        # 3. Arithmetic Validation
        receipt.processing_status = ProcessingStatus.VALIDATING
        db.commit()
        validation_note = extraction_service.validate_totals(extracted)
        receipt.validation_notes = validation_note

        # 4. Items Insertion
        db.query(ReceiptItem).filter(ReceiptItem.receipt_id == receipt.id).delete()
        items_data = extracted.get("items", [])
        for item in items_data:
            r_item = ReceiptItem(
                receipt_id=receipt.id,
                product_name=item.get("product_name", "Item"),
                quantity=item.get("quantity", 1.0),
                unit_price=item.get("unit_price"),
                total_price=item.get("total_price"),
                sku=item.get("sku")
            )
            db.add(r_item)

        # 5. Categorization
        cat = categorization_service.classify_receipt(
            merchant_name=receipt.merchant_name or "",
            items=items_data,
            raw_text=raw_text
        )
        receipt.category = cat

        # 6. Duplicate Check
        is_dup, dup_id, dup_reason = duplicate_service.check_duplicate(
            db=db,
            user_id=receipt.user_id,
            file_hash=receipt.file_hash,
            merchant_name=receipt.merchant_name,
            receipt_date=receipt.receipt_date,
            total=receipt.total,
            current_receipt_id=receipt.id
        )
        receipt.is_duplicate = is_dup
        receipt.duplicate_of_id = dup_id

        db.commit()
        db.refresh(receipt)

        # 7. Chunking & Vector Store Indexing
        receipt.processing_status = ProcessingStatus.INDEXING
        db.commit()

        chunks = receipt_chunker.create_chunks(receipt)
        embeddings = [embedding_service.get_embedding(c.chunk_text) for c in chunks]
        vector_store.add_chunks(user_id=receipt.user_id, chunks=chunks, embeddings=embeddings)

        # 8. Complete Pipeline
        receipt.processing_status = ProcessingStatus.COMPLETED if receipt.merchant_name and receipt.total else ProcessingStatus.NEEDS_REVIEW
        db.commit()

    except Exception as e:
        logger.exception("Error processing receipt #%s", receipt_id)
        if receipt:
            receipt.processing_status = ProcessingStatus.FAILED
            receipt.validation_notes = f"Processing error: {str(e)}"
            db.commit()
    finally:
        db.close()

@router.post("/upload", response_model=List[ReceiptResponse], status_code=status.HTTP_201_CREATED)
async def upload_receipts(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    session_factory = _active_db_session_factory(request)
    created_receipts = []
    for file in files:
        file_bytes = await file.read()
        valid, err_msg = validate_file(file.filename, len(file_bytes))
        if not valid:
            raise HTTPException(status_code=400, detail=err_msg)

        file_hash = compute_sha256(file_bytes)

        # Save actual uploaded file to upload directory
        ext = os.path.splitext(file.filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        saved_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        new_receipt = Receipt(
            user_id=current_user.id,
            original_filename=file.filename,
            file_path=saved_path,
            file_hash=file_hash,
            entry_type="UPLOAD",
            processing_status=ProcessingStatus.PENDING
        )
        db.add(new_receipt)
        db.commit()
        db.refresh(new_receipt)

        background_tasks.add_task(process_receipt_pipeline, new_receipt.id, session_factory)
        created_receipts.append(new_receipt)

    return created_receipts

@router.post("/manual", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
def create_manual_receipt(
    manual_in: ManualReceiptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a manual receipt entry without an uploaded file."""
    placeholder_path = os.path.join(settings.UPLOAD_DIR, "manual_entry.txt")
    if not os.path.exists(placeholder_path):
        with open(placeholder_path, "w") as f:
            f.write("Manual Receipt Record")

    new_receipt = Receipt(
        user_id=current_user.id,
        original_filename="Manual Entry",
        file_path=placeholder_path,
        entry_type="MANUAL",
        merchant_name=manual_in.merchant_name,
        merchant_address=manual_in.merchant_address,
        phone=manual_in.phone,
        gstin=manual_in.gstin,
        receipt_date=manual_in.receipt_date or datetime.utcnow().strftime("%Y-%m-%d"),
        receipt_time=manual_in.receipt_time,
        receipt_number=manual_in.receipt_number,
        currency=manual_in.currency,
        subtotal=manual_in.subtotal,
        tax=manual_in.tax,
        cgst=manual_in.cgst,
        sgst=manual_in.sgst,
        igst=manual_in.igst,
        discount=manual_in.discount,
        total=manual_in.total,
        category=manual_in.category or "Other",
        payment_method=manual_in.payment_method or "Cash",
        raw_ocr_text=f"MANUAL RECEIPT: {manual_in.merchant_name} Total: {manual_in.currency} {manual_in.total:.2f}",
        processing_status=ProcessingStatus.COMPLETED
    )

    db.add(new_receipt)
    db.commit()
    db.refresh(new_receipt)

    for item in manual_in.items:
        r_item = ReceiptItem(
            receipt_id=new_receipt.id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price or ((item.unit_price or 0.0) * item.quantity),
            sku=item.sku
        )
        db.add(r_item)

    db.commit()
    db.refresh(new_receipt)

    # Index manual receipt in ChromaDB Vector Store
    chunks = receipt_chunker.create_chunks(new_receipt)
    embeddings = [embedding_service.get_embedding(c.chunk_text) for c in chunks]
    vector_store.add_chunks(user_id=current_user.id, chunks=chunks, embeddings=embeddings)

    return new_receipt

@router.get("", response_model=List[ReceiptResponse])
def get_user_receipts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    merchant: Optional[str] = None
):
    query = db.query(Receipt).filter(Receipt.user_id == current_user.id)
    if category:
        query = query.filter(Receipt.category.ilike(f"%{category}%"))
    if merchant:
        query = query.filter(Receipt.merchant_name.ilike(f"%{merchant}%"))
    
    receipts = query.order_by(Receipt.created_at.desc()).all()
    return receipts

@router.get("/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(
    receipt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    return receipt

@router.put("/{receipt_id}", response_model=ReceiptResponse)
def update_receipt(
    receipt_id: int,
    receipt_update: ReceiptUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    if receipt_update.merchant_name is not None:
        receipt.merchant_name = receipt_update.merchant_name
    if receipt_update.merchant_address is not None:
        receipt.merchant_address = receipt_update.merchant_address
    if receipt_update.phone is not None:
        receipt.phone = receipt_update.phone
    if receipt_update.gstin is not None:
        receipt.gstin = receipt_update.gstin
    if receipt_update.receipt_date is not None:
        receipt.receipt_date = receipt_update.receipt_date
    if receipt_update.receipt_time is not None:
        receipt.receipt_time = receipt_update.receipt_time
    if receipt_update.receipt_number is not None:
        receipt.receipt_number = receipt_update.receipt_number
    if receipt_update.currency is not None:
        receipt.currency = receipt_update.currency
    if receipt_update.subtotal is not None:
        receipt.subtotal = receipt_update.subtotal
    if receipt_update.tax is not None:
        receipt.tax = receipt_update.tax
    if receipt_update.cgst is not None:
        receipt.cgst = receipt_update.cgst
    if receipt_update.sgst is not None:
        receipt.sgst = receipt_update.sgst
    if receipt_update.igst is not None:
        receipt.igst = receipt_update.igst
    if receipt_update.discount is not None:
        receipt.discount = receipt_update.discount
    if receipt_update.total is not None:
        receipt.total = receipt_update.total
    if receipt_update.category is not None:
        receipt.category = receipt_update.category
    if receipt_update.payment_method is not None:
        receipt.payment_method = receipt_update.payment_method

    if receipt_update.items is not None:
        db.query(ReceiptItem).filter(ReceiptItem.receipt_id == receipt.id).delete()
        for item in receipt_update.items:
            new_item = ReceiptItem(
                receipt_id=receipt.id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price or ((item.unit_price or 0.0) * item.quantity),
                sku=item.sku
            )
            db.add(new_item)

    # Re-validate totals & mark status COMPLETED
    extracted = {
        "subtotal": receipt.subtotal,
        "tax": receipt.tax,
        "discount": receipt.discount,
        "total": receipt.total
    }
    receipt.validation_notes = extraction_service.validate_totals(extracted)
    receipt.processing_status = ProcessingStatus.COMPLETED

    db.commit()
    db.refresh(receipt)

    # Update Vector Store Index
    vector_store.delete_receipt(user_id=current_user.id, receipt_id=receipt.id)
    chunks = receipt_chunker.create_chunks(receipt)
    embeddings = [embedding_service.get_embedding(c.chunk_text) for c in chunks]
    vector_store.add_chunks(user_id=current_user.id, chunks=chunks, embeddings=embeddings)

    return receipt

@router.delete("/{receipt_id}", status_code=status.HTTP_200_OK)
def delete_receipt(
    receipt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    if os.path.exists(receipt.file_path) and receipt.entry_type != "MANUAL":
        try:
            os.remove(receipt.file_path)
        except Exception:
            pass

    vector_store.delete_receipt(user_id=current_user.id, receipt_id=receipt.id)

    db.delete(receipt)
    db.commit()
    return {"message": f"Receipt #{receipt_id} deleted successfully."}

@router.post("/{receipt_id}/reprocess", response_model=ReceiptResponse)
def reprocess_receipt(
    receipt_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    receipt.processing_status = ProcessingStatus.PENDING
    db.commit()

    background_tasks.add_task(process_receipt_pipeline, receipt.id, _active_db_session_factory(request))
    return receipt
