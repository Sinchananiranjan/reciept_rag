"""Turns a natural-language chat question into structured filters (date range,
item keyword, merchant, category, requested statistic) so the RAG pipeline can
query and aggregate the database directly for numerical/analytical questions
instead of relying on the LLM to read totals out of retrieved text chunks.

Merchant/category matching is done against the user's OWN receipts and the
app's fixed category list — never a hardcoded vocabulary of stores or
products, so it generalizes to any user's real data.
"""
import re
import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Receipt
from app.services.categorization_service import CATEGORIES

MONTH_NAME_TO_NUM = {name.lower(): i + 1 for i, name in enumerate(calendar.month_name) if name}
MONTH_NAME_TO_NUM.update({name.lower(): i + 1 for i, name in enumerate(calendar.month_abbr) if name})

_ANALYTICAL_RE = re.compile(
    r"\bhow much\b|\bhow many\b|\btotal\b|\bspend\b|\bspent\b|\bspending\b|\bcost\b|\baverage\b|\bavg\b|"
    r"\bcompare\b|\bcomparison\b|\bbreakdown\b|\bhighest\b|\blowest\b|\bmost expensive\b|\bcheapest\b|"
    r"\bnumber of\b|\bcount\b|\btax\b|\bgst\b|\bdiscount\b|\bquantity\b|\bhow much did i\b",
    re.IGNORECASE
)

_STOPWORD_TAIL_RE = re.compile(
    r"\s+(this|last|in|during|for|since|between|on|at|from|of|please|month|year|\?)\b.*$",
    re.IGNORECASE
)

_LEADING_ARTICLES_RE = re.compile(r"^(the|a|an|any|my|some)\s+", re.IGNORECASE)


@dataclass
class QueryFilters:
    is_analytical: bool = False
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    date_label: Optional[str] = None
    item_keyword: Optional[str] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    wants_count: bool = False
    wants_quantity: bool = False
    wants_average: bool = False
    wants_highest: bool = False
    wants_lowest: bool = False
    wants_tax: bool = False
    wants_discount: bool = False


def _month_range(year: int, month: int) -> Tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _year_range(year: int) -> Tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def _extract_date_range(q: str, today: date) -> Tuple[Optional[date], Optional[date], Optional[str]]:
    ql = q.lower()

    if re.search(r"\bthis month\b", ql):
        s, e = _month_range(today.year, today.month)
        return s, e, f"{calendar.month_name[today.month]} {today.year}"

    if re.search(r"\blast month\b", ql):
        y, m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        s, e = _month_range(y, m)
        return s, e, f"{calendar.month_name[m]} {y}"

    if re.search(r"\bthis year\b", ql):
        s, e = _year_range(today.year)
        return s, e, str(today.year)

    if re.search(r"\blast year\b", ql):
        s, e = _year_range(today.year - 1)
        return s, e, str(today.year - 1)

    if re.search(r"\btoday\b", ql):
        return today, today, "today"

    if re.search(r"\bthis week\b", ql):
        start = date.fromordinal(today.toordinal() - today.weekday())
        return start, today, "this week"

    # "August 2026", "in August", "for Aug"
    m = re.search(
        r"\b(" + "|".join(sorted(MONTH_NAME_TO_NUM.keys(), key=len, reverse=True)) + r")\b(?:\s+(\d{4}))?",
        ql
    )
    if m:
        mon = MONTH_NAME_TO_NUM.get(m.group(1).lower())
        yr = int(m.group(2)) if m.group(2) else today.year
        if mon:
            s, e = _month_range(yr, mon)
            return s, e, f"{calendar.month_name[mon]} {yr}"

    # Bare year mention, e.g. "in 2025"
    m = re.search(r"\b(20\d{2})\b", ql)
    if m:
        yr = int(m.group(1))
        s, e = _year_range(yr)
        return s, e, str(yr)

    return None, None, None


def _extract_item_keyword(ql: str) -> Optional[str]:
    patterns = [
        r"how many times\s+(?:did i |have i )?(?:buy|bought|purchase[d]?)\s+([a-z0-9\s\-']+?)(?:\s+(?:this|last|in|during|for|since|between)\b|\?|$)",
        r"how much (?:did i |have i )?spen[dt]\s+on\s+([a-z0-9\s\-']+?)(?:\s+(?:this|last|in|during|for|since|between)\b|\?|$)",
        r"(?:spend|spent|cost|paid)\s+(?:on|for)\s+([a-z0-9\s\-']+?)(?:\s+(?:this|last|in|during|for|since|between)\b|\?|$)",
        r"how many\s+([a-z0-9\s\-']+?)\s+(?:did i buy|have i bought|did i purchase|have i purchased)\b",
        r"\bbought\s+([a-z0-9\s\-']+?)(?:\s+(?:this|last|in|during|for|since|between)\b|\?|$)",
        r"([a-z0-9\s\-']+?)\s+purchases\b",
        r"\bon\s+([a-z0-9\s\-']+?)(?:\s+(?:this|last|in|during|since|between)\b|\?|$)",
        r"how many\s+([a-z0-9\s\-']+?)(?:\?|$)",
    ]
    for pat in patterns:
        m = re.search(pat, ql)
        if m:
            phrase = m.group(1).strip()
            phrase = _LEADING_ARTICLES_RE.sub("", phrase).strip()
            # Reject phrases that are just question words / too short / too long to be a product
            if phrase and 1 < len(phrase) <= 40 and not re.match(r"^(much|many|i|it|this|that)$", phrase):
                return phrase
    return None


def _extract_merchant(ql: str, db: Session, user_id: int) -> Optional[str]:
    merchants = db.query(Receipt.merchant_name).filter(
        Receipt.user_id == user_id, Receipt.merchant_name.isnot(None)
    ).distinct().all()
    for (name,) in merchants:
        if name and name.lower() in ql:
            return name
    return None


def _extract_category(ql: str) -> Optional[str]:
    for cat in CATEGORIES:
        if cat.lower() in ql:
            return cat
    return None


def analyze_question(question: str, db: Session, user_id: int) -> QueryFilters:
    ql = question.lower().strip()
    today = date.today()

    is_analytical = bool(_ANALYTICAL_RE.search(ql))

    start_date, end_date, date_label = _extract_date_range(ql, today)
    merchant = _extract_merchant(ql, db, user_id)
    category = _extract_category(ql)

    item_keyword = None
    if is_analytical:
        item_keyword = _extract_item_keyword(ql)
        # A matched category/merchant name is not itself a product — don't
        # double-apply it as an item-name filter too.
        if item_keyword and category and item_keyword == category.lower():
            item_keyword = None
        if item_keyword and merchant and item_keyword == merchant.lower():
            item_keyword = None

    return QueryFilters(
        is_analytical=is_analytical,
        start_date=start_date,
        end_date=end_date,
        date_label=date_label,
        item_keyword=item_keyword,
        merchant=merchant,
        category=category,
        wants_count=bool(re.search(r"\bhow many\b|\bnumber of\b|\bcount\b", ql)),
        wants_quantity=bool(re.search(r"\bhow many\b|\bquantity\b|\bunits\b", ql)),
        wants_average=bool(re.search(r"\baverage\b|\bavg\b", ql)),
        wants_highest=bool(re.search(r"\bhighest\b|\bmost expensive\b|\bmax\b|\btop\b|\bmaximum\b", ql)),
        wants_lowest=bool(re.search(r"\blowest\b|\bcheapest\b|\bmin\b|\bminimum\b|\bleast\b", ql)),
        wants_tax=bool(re.search(r"\btax\b|\bgst\b|\bcgst\b|\bsgst\b|\bigst\b", ql)),
        wants_discount=bool(re.search(r"\bdiscount\b|\bsaved\b|\bsavings\b", ql)),
    )
