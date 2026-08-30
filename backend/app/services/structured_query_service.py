"""Structured-first aggregation for analytical chat questions.

For any question the query_analyzer classifies as analytical (spend/count/
average/breakdown-style), this module queries and aggregates the database
directly — it never asks the LLM to add up numbers from retrieved text. The
LLM (when configured) is only ever handed the already-computed result to
phrase in natural language; it cannot alter the figures.

Key correctness rules enforced here:
  * Item-level questions (e.g. "how much did I spend on milk") sum
    ReceiptItem.total_price (falling back to unit_price * quantity) — never
    Receipt.total — so a receipt with 5 items only contributes its milk
    line, not its whole total. This also means a single receipt can never
    be double-counted across multiple item rows in the same breakdown.
  * Product variants are grouped by their literal (trimmed/cased) name, so
    "Regular Milk", "Almond Milk", and "Oat Milk" are always distinct rows
    and are never merged into one "milk" bucket.
  * Receipt-level questions (merchant/category/date only, no item keyword)
    sum Receipt.total exactly once per receipt.
  * All date filtering uses each receipt's own effective date
    (receipt_date, falling back to upload date only when unparseable).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Receipt, ReceiptItem
from app.utils.date_utils import receipt_effective_date
from app.services.query_analyzer import QueryFilters


@dataclass
class BreakdownRow:
    name: str
    purchase_count: int
    quantity: float
    total_amount: float
    avg_price: float


@dataclass
class StructuredResult:
    mode: str  # "item" | "receipt" | "empty"
    total_amount: float = 0.0
    total_quantity: Optional[float] = None
    purchase_count: int = 0
    receipt_count: int = 0
    average: float = 0.0
    tax_total: float = 0.0
    discount_total: float = 0.0
    highest: Optional[Receipt] = None
    lowest: Optional[Receipt] = None
    breakdown: List[BreakdownRow] = field(default_factory=list)
    secondary_breakdown: List[BreakdownRow] = field(default_factory=list)
    secondary_label: str = ""
    receipt_ids: List[int] = field(default_factory=list)


def _group_items(items: List[ReceiptItem]) -> List[BreakdownRow]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for it in items:
        name = (it.product_name or "Item").strip()
        key = name.lower()
        if key not in grouped:
            grouped[key] = {"display": name, "count": 0, "qty": 0.0, "amount": 0.0}
        amount = it.total_price if it.total_price is not None else (
            (it.unit_price or 0.0) * (it.quantity or 1.0) if it.unit_price is not None else 0.0
        )
        grouped[key]["count"] += 1
        grouped[key]["qty"] += it.quantity or 1.0
        grouped[key]["amount"] += amount or 0.0

    rows = [
        BreakdownRow(
            name=d["display"], purchase_count=d["count"], quantity=round(d["qty"], 2),
            total_amount=round(d["amount"], 2),
            avg_price=round(d["amount"] / d["qty"], 2) if d["qty"] else round(d["amount"], 2)
        )
        for d in grouped.values()
    ]
    rows.sort(key=lambda r: r.total_amount, reverse=True)
    return rows


def _group_receipts_by(receipts: List[Receipt], key_fn) -> List[BreakdownRow]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for r in receipts:
        k = key_fn(r) or "Unknown"
        grouped.setdefault(k, {"count": 0, "amount": 0.0})
        grouped[k]["count"] += 1
        grouped[k]["amount"] += r.total or 0.0
    rows = [
        BreakdownRow(name=k, purchase_count=d["count"], quantity=0.0,
                      total_amount=round(d["amount"], 2),
                      avg_price=round(d["amount"] / d["count"], 2) if d["count"] else 0.0)
        for k, d in grouped.items()
    ]
    rows.sort(key=lambda r: r.total_amount, reverse=True)
    return rows


def run_structured_query(db: Session, user_id: int, filters: QueryFilters) -> StructuredResult:
    all_receipts = db.query(Receipt).filter(Receipt.user_id == user_id).all()
    dated = [(r, receipt_effective_date(r)) for r in all_receipts]

    if filters.start_date and filters.end_date:
        dated = [(r, d) for r, d in dated if d and filters.start_date <= d <= filters.end_date]

    receipts = [r for r, _ in dated]

    if filters.merchant:
        receipts = [r for r in receipts if (r.merchant_name or "").strip().lower() == filters.merchant.strip().lower()]
    if filters.category:
        receipts = [r for r in receipts if (r.category or "").strip().lower() == filters.category.strip().lower()]

    if not receipts:
        return StructuredResult(mode="empty")

    if filters.item_keyword:
        receipt_ids = [r.id for r in receipts]
        items = db.query(ReceiptItem).filter(ReceiptItem.receipt_id.in_(receipt_ids)).all()
        kw = filters.item_keyword.strip().lower()
        matched = [it for it in items if kw in (it.product_name or "").lower()]

        if not matched:
            return StructuredResult(mode="empty")

        breakdown = _group_items(matched)
        total_amount = sum(row.total_amount for row in breakdown)
        total_quantity = sum(row.quantity for row in breakdown)
        purchase_count = len(matched)
        matched_receipt_ids = list({it.receipt_id for it in matched})

        return StructuredResult(
            mode="item",
            total_amount=round(total_amount, 2),
            total_quantity=round(total_quantity, 2),
            purchase_count=purchase_count,
            receipt_count=len(matched_receipt_ids),
            average=round(total_amount / total_quantity, 2) if total_quantity else (
                round(total_amount / purchase_count, 2) if purchase_count else 0.0
            ),
            breakdown=breakdown,
            receipt_ids=matched_receipt_ids,
        )

    # Receipt-level aggregation (merchant/category/date filters only)
    total_amount = sum(r.total or 0.0 for r in receipts)
    receipt_count = len(receipts)
    tax_total = sum(r.tax or 0.0 for r in receipts)
    discount_total = sum(r.discount or 0.0 for r in receipts)
    highest = max(receipts, key=lambda r: r.total or 0.0)
    lowest = min(receipts, key=lambda r: r.total or 0.0)

    if filters.merchant and not filters.category:
        secondary = _group_receipts_by(receipts, lambda r: r.category or "Other")
        secondary_label = "Category"
    elif filters.category and not filters.merchant:
        secondary = _group_receipts_by(receipts, lambda r: r.merchant_name or "Unknown Merchant")
        secondary_label = "Store"
    else:
        secondary = _group_receipts_by(receipts, lambda r: r.category or "Other")
        secondary_label = "Category"

    return StructuredResult(
        mode="receipt",
        total_amount=round(total_amount, 2),
        purchase_count=receipt_count,
        receipt_count=receipt_count,
        average=round(total_amount / receipt_count, 2) if receipt_count else 0.0,
        tax_total=round(tax_total, 2),
        discount_total=round(discount_total, 2),
        highest=highest,
        lowest=lowest,
        secondary_breakdown=secondary,
        secondary_label=secondary_label,
        receipt_ids=[r.id for r in receipts],
    )
