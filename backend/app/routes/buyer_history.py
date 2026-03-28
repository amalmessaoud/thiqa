import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.models.models import Report, Review, SellerProfile, User
from app.routes.auth import get_current_user

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class HistoryReportItem(BaseModel):
    kind: str = "report"         # discriminator field for the frontend
    id: str
    seller_id: str
    seller_url: str
    scam_type: str
    description: Optional[str]
    screenshot_url: str
    credibility_score: Optional[float]
    created_at: str


class HistoryReviewItem(BaseModel):
    kind: str = "review"
    id: str
    seller_id: str
    seller_url: str
    stars: int
    comment: Optional[str]
    product_matched: Optional[bool]
    responded_fast: Optional[bool]
    item_received: Optional[bool]
    would_buy_again: Optional[bool]
    created_at: str


class BuyerHistoryResponse(BaseModel):
    reports: list[HistoryReportItem]
    reviews: list[HistoryReviewItem]
    total_reports: int
    total_reviews: int


# ── GET /api/history/ ─────────────────────────────────────────────────────────

@router.get("/", response_model=BuyerHistoryResponse)
def get_buyer_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),   # auth required
):
    # ── Reports this user filed ───────────────────────────────────────────────
    raw_reports = (
        db.query(Report)
        .filter(Report.reporter_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )

    reports = []
    for r in raw_reports:
        seller = db.query(SellerProfile).filter(SellerProfile.id == r.seller_id).first()
        reports.append(HistoryReportItem(
            id=str(r.id),
            seller_id=str(r.seller_id),
            seller_url=seller.profile_url if seller else "",
            scam_type=r.scam_type.value,
            description=r.description,
            screenshot_url=r.screenshot_url,
            credibility_score=r.credibility_score,
            created_at=r.created_at.isoformat(),
        ))

    # ── Reviews this user left ────────────────────────────────────────────────
    raw_reviews = (
        db.query(Review)
        .filter(Review.reviewer_id == current_user.id)
        .order_by(Review.created_at.desc())
        .all()
    )

    reviews = []
    for r in raw_reviews:
        seller = db.query(SellerProfile).filter(SellerProfile.id == r.seller_id).first()
        reviews.append(HistoryReviewItem(
            id=str(r.id),
            seller_id=str(r.seller_id),
            seller_url=seller.profile_url if seller else "",
            stars=r.stars,
            comment=r.comment,
            product_matched=r.product_matched,
            responded_fast=r.responded_fast,
            item_received=r.item_received,
            would_buy_again=r.would_buy_again,
            created_at=r.created_at.isoformat(),
        ))

    return BuyerHistoryResponse(
        reports=reports,
        reviews=reviews,
        total_reports=len(reports),
        total_reviews=len(reviews),
    )




@router.get("/user/{user_id}", response_model=BuyerHistoryResponse)
def get_user_history(
    user_id: str,
    db: Session = Depends(get_db),
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    raw_reports = (
        db.query(Report)
        .filter(Report.reporter_id == user_uuid)
        .order_by(Report.created_at.desc())
        .all()
    )

    reports = []
    for r in raw_reports:
        seller = db.query(SellerProfile).filter(SellerProfile.id == r.seller_id).first()
        reports.append(HistoryReportItem(
            id=str(r.id),
            seller_id=str(r.seller_id),
            seller_url=seller.profile_url if seller else "",
            scam_type=r.scam_type.value,
            description=r.description,
            screenshot_url=r.screenshot_url,
            credibility_score=r.credibility_score,
            created_at=r.created_at.isoformat(),
        ))

    raw_reviews = (
        db.query(Review)
        .filter(Review.reviewer_id == user_uuid)
        .order_by(Review.created_at.desc())
        .all()
    )

    reviews = []
    for r in raw_reviews:
        seller = db.query(SellerProfile).filter(SellerProfile.id == r.seller_id).first()
        reviews.append(HistoryReviewItem(
            id=str(r.id),
            seller_id=str(r.seller_id),
            seller_url=seller.profile_url if seller else "",
            stars=r.stars,
            comment=r.comment,
            product_matched=r.product_matched,
            responded_fast=r.responded_fast,
            item_received=r.item_received,
            would_buy_again=r.would_buy_again,
            created_at=r.created_at.isoformat(),
        ))

    return BuyerHistoryResponse(
        reports=reports,
        reviews=reviews,
        total_reports=len(reports),
        total_reviews=len(reviews),
    )