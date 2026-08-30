"""Shared date parsing for receipt_date strings.

receipt_date is stored as free text — produced either by OCR extraction
(various formats depending on the receipt) or typed by the user in the
manual-entry form (always "YYYY-MM-DD" from the date input). Analytics and
RAG both need a real `date` to group/filter by, so this is the single place
that turns that free text into a `date` object.
"""
import re
from datetime import date, datetime
from typing import Optional

MONTH_NAME_TO_NUM = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def _expand_year(y: int) -> int:
    if y < 100:
        return 2000 + y if y < 70 else 1900 + y
    return y


def parse_flexible_date(date_str: Optional[str]) -> Optional[date]:
    """Parses a receipt_date string in any of the formats our extraction/manual
    entry paths produce. Returns None if it can't be confidently parsed
    (never guesses/fabricates a date)."""
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip()

    # ISO: YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    # DD-Mon-YYYY / DD Mon YYYY (e.g. "25-Aug-2026", "25 Aug 2026")
    m = re.match(r"^(\d{1,2})[-\s]([A-Za-z]{3,9})[-\s](\d{2,4})$", s)
    if m:
        mon = MONTH_NAME_TO_NUM.get(m.group(2).lower())
        if mon:
            try:
                return date(_expand_year(int(m.group(3))), mon, int(m.group(1)))
            except ValueError:
                return None

    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY (Indian receipts: day-first)
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$", s)
    if m:
        day, mon, yr = int(m.group(1)), int(m.group(2)), _expand_year(int(m.group(3)))
        # If the "day" component is > 12 it can't be a month either way; if the
        # "month" component is > 12, the fields must actually be swapped.
        if mon > 12 and day <= 12:
            day, mon = mon, day
        try:
            return date(yr, mon, day)
        except ValueError:
            return None

    return None


def receipt_effective_date(receipt) -> Optional[date]:
    """The date to use for analytics/RAG grouping: the receipt's own
    receipt_date when parseable, otherwise the upload/creation date as a
    fallback so the record isn't silently dropped from time-based views."""
    parsed = parse_flexible_date(getattr(receipt, "receipt_date", None))
    if parsed:
        return parsed
    created = getattr(receipt, "created_at", None)
    if created:
        return created.date() if isinstance(created, datetime) else created
    return None
