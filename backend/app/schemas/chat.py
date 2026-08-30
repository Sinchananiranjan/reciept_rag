from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class SourceCitation(BaseModel):
    receipt_id: int
    merchant_name: str
    receipt_date: str
    total: float
    category: str
    snippet: str

class ChatBreakdownTable(BaseModel):
    title: str
    columns: List[str]
    rows: List[List[str]]

class RAGQueryRequest(BaseModel):
    question: str
    session_id: Optional[int] = None
    merchant_filter: Optional[str] = None
    category_filter: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class RAGQueryResponse(BaseModel):
    answer: str
    session_id: int
    sources: List[SourceCitation]
    breakdown: Optional[ChatBreakdownTable] = None

class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    sources: List[SourceCitation] = []
    breakdown: Optional[ChatBreakdownTable] = None
    created_at: datetime

class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []
