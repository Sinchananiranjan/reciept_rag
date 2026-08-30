from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SpendingSummary(BaseModel):
    total_spending: float
    total_receipts: int
    avg_receipt_amount: float
    highest_purchase: float
    current_month_spending: float
    current_year_spending: float
    currency: str = "INR"

class CategoryBreakdownItem(BaseModel):
    category: str
    amount: float
    percentage: float
    count: int

class MerchantBreakdownItem(BaseModel):
    merchant: str
    amount: float
    count: int

class SpendingTrendPoint(BaseModel):
    date_label: str
    amount: float
    count: int

class MonthlyAnalyticsPoint(BaseModel):
    month_name: str
    year: int
    amount: float
    receipt_count: int
    category_breakdown: Dict[str, float] = {}

class YearlyAnalyticsPoint(BaseModel):
    year: int
    amount: float
    receipt_count: int
    category_breakdown: Dict[str, float] = {}

class AIInsightItem(BaseModel):
    title: str
    description: str
    type: str  # "trend", "warning", "stat", "tip"

class AnalyticsOverview(BaseModel):
    summary: SpendingSummary
    categories: List[CategoryBreakdownItem]
    merchants: List[MerchantBreakdownItem]
    trends: List[SpendingTrendPoint]
    monthly_analytics: List[MonthlyAnalyticsPoint]
    yearly_analytics: List[YearlyAnalyticsPoint]
    highest_spending_month: Optional[str] = None
    highest_spending_year: Optional[int] = None
    payment_methods: List[Dict[str, Any]]
    insights: List[AIInsightItem]


class ItemBreakdownItem(BaseModel):
    product_name: str
    purchase_count: int
    total_quantity: float
    total_amount: float
    avg_price: float


class ComparisonStat(BaseModel):
    label: str
    current: float
    previous: float
    change_pct: Optional[float] = None


class DailyTrendPoint(BaseModel):
    day: int
    date_label: str
    amount: float


class MonthTrendPoint(BaseModel):
    month: int
    month_name: str
    amount: float
    receipt_count: int


class MonthlyReview(BaseModel):
    year: int
    month: int
    month_name: str
    has_data: bool
    total_spending: float = 0.0
    total_receipts: int = 0
    avg_purchase: float = 0.0
    highest_purchase: float = 0.0
    highest_purchase_merchant: Optional[str] = None
    total_tax: float = 0.0
    total_discount: float = 0.0
    categories: List[CategoryBreakdownItem] = []
    stores: List[MerchantBreakdownItem] = []
    top_items: List[ItemBreakdownItem] = []
    daily_trend: List[DailyTrendPoint] = []
    spending_comparison: Optional[ComparisonStat] = None
    receipts_comparison: Optional[ComparisonStat] = None
    insights: List[AIInsightItem] = []


class YearlyReview(BaseModel):
    year: int
    has_data: bool
    total_spending: float = 0.0
    total_receipts: int = 0
    avg_purchase: float = 0.0
    highest_purchase: float = 0.0
    total_tax: float = 0.0
    total_discount: float = 0.0
    monthly_trend: List[MonthTrendPoint] = []
    categories: List[CategoryBreakdownItem] = []
    stores: List[MerchantBreakdownItem] = []
    top_items: List[ItemBreakdownItem] = []
    highest_spending_month: Optional[str] = None
    lowest_spending_month: Optional[str] = None
    spending_comparison: Optional[ComparisonStat] = None
    insights: List[AIInsightItem] = []


class AvailablePeriods(BaseModel):
    years: List[int] = []
    months_by_year: Dict[int, List[int]] = {}
