import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Review, SellerProfile, User, Platform
from app.routes.auth import get_current_user

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReviewSubmitRequest(BaseModel):
    profile_url: str
    stars: int
    comment: Optional[str] = None
    product_matched: Optional[bool] = None
    responded_fast: Optional[bool] = None
    item_received: Optional[bool] = None
    would_buy_again: Optional[bool] = None

    @field_validator("stars")
    @classmethod
    def stars_range(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("stars must be between 1 and 5")
        return v

    @field_validator("profile_url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("profile_url must not be empty")
        return v.strip()


class ReviewSubmitResponse(BaseModel):
    success: bool
    review_id: str
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_platform(profile_url: str) -> Platform:
    """Detect platform enum from a profile URL."""
    if "instagram.com" in profile_url:
        return Platform.instagram
    if "tiktok.com" in profile_url:
        return Platform.tiktok
    return Platform.facebook


def _upsert_seller(db: Session, profile_url: str) -> SellerProfile:
    """Find or create a SellerProfile by profile URL."""
    seller = db.query(SellerProfile).filter(
        SellerProfile.profile_url == profile_url
    ).first()

    if not seller:
        seller = SellerProfile(
            id=uuid.uuid4(),
            profile_url=profile_url,
            platform=_detect_platform(profile_url),
        )
        db.add(seller)
        db.commit()
        db.refresh(seller)

    return seller


# ── POST /api/reviews/ ────────────────────────────────────────────────────────

@router.post("/", response_model=ReviewSubmitResponse)
def submit_review(
    body: ReviewSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seller = _upsert_seller(db, body.profile_url)

    # Option C: ensure no None values for booleans
    review = Review(
        seller_id=seller.id,
        reviewer_id=current_user.id,
        stars=body.stars,
        comment=body.comment or "",  # empty string if comment is None
        product_matched=body.product_matched if body.product_matched is not None else False,
        responded_fast=body.responded_fast if body.responded_fast is not None else False,
        item_received=body.item_received if body.item_received is not None else False,
        would_buy_again=body.would_buy_again if body.would_buy_again is not None else False,
    )

    db.add(review)
    db.commit()
    db.refresh(review)
    return ReviewSubmitResponse(
        success=True,
        review_id=str(review.id),
        message="تم تسجيل تقييمك بنجاح",
    )