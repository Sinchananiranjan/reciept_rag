from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import User
from app.schemas.analytics import AnalyticsOverview, MonthlyReview, YearlyReview, AvailablePeriods
from app.api.auth import get_current_user
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return analytics_service.get_overview(db, current_user.id)

@router.get("/available-periods", response_model=AvailablePeriods)
def get_available_periods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Years/months for which the user actually has receipts, so the UI
    never offers a period with nothing to show."""
    return analytics_service.get_available_periods(db, current_user.id)

@router.get("/monthly", response_model=MonthlyReview)
def get_monthly_review(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return analytics_service.get_monthly_review(db, current_user.id, year, month)

@router.get("/yearly", response_model=YearlyReview)
def get_yearly_review(
    year: int = Query(default_factory=lambda: date.today().year),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return analytics_service.get_yearly_review(db, current_user.id, year)
