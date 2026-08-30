from datetime import date as date_cls, datetime
from calendar import monthrange
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Receipt, ReceiptItem
from app.utils.date_utils import receipt_effective_date
from app.schemas.analytics import (
    SpendingSummary,
    CategoryBreakdownItem,
    MerchantBreakdownItem,
    SpendingTrendPoint,
    MonthlyAnalyticsPoint,
    YearlyAnalyticsPoint,
    AIInsightItem,
    AnalyticsOverview,
    ItemBreakdownItem,
    ComparisonStat,
    DailyTrendPoint,
    MonthTrendPoint,
    MonthlyReview,
    YearlyReview,
    AvailablePeriods,
)

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FULL_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
                     "August", "September", "October", "November", "December"]


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100.0, 1)


class AnalyticsService:
    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _dated_receipts(self, db: Session, user_id: int) -> List[tuple]:
        """Returns (receipt, effective_date) pairs for every receipt owned by
        the user, using receipt_date (falling back to upload date) so all
        time-based views are anchored to the receipt's own date, not the
        moment it happened to be uploaded/processed."""
        receipts = db.query(Receipt).filter(Receipt.user_id == user_id).all()
        return [(r, receipt_effective_date(r)) for r in receipts]

    def _item_breakdown_for_receipt_ids(self, db: Session, receipt_ids: List[int], limit: int = 15) -> List[ItemBreakdownItem]:
        if not receipt_ids:
            return []
        items = db.query(ReceiptItem).filter(ReceiptItem.receipt_id.in_(receipt_ids)).all()
        grouped: Dict[str, Dict[str, Any]] = {}
        for it in items:
            name = (it.product_name or "Item").strip()
            key = name.lower()
            if key not in grouped:
                grouped[key] = {"display_name": name, "count": 0, "qty": 0.0, "amount": 0.0}
            amount = it.total_price if it.total_price is not None else (
                (it.unit_price or 0.0) * (it.quantity or 1.0) if it.unit_price is not None else 0.0
            )
            grouped[key]["count"] += 1
            grouped[key]["qty"] += it.quantity or 1.0
            grouped[key]["amount"] += amount or 0.0

        breakdown = [
            ItemBreakdownItem(
                product_name=d["display_name"],
                purchase_count=d["count"],
                total_quantity=round(d["qty"], 2),
                total_amount=round(d["amount"], 2),
                avg_price=round(d["amount"] / d["qty"], 2) if d["qty"] else 0.0
            )
            for d in grouped.values()
        ]
        breakdown.sort(key=lambda x: x.total_amount, reverse=True)
        return breakdown[:limit]

    def _category_breakdown(self, receipts: List[Receipt]) -> List[CategoryBreakdownItem]:
        total = sum(r.total or 0.0 for r in receipts)
        cat_map: Dict[str, Dict[str, Any]] = {}
        for r in receipts:
            c = r.category or "Other"
            cat_map.setdefault(c, {"amount": 0.0, "count": 0})
            cat_map[c]["amount"] += r.total or 0.0
            cat_map[c]["count"] += 1
        out = [
            CategoryBreakdownItem(
                category=cat,
                amount=round(d["amount"], 2),
                percentage=round((d["amount"] / total * 100.0) if total > 0 else 0.0, 1),
                count=d["count"]
            )
            for cat, d in cat_map.items()
        ]
        out.sort(key=lambda x: x.amount, reverse=True)
        return out

    def _store_breakdown(self, receipts: List[Receipt]) -> List[MerchantBreakdownItem]:
        m_map: Dict[str, Dict[str, Any]] = {}
        for r in receipts:
            m = r.merchant_name or "Unknown Merchant"
            m_map.setdefault(m, {"amount": 0.0, "count": 0})
            m_map[m]["amount"] += r.total or 0.0
            m_map[m]["count"] += 1
        out = [
            MerchantBreakdownItem(merchant=m, amount=round(d["amount"], 2), count=d["count"])
            for m, d in m_map.items()
        ]
        out.sort(key=lambda x: x.amount, reverse=True)
        return out

    # ------------------------------------------------------------------
    # Legacy overview (Dashboard quick-glance) — now date-corrected
    # ------------------------------------------------------------------
    def get_overview(self, db: Session, user_id: int) -> AnalyticsOverview:
        dated = self._dated_receipts(db, user_id)
        receipts = [r for r, _ in dated]

        if not receipts:
            return AnalyticsOverview(
                summary=SpendingSummary(
                    total_spending=0.0, total_receipts=0, avg_receipt_amount=0.0,
                    highest_purchase=0.0, current_month_spending=0.0, current_year_spending=0.0
                ),
                categories=[], merchants=[], trends=[], monthly_analytics=[], yearly_analytics=[],
                highest_spending_month=None, highest_spending_year=None, payment_methods=[],
                insights=[AIInsightItem(
                    title="No receipts yet.",
                    description="Upload your first receipt image/PDF or enter a receipt manually to start tracking spending analytics.",
                    type="tip"
                )]
            )

        today = date_cls.today()
        totals = [r.total or 0.0 for r in receipts]
        total_spending = sum(totals)
        total_count = len(receipts)
        avg_amount = total_spending / total_count if total_count > 0 else 0.0
        highest_purchase = max(totals) if totals else 0.0

        current_month_spending = sum(
            r.total or 0.0 for r, d in dated if d and d.year == today.year and d.month == today.month
        )
        current_year_spending = sum(
            r.total or 0.0 for r, d in dated if d and d.year == today.year
        )

        summary = SpendingSummary(
            total_spending=round(total_spending, 2),
            total_receipts=total_count,
            avg_receipt_amount=round(avg_amount, 2),
            highest_purchase=round(highest_purchase, 2),
            current_month_spending=round(current_month_spending, 2),
            current_year_spending=round(current_year_spending, 2)
        )

        categories = self._category_breakdown(receipts)
        merchants = self._store_breakdown(receipts)

        # Monthly analytics (by actual receipt date)
        monthly_map: Dict[str, Dict[str, Any]] = {}
        for r, d in dated:
            if not d:
                continue
            key = f"{d.year}-{d.month:02d}"
            if key not in monthly_map:
                monthly_map[key] = {
                    "month_name": f"{MONTH_NAMES[d.month - 1]} {d.year}",
                    "year": d.year, "month_num": d.month, "amount": 0.0,
                    "receipt_count": 0, "categories": {}
                }
            amt = r.total or 0.0
            cat = r.category or "Other"
            monthly_map[key]["amount"] += amt
            monthly_map[key]["receipt_count"] += 1
            monthly_map[key]["categories"][cat] = monthly_map[key]["categories"].get(cat, 0.0) + amt

        monthly_analytics = [
            MonthlyAnalyticsPoint(
                month_name=d["month_name"], year=d["year"], amount=round(d["amount"], 2),
                receipt_count=d["receipt_count"],
                category_breakdown={k: round(v, 2) for k, v in d["categories"].items()}
            )
            for d in (monthly_map[k] for k in sorted(monthly_map.keys()))
        ]
        highest_spending_month = max(monthly_analytics, key=lambda x: x.amount).month_name if monthly_analytics else None

        # Yearly analytics
        yearly_map: Dict[int, Dict[str, Any]] = {}
        for r, d in dated:
            if not d:
                continue
            yearly_map.setdefault(d.year, {"amount": 0.0, "receipt_count": 0, "categories": {}})
            amt = r.total or 0.0
            cat = r.category or "Other"
            yearly_map[d.year]["amount"] += amt
            yearly_map[d.year]["receipt_count"] += 1
            yearly_map[d.year]["categories"][cat] = yearly_map[d.year]["categories"].get(cat, 0.0) + amt

        yearly_analytics = [
            YearlyAnalyticsPoint(
                year=y, amount=round(yearly_map[y]["amount"], 2), receipt_count=yearly_map[y]["receipt_count"],
                category_breakdown={k: round(v, 2) for k, v in yearly_map[y]["categories"].items()}
            )
            for y in sorted(yearly_map.keys())
        ]
        highest_spending_year = max(yearly_analytics, key=lambda x: x.amount).year if yearly_analytics else None

        # Daily trend points (by actual receipt date, falls back to upload date)
        t_map: Dict[str, Dict[str, Any]] = {}
        for r, d in dated:
            label = d.isoformat() if d else "Unknown"
            t_map.setdefault(label, {"amount": 0.0, "count": 0})
            t_map[label]["amount"] += r.total or 0.0
            t_map[label]["count"] += 1
        trends = [
            SpendingTrendPoint(date_label=lbl, amount=round(v["amount"], 2), count=v["count"])
            for lbl, v in t_map.items()
        ]
        trends.sort(key=lambda x: x.date_label)

        pm_map: Dict[str, float] = {}
        for r in receipts:
            pm = r.payment_method or "Other"
            pm_map[pm] = pm_map.get(pm, 0.0) + (r.total or 0.0)
        payment_methods = [{"method": pm, "amount": round(amt, 2)} for pm, amt in pm_map.items()]

        insights = []
        if categories:
            top_cat = categories[0]
            insights.append(AIInsightItem(
                title=f"Top Category: {top_cat.category}",
                description=f"{top_cat.category} represents {top_cat.percentage}% of total expenses (₹{top_cat.amount:,.2f}).",
                type="stat"
            ))
        if merchants:
            top_m = merchants[0]
            insights.append(AIInsightItem(
                title=f"Top Merchant: {top_m.merchant}",
                description=f"{top_m.count} receipt(s) recorded at {top_m.merchant} totaling ₹{top_m.amount:,.2f}.",
                type="trend"
            ))
        if highest_spending_month:
            insights.append(AIInsightItem(
                title=f"Highest Spending Month: {highest_spending_month}",
                description=f"Your highest spending month is {highest_spending_month}.",
                type="warning"
            ))

        return AnalyticsOverview(
            summary=summary, categories=categories, merchants=merchants[:10], trends=trends,
            monthly_analytics=monthly_analytics, yearly_analytics=yearly_analytics,
            highest_spending_month=highest_spending_month, highest_spending_year=highest_spending_year,
            payment_methods=payment_methods, insights=insights
        )

    # ------------------------------------------------------------------
    # Available periods (drives the month/year pickers with real data only)
    # ------------------------------------------------------------------
    def get_available_periods(self, db: Session, user_id: int) -> AvailablePeriods:
        dated = self._dated_receipts(db, user_id)
        months_by_year: Dict[int, set] = {}
        for _, d in dated:
            if not d:
                continue
            months_by_year.setdefault(d.year, set()).add(d.month)
        years = sorted(months_by_year.keys(), reverse=True)
        return AvailablePeriods(
            years=years,
            months_by_year={y: sorted(months_by_year[y], reverse=True) for y in years}
        )

    # ------------------------------------------------------------------
    # Monthly Review
    # ------------------------------------------------------------------
    def get_monthly_review(self, db: Session, user_id: int, year: int, month: int) -> MonthlyReview:
        dated = self._dated_receipts(db, user_id)
        month_receipts = [(r, d) for r, d in dated if d and d.year == year and d.month == month]

        # Previous month, for the month-over-month comparison
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        prev_receipts = [r for r, d in dated if d and d.year == prev_year and d.month == prev_month]

        month_name = f"{FULL_MONTH_NAMES[month - 1]} {year}"

        if not month_receipts:
            spending_comparison = None
            if prev_receipts:
                prev_total = sum(r.total or 0.0 for r in prev_receipts)
                spending_comparison = ComparisonStat(
                    label=f"{MONTH_NAMES[prev_month - 1]} {prev_year}", current=0.0,
                    previous=round(prev_total, 2), change_pct=_pct_change(0.0, prev_total)
                )
            return MonthlyReview(year=year, month=month, month_name=month_name, has_data=False,
                                  spending_comparison=spending_comparison)

        receipts = [r for r, _ in month_receipts]
        receipt_ids = [r.id for r in receipts]
        totals = [r.total or 0.0 for r in receipts]
        total_spending = sum(totals)
        total_receipts = len(receipts)
        avg_purchase = total_spending / total_receipts if total_receipts else 0.0
        top_receipt = max(receipts, key=lambda r: r.total or 0.0)

        total_tax = sum((r.tax or 0.0) for r in receipts)
        total_discount = sum((r.discount or 0.0) for r in receipts)

        categories = self._category_breakdown(receipts)
        stores = self._store_breakdown(receipts)
        top_items = self._item_breakdown_for_receipt_ids(db, receipt_ids)

        # Daily trend across the month's actual calendar days
        days_in_month = monthrange(year, month)[1]
        daily_map: Dict[int, float] = {d: 0.0 for d in range(1, days_in_month + 1)}
        for r, d in month_receipts:
            daily_map[d.day] += r.total or 0.0
        daily_trend = [
            DailyTrendPoint(day=day, date_label=f"{day}", amount=round(amt, 2))
            for day, amt in sorted(daily_map.items())
        ]

        prev_total = sum(r.total or 0.0 for r in prev_receipts)
        spending_comparison = ComparisonStat(
            label=f"{MONTH_NAMES[prev_month - 1]} {prev_year}",
            current=round(total_spending, 2), previous=round(prev_total, 2),
            change_pct=_pct_change(total_spending, prev_total)
        ) if prev_receipts or total_spending else None

        receipts_comparison = ComparisonStat(
            label=f"{MONTH_NAMES[prev_month - 1]} {prev_year}",
            current=total_receipts, previous=len(prev_receipts),
            change_pct=_pct_change(total_receipts, len(prev_receipts))
        ) if prev_receipts or total_receipts else None

        insights: List[AIInsightItem] = []
        if categories:
            top_cat = categories[0]
            insights.append(AIInsightItem(
                title=f"{top_cat.category} was your biggest category",
                description=f"₹{top_cat.amount:,.2f} across {top_cat.count} receipt(s), {top_cat.percentage}% of the month's spending.",
                type="stat"
            ))
        if spending_comparison and spending_comparison.change_pct is not None:
            direction = "up" if spending_comparison.change_pct >= 0 else "down"
            insights.append(AIInsightItem(
                title=f"Spending is {direction} {abs(spending_comparison.change_pct)}% vs last month",
                description=f"₹{total_spending:,.2f} this month compared to ₹{prev_total:,.2f} in {spending_comparison.label}.",
                type="trend" if direction == "down" else "warning"
            ))
        if top_items:
            insights.append(AIInsightItem(
                title=f"Most purchased: {top_items[0].product_name}",
                description=f"Bought {top_items[0].purchase_count} time(s), totaling ₹{top_items[0].total_amount:,.2f}.",
                type="tip"
            ))

        return MonthlyReview(
            year=year, month=month, month_name=month_name, has_data=True,
            total_spending=round(total_spending, 2), total_receipts=total_receipts,
            avg_purchase=round(avg_purchase, 2), highest_purchase=round(top_receipt.total or 0.0, 2),
            highest_purchase_merchant=top_receipt.merchant_name,
            total_tax=round(total_tax, 2), total_discount=round(total_discount, 2),
            categories=categories, stores=stores, top_items=top_items, daily_trend=daily_trend,
            spending_comparison=spending_comparison, receipts_comparison=receipts_comparison,
            insights=insights
        )

    # ------------------------------------------------------------------
    # Yearly Review
    # ------------------------------------------------------------------
    def get_yearly_review(self, db: Session, user_id: int, year: int) -> YearlyReview:
        dated = self._dated_receipts(db, user_id)
        year_receipts = [(r, d) for r, d in dated if d and d.year == year]
        prev_year_receipts = [r for r, d in dated if d and d.year == year - 1]

        if not year_receipts:
            spending_comparison = None
            if prev_year_receipts:
                prev_total = sum(r.total or 0.0 for r in prev_year_receipts)
                spending_comparison = ComparisonStat(
                    label=str(year - 1), current=0.0, previous=round(prev_total, 2),
                    change_pct=_pct_change(0.0, prev_total)
                )
            return YearlyReview(year=year, has_data=False, spending_comparison=spending_comparison)

        receipts = [r for r, _ in year_receipts]
        receipt_ids = [r.id for r in receipts]
        totals = [r.total or 0.0 for r in receipts]
        total_spending = sum(totals)
        total_receipts = len(receipts)
        avg_purchase = total_spending / total_receipts if total_receipts else 0.0
        highest_purchase = max(totals) if totals else 0.0

        total_tax = sum((r.tax or 0.0) for r in receipts)
        total_discount = sum((r.discount or 0.0) for r in receipts)

        categories = self._category_breakdown(receipts)
        stores = self._store_breakdown(receipts)
        top_items = self._item_breakdown_for_receipt_ids(db, receipt_ids)

        monthly_map: Dict[int, Dict[str, Any]] = {m: {"amount": 0.0, "count": 0} for m in range(1, 13)}
        for r, d in year_receipts:
            monthly_map[d.month]["amount"] += r.total or 0.0
            monthly_map[d.month]["count"] += 1
        monthly_trend = [
            MonthTrendPoint(month=m, month_name=MONTH_NAMES[m - 1], amount=round(v["amount"], 2), receipt_count=v["count"])
            for m, v in monthly_map.items()
        ]

        months_with_data = [mt for mt in monthly_trend if mt.receipt_count > 0]
        highest_spending_month = max(months_with_data, key=lambda x: x.amount).month_name if months_with_data else None
        lowest_spending_month = min(months_with_data, key=lambda x: x.amount).month_name if months_with_data else None

        prev_total = sum(r.total or 0.0 for r in prev_year_receipts)
        spending_comparison = ComparisonStat(
            label=str(year - 1), current=round(total_spending, 2), previous=round(prev_total, 2),
            change_pct=_pct_change(total_spending, prev_total)
        ) if prev_year_receipts or total_spending else None

        insights: List[AIInsightItem] = []
        if categories:
            top_cat = categories[0]
            insights.append(AIInsightItem(
                title=f"{top_cat.category} led your spending in {year}",
                description=f"₹{top_cat.amount:,.2f} total, {top_cat.percentage}% of the year's expenses.",
                type="stat"
            ))
        if highest_spending_month:
            insights.append(AIInsightItem(
                title=f"Peak month: {highest_spending_month}",
                description=f"{highest_spending_month} was your highest spending month of {year}.",
                type="trend"
            ))
        if spending_comparison and spending_comparison.change_pct is not None:
            direction = "up" if spending_comparison.change_pct >= 0 else "down"
            insights.append(AIInsightItem(
                title=f"Spending is {direction} {abs(spending_comparison.change_pct)}% vs {year - 1}",
                description=f"₹{total_spending:,.2f} in {year} compared to ₹{prev_total:,.2f} in {year - 1}.",
                type="warning" if direction == "up" else "tip"
            ))

        return YearlyReview(
            year=year, has_data=True, total_spending=round(total_spending, 2), total_receipts=total_receipts,
            avg_purchase=round(avg_purchase, 2), highest_purchase=round(highest_purchase, 2),
            total_tax=round(total_tax, 2), total_discount=round(total_discount, 2),
            monthly_trend=monthly_trend, categories=categories, stores=stores, top_items=top_items,
            highest_spending_month=highest_spending_month, lowest_spending_month=lowest_spending_month,
            spending_comparison=spending_comparison, insights=insights
        )


analytics_service = AnalyticsService()
