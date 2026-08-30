from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.db.database import Base

class ProcessingStatus(str, enum.Enum):
    UPLOADING = "UPLOADING"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    OCR_PROCESSING = "OCR_PROCESSING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    receipts = relationship("Receipt", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)
    upload_date = Column(DateTime, default=datetime.utcnow)
    entry_type = Column(String(32), default="UPLOAD")  # "UPLOAD" or "MANUAL"

    merchant_name = Column(String(255), nullable=True, index=True)
    merchant_address = Column(String(512), nullable=True)
    phone = Column(String(64), nullable=True)
    gstin = Column(String(64), nullable=True)

    receipt_date = Column(String(64), nullable=True, index=True)
    receipt_time = Column(String(64), nullable=True)
    receipt_number = Column(String(128), nullable=True)
    currency = Column(String(32), default="INR")

    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    cgst = Column(Float, nullable=True)
    sgst = Column(Float, nullable=True)
    igst = Column(Float, nullable=True)
    discount = Column(Float, nullable=True)
    total = Column(Float, nullable=True, index=True)
    payment_method = Column(String(128), nullable=True)
    category = Column(String(128), default="Other", index=True)

    raw_ocr_text = Column(Text, nullable=True)
    extracted_json = Column(Text, nullable=True)
    validation_notes = Column(Text, nullable=True)

    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, nullable=True)

    processing_status = Column(String(32), default=ProcessingStatus.PENDING, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="receipts")
    items = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")
    ocr_result = relationship("OCRResult", back_populates="receipt", uselist=False, cascade="all, delete-orphan")

class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    sku = Column(String(128), nullable=True)

    receipt = relationship("Receipt", back_populates="items")

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    confidence_score = Column(Float, default=1.0)
    language = Column(String(32), default="eng")
    created_at = Column(DateTime, default=datetime.utcnow)

    receipt = relationship("Receipt", back_populates="ocr_result")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)
    breakdown_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
