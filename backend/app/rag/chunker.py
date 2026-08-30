from typing import List, Dict, Any
from app.models import Receipt

class ReceiptChunk:
    def __init__(self, chunk_id: str, chunk_text: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.chunk_text = chunk_text
        self.metadata = metadata

class ReceiptChunker:
    def create_chunks(self, receipt: Receipt) -> List[ReceiptChunk]:
        chunks = []
        
        # 1. Main Structured Summary Chunk
        items_summary = []
        if receipt.items:
            for item in receipt.items:
                items_summary.append(
                    f"- {item.product_name}: {item.quantity} x ₹{item.unit_price or 0:.2f} = ₹{item.total_price or 0:.2f}"
                )
        items_text = "\n".join(items_summary) if items_summary else "No line items listed."

        summary_text = (
            f"Receipt #{receipt.id}\n"
            f"Merchant: {receipt.merchant_name or 'Unknown'}\n"
            f"Date: {receipt.receipt_date or 'Unknown'}\n"
            f"Category: {receipt.category or 'Other'}\n"
            f"Payment Method: {receipt.payment_method or 'Unknown'}\n"
            f"Subtotal: ₹{receipt.subtotal or 0:.2f} | Tax: ₹{receipt.tax or 0:.2f} | Discount: ₹{receipt.discount or 0:.2f}\n"
            f"Total Amount: ₹{receipt.total or 0:.2f} {receipt.currency or 'INR'}\n"
            f"Items Purchased:\n{items_text}\n"
            f"Raw OCR Excerpt: {(receipt.raw_ocr_text or '')[:300]}"
        )

        metadata = {
            "user_id": receipt.user_id,
            "receipt_id": receipt.id,
            "merchant": (receipt.merchant_name or "").lower(),
            "date": str(receipt.receipt_date or ""),
            "total": float(receipt.total or 0.0),
            "category": (receipt.category or "Other").lower(),
            "payment_method": (receipt.payment_method or "").lower()
        }

        chunks.append(
            ReceiptChunk(
                chunk_id=f"receipt_{receipt.id}_summary",
                chunk_text=summary_text,
                metadata=metadata
            )
        )

        # 2. Detailed OCR Chunk if raw text is long
        if receipt.raw_ocr_text and len(receipt.raw_ocr_text) > 300:
            ocr_text = (
                f"Receipt #{receipt.id} Full OCR Text:\n"
                f"Merchant: {receipt.merchant_name}\n"
                f"Date: {receipt.receipt_date}\n"
                f"Content: {receipt.raw_ocr_text}"
            )
            chunks.append(
                ReceiptChunk(
                    chunk_id=f"receipt_{receipt.id}_ocr",
                    chunk_text=ocr_text,
                    metadata=metadata
                )
            )

        return chunks

receipt_chunker = ReceiptChunker()
