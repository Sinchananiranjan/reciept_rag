import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import User, ChatSession, ChatMessage
from app.schemas.chat import (
    RAGQueryRequest,
    RAGQueryResponse,
    ChatSessionResponse,
    ChatMessageResponse,
    SourceCitation,
    ChatBreakdownTable
)
from app.api.auth import get_current_user
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/chat", tags=["Chat & RAG"])

@router.post("", response_model=RAGQueryResponse)
def ask_question(
    query_in: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not query_in.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Get or create ChatSession for current_user
    session = None
    if query_in.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == query_in.session_id,
            ChatSession.user_id == current_user.id
        ).first()

    if not session:
        title = query_in.question[:40] + ("..." if len(query_in.question) > 40 else "")
        session = ChatSession(user_id=current_user.id, title=title)
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. Save User Message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=query_in.question
    )
    db.add(user_msg)
    db.commit()

    # 3. Execute Grounded RAG Pipeline
    rag_result = rag_service.answer_question(
        db=db,
        user_id=current_user.id,
        question=query_in.question,
        merchant_filter=query_in.merchant_filter,
        category_filter=query_in.category_filter,
        min_amount=query_in.min_amount,
        max_amount=query_in.max_amount,
        start_date=query_in.start_date,
        end_date=query_in.end_date
    )

    sources_list = [SourceCitation(**src) for src in rag_result["sources"]]
    sources_json = json.dumps([src.model_dump() for src in sources_list])

    breakdown_obj = ChatBreakdownTable(**rag_result["breakdown"]) if rag_result.get("breakdown") else None
    breakdown_json = json.dumps(breakdown_obj.model_dump()) if breakdown_obj else None

    # 4. Save Assistant Message
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=rag_result["answer"],
        sources_json=sources_json,
        breakdown_json=breakdown_json
    )
    db.add(assistant_msg)
    db.commit()

    return RAGQueryResponse(
        answer=rag_result["answer"],
        session_id=session.id,
        sources=sources_list,
        breakdown=breakdown_obj
    )

@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).all()
    
    res = []
    for s in sessions:
        msgs = []
        for m in s.messages:
            sources = []
            if m.sources_json:
                try:
                    sources = [SourceCitation(**x) for x in json.loads(m.sources_json)]
                except Exception:
                    pass
            breakdown = None
            if m.breakdown_json:
                try:
                    breakdown = ChatBreakdownTable(**json.loads(m.breakdown_json))
                except Exception:
                    pass
            msgs.append(
                ChatMessageResponse(
                    id=m.id,
                    session_id=m.session_id,
                    role=m.role,
                    content=m.content,
                    sources=sources,
                    breakdown=breakdown,
                    created_at=m.created_at
                )
            )
        res.append(
            ChatSessionResponse(
                id=s.id,
                user_id=s.user_id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                messages=msgs
            )
        )
    return res

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    msgs = []
    for m in session.messages:
        sources = []
        if m.sources_json:
            try:
                sources = [SourceCitation(**x) for x in json.loads(m.sources_json)]
            except Exception:
                pass
        breakdown = None
        if m.breakdown_json:
            try:
                breakdown = ChatBreakdownTable(**json.loads(m.breakdown_json))
            except Exception:
                pass
        msgs.append(
            ChatMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                sources=sources,
                breakdown=breakdown,
                created_at=m.created_at
            )
        )

    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=msgs
    )

@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
def delete_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    db.delete(session)
    db.commit()
    return {"message": f"Session #{session_id} deleted."}
