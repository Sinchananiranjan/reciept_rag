import json
import re
import urllib.request
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Receipt
from app.rag.retriever import retriever
from app.rag.prompts import (
    RAG_SYSTEM_PROMPT,
    build_rag_user_prompt,
    STRUCTURED_EXPLAIN_SYSTEM_PROMPT,
    build_structured_explain_prompt,
)
from app.rag.structured_formatter import format_structured_answer
from app.services.query_analyzer import analyze_question, QueryFilters
from app.services.structured_query_service import run_structured_query


class RAGService:
    def answer_question(
        self,
        db: Session,
        user_id: int,
        question: str,
        merchant_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        filters = analyze_question(question, db, user_id)
        # Explicit filters passed by the caller (e.g. an advanced search UI)
        # take precedence over whatever the question text implies.
        if merchant_filter:
            filters.merchant = merchant_filter
        if category_filter:
            filters.category = category_filter

        if filters.is_analytical:
            return self._answer_structured(db, user_id, question, filters)

        return self._answer_retrieval(
            db, user_id, question,
            merchant_filter=filters.merchant, category_filter=filters.category,
            min_amount=min_amount, max_amount=max_amount,
            start_date=start_date or (filters.start_date.isoformat() if filters.start_date else None),
            end_date=end_date or (filters.end_date.isoformat() if filters.end_date else None),
        )

    # ------------------------------------------------------------------
    # Structured-first path: query & aggregate the DB directly (see
    # structured_query_service — never sums whole receipt totals for
    # item-level questions, and groups product variants separately), then
    # deterministically format the verified numbers. The LLM, if configured,
    # is only ever asked to rephrase that already-correct summary — never to
    # compute anything — and its output is discarded if it drops a number.
    # ------------------------------------------------------------------
    def _answer_structured(self, db: Session, user_id: int, question: str, filters: QueryFilters) -> Dict[str, Any]:
        result = run_structured_query(db, user_id=user_id, filters=filters)
        narrative, breakdown = format_structured_answer(filters, result)

        answer_text = narrative
        if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 5 and result.mode != "empty":
            try:
                polished = self._call_openai_chat(
                    STRUCTURED_EXPLAIN_SYSTEM_PROMPT,
                    build_structured_explain_prompt(question, narrative)
                )
                if self._preserves_figures(narrative, polished):
                    answer_text = polished
            except Exception as e:
                print(f"OpenAI structured-explain error ({str(e)}), using deterministic summary.")

        sources = self._sources_for_receipt_ids(db, result.receipt_ids)
        return {"answer": answer_text, "sources": sources, "breakdown": breakdown}

    @staticmethod
    def _preserves_figures(verified_text: str, candidate_text: str) -> bool:
        """Sanity check so a polished LLM response can never silently drop or
        alter a verified number: every distinct monetary/numeric figure that
        appears in the deterministic summary must still appear in the
        candidate, otherwise we discard the LLM's version."""
        figures = set(re.findall(r"\d[\d,]*\.?\d*", verified_text))
        if not figures:
            return True
        return all(fig in candidate_text for fig in figures)

    def _sources_for_receipt_ids(self, db: Session, receipt_ids: List[int]) -> List[Dict[str, Any]]:
        if not receipt_ids:
            return []
        receipts = db.query(Receipt).filter(Receipt.id.in_(receipt_ids)).all()
        receipts.sort(key=lambda r: r.total or 0.0, reverse=True)
        sources = []
        for r in receipts[:10]:
            sources.append({
                "receipt_id": r.id,
                "merchant_name": r.merchant_name or "Unknown",
                "receipt_date": r.receipt_date or "",
                "total": r.total or 0.0,
                "category": r.category or "Other",
                "snippet": f"{r.merchant_name or 'Unknown'} — {r.receipt_date or ''} — ₹{(r.total or 0.0):.2f}"
            })
        return sources

    # ------------------------------------------------------------------
    # Hybrid retrieval path for exploratory / non-analytical questions
    # (unchanged in spirit from the original implementation).
    # ------------------------------------------------------------------
    def _answer_retrieval(
        self, db: Session, user_id: int, question: str,
        merchant_filter: Optional[str], category_filter: Optional[str],
        min_amount: Optional[float], max_amount: Optional[float],
        start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, Any]:
        context_items = retriever.retrieve(
            db=db, user_id=user_id, query=question, top_k=5,
            merchant_filter=merchant_filter, category_filter=category_filter,
            min_amount=min_amount, max_amount=max_amount,
            start_date=start_date, end_date=end_date
        )

        if not context_items:
            return {"answer": "I couldn't find a matching receipt in your ReceiptRAG library.", "sources": [], "breakdown": None}

        answer_text = ""
        if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 5:
            try:
                answer_text = self._generate_openai_answer(question, context_items)
            except Exception as e:
                print(f"OpenAI RAG generation error ({str(e)}), using local synthesizer.")

        if not answer_text:
            answer_text = self._generate_local_answer(question, context_items)

        sources = [
            {
                "receipt_id": item["receipt_id"],
                "merchant_name": item["merchant_name"],
                "receipt_date": item["receipt_date"],
                "total": item["total"],
                "category": item["category"],
                "snippet": f"{item['merchant_name']} — {item['receipt_date']} — ₹{item['total']:.2f}"
            }
            for item in context_items
        ]

        return {"answer": answer_text, "sources": sources, "breakdown": None}

    def _generate_openai_answer(self, question: str, context_items: list) -> str:
        prompt_content = build_rag_user_prompt(question, context_items)
        return self._call_openai_chat(RAG_SYSTEM_PROMPT, prompt_content)

    def _generate_local_answer(self, question: str, context_items: list) -> str:
        """Deterministic local synthesis for exploratory questions — lists the
        matching receipts individually rather than summing their totals,
        since a set of retrieved receipts is not itself a verified aggregate."""
        lines = [f"Here are the {len(context_items)} receipt(s) in your ReceiptRAG library that best match your question:", ""]
        for item in context_items:
            lines.append(f"- **{item['merchant_name']}** ({item['receipt_date']}): ₹{item['total']:,.2f} [{item['category']}]")
        return "\n".join(lines)

    def _call_openai_chat(self, system_prompt: str, user_prompt: str) -> str:
        req_data = json.dumps({
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=req_data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]


rag_service = RAGService()
