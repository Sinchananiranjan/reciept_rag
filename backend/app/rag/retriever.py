from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Receipt
from app.services.embedding_service import embedding_service
from app.rag.vector_store import vector_store

class HybridRetriever:
    def retrieve(
        self,
        db: Session,
        user_id: int,
        query: str,
        top_k: int = 5,
        merchant_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # 1. Generate query embedding
        query_vec = embedding_service.get_embedding(query)

        # 2. Vector search in ChromaDB
        vector_results = vector_store.search(
            user_id=user_id,
            query_embedding=query_vec,
            top_k=top_k,
            merchant_filter=merchant_filter,
            category_filter=category_filter
        )

        # Extract retrieved receipt IDs
        retrieved_ids = set()
        for res in vector_results:
            rid = res.get("metadata", {}).get("receipt_id")
            if rid:
                retrieved_ids.add(rid)

        # 3. SQL Relational Database Filter & Fallback Search
        sql_query = db.query(Receipt).filter(Receipt.user_id == user_id)

        if merchant_filter:
            sql_query = sql_query.filter(Receipt.merchant_name.ilike(f"%{merchant_filter}%"))
        if category_filter:
            sql_query = sql_query.filter(Receipt.category.ilike(f"%{category_filter}%"))
        if min_amount is not None:
            sql_query = sql_query.filter(Receipt.total >= min_amount)
        if max_amount is not None:
            sql_query = sql_query.filter(Receipt.total <= max_amount)
        if start_date:
            sql_query = sql_query.filter(Receipt.receipt_date >= start_date)
        if end_date:
            sql_query = sql_query.filter(Receipt.receipt_date <= end_date)

        # Keyword matching over query terms if few vector results
        query_terms = [term for term in query.lower().split() if len(term) > 2]
        if query_terms:
            or_conditions = []
            for term in query_terms:
                or_conditions.append(Receipt.merchant_name.ilike(f"%{term}%"))
                or_conditions.append(Receipt.category.ilike(f"%{term}%"))
                or_conditions.append(Receipt.raw_ocr_text.ilike(f"%{term}%"))
            sql_query = sql_query.filter(*[c for c in or_conditions if c is not None])

        matched_receipts = sql_query.limit(top_k * 2).all()
        for r in matched_receipts:
            retrieved_ids.add(r.id)

        # 4. Fetch full receipt objects from DB strictly scoped by user_id
        final_receipts = db.query(Receipt).filter(
            Receipt.user_id == user_id,
            Receipt.id.in_(list(retrieved_ids))
        ).all()

        formatted_context = []
        for r in final_receipts:
            items_str = ", ".join([f"{item.product_name} (₹{item.total_price or 0:.2f})" for item in r.items]) if r.items else "N/A"
            formatted_context.append({
                "receipt_id": r.id,
                "merchant_name": r.merchant_name or "Unknown Merchant",
                "receipt_date": r.receipt_date or "N/A",
                "total": r.total or 0.0,
                "currency": r.currency or "INR",
                "category": r.category or "Other",
                "payment_method": r.payment_method or "N/A",
                "items_summary": items_str,
                "raw_text": (r.raw_ocr_text or "")[:400]
            })

        return formatted_context

retriever = HybridRetriever()
