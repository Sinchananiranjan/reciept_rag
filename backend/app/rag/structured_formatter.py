"""Turns a verified StructuredResult (already computed straight from the
database) into the chat answer text and an optional breakdown table for the
frontend. This is the ONLY place that decides what the numbers mean in
words — the numbers themselves never change here."""
from typing import Optional, Tuple
from app.services.query_analyzer import QueryFilters
from app.services.structured_query_service import StructuredResult


def _date_phrase(filters: QueryFilters) -> str:
    return f" in {filters.date_label}" if filters.date_label else ""


def _merchant_phrase(filters: QueryFilters) -> str:
    return f" at {filters.merchant}" if filters.merchant else ""


def _category_phrase(filters: QueryFilters) -> str:
    return f" in the {filters.category} category" if filters.category else ""


def format_structured_answer(filters: QueryFilters, result: StructuredResult) -> Tuple[str, Optional[dict]]:
    date_p = _date_phrase(filters)
    merchant_p = _merchant_phrase(filters)
    category_p = _category_phrase(filters)

    if result.mode == "empty":
        what = f"'{filters.item_keyword}'" if filters.item_keyword else "purchases"
        return (
            f"I couldn't find any {what}{merchant_p}{category_p}{date_p} in your receipts. "
            "Try a different item name, store, or time period.",
            None
        )

    if result.mode == "item":
        variants = result.breakdown
        lines = [
            f"You bought **{filters.item_keyword}** {result.purchase_count} time(s){date_p}"
            f"{merchant_p}{category_p}, totaling **{result.total_quantity:g} unit(s)** for "
            f"**₹{result.total_amount:,.2f}** across {result.receipt_count} receipt(s)."
        ]
        if len(variants) > 1:
            lines.append(f"That breaks down into {len(variants)} distinct product(s) — see the table below.")
        if filters.wants_average:
            lines.append(f"Average price per unit: ₹{result.average:,.2f}.")
        if filters.wants_highest and variants:
            top = variants[0]
            lines.append(f"Highest total: **{top.name}** at ₹{top.total_amount:,.2f} ({top.purchase_count} purchase(s)).")
        if filters.wants_lowest and variants:
            bottom = variants[-1]
            lines.append(f"Lowest total: **{bottom.name}** at ₹{bottom.total_amount:,.2f}.")

        breakdown = {
            "title": f"'{filters.item_keyword.title()}' purchases{date_p}",
            "columns": ["Product", "Purchases", "Quantity", "Total (₹)", "Avg Price (₹)"],
            "rows": [
                [row.name, str(row.purchase_count), f"{row.quantity:g}", f"{row.total_amount:,.2f}", f"{row.avg_price:,.2f}"]
                for row in variants
            ]
        }
        return "\n".join(lines), breakdown

    # mode == "receipt"
    total_line = (
        f"You spent **₹{result.total_amount:,.2f}** across **{result.receipt_count} receipt(s)**"
        f"{merchant_p}{category_p}{date_p}. Average per receipt: ₹{result.average:,.2f}."
    )
    tax_line = f"Total tax paid: ₹{result.tax_total:,.2f}." if (filters.wants_tax or result.tax_total > 0) else None
    discount_line = (
        f"Total discount received: ₹{result.discount_total:,.2f}."
        if (filters.wants_discount or result.discount_total > 0) else None
    )
    highest_line = None
    if result.highest:
        highest_line = (
            f"Highest single purchase: **{result.highest.merchant_name or 'Unknown'}** — "
            f"₹{(result.highest.total or 0):,.2f}" + (f" on {result.highest.receipt_date}" if result.highest.receipt_date else "") + "."
        )
    lowest_line = None
    if result.lowest and (result.highest is None or result.lowest.id != result.highest.id):
        lowest_line = f"Lowest single purchase: **{result.lowest.merchant_name or 'Unknown'}** — ₹{(result.lowest.total or 0):,.2f}."

    # Lead with whichever fact the question actually asked for; the overall
    # total is always included, just not necessarily first.
    if filters.wants_highest:
        lines = [l for l in [highest_line, total_line, lowest_line if filters.wants_lowest else None, tax_line, discount_line] if l]
    elif filters.wants_lowest:
        lines = [l for l in [lowest_line, total_line, tax_line, discount_line] if l]
    elif (filters.wants_tax and not filters.wants_discount):
        lines = [l for l in [tax_line, total_line, discount_line, highest_line] if l]
    elif (filters.wants_discount and not filters.wants_tax):
        lines = [l for l in [discount_line, total_line, tax_line, highest_line] if l]
    else:
        lines = [l for l in [total_line, tax_line, discount_line, highest_line] if l]

    breakdown = None
    if result.secondary_breakdown:
        breakdown = {
            "title": f"Spending by {result.secondary_label}{date_p}",
            "columns": [result.secondary_label, "Receipts", "Total (₹)"],
            "rows": [
                [row.name, str(row.purchase_count), f"{row.total_amount:,.2f}"]
                for row in result.secondary_breakdown
            ]
        }

    return "\n".join(lines), breakdown
