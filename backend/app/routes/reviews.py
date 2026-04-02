import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Review, SellerProfile, User, Platform
from app.routes.auth import get_current_user

router = APIRouter()


# ── Schemas (inline — add to schemas.py if you prefer) ───────────────────────

class ReviewSubmitRequest(BaseModel):
    profile_url: str
    stars: int
    comment: Optional[str] = None
    product_matched: Optional[bool] = None   # الصورة مطابقة للسلعة
    responded_fast: Optional[bool] = None    # رد بسرعة
    item_received: Optional[bool] = None     # وصلتني السلعة
    would_buy_again: Optional[bool] = None   # نعاود نشري منه

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


class ReviewResponse(BaseModel):
    id: str
    seller_id: str
    stars: int
    comment: Optional[str]
    product_matched: Optional[bool]
    responded_fast: Optional[bool]
    item_received: Optional[bool]
    would_buy_again: Optional[bool]
    reviewer_email: str
    created_at: str


class ReviewSubmitResponse(BaseModel):
    success: bool
    review_id: str
    message: str


class ReviewsListResponse(BaseModel):
    reviews: list[ReviewResponse]
    avg_stars: Optional[float]
    total: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_platform(profile_url: str) -> Platform:
    """Detect platform enum from a profile URL."""
    if "instagram.com" in profile_url:
        return Platform.instagram
    if "tiktok.com" in profile_url:
        return Platform.tiktok
    return Platform.facebook


def _upsert_seller(db: Session, profile_url: str) -> SellerProfile:
    """
    Find or create a SellerProfile by profile URL.

    If the seller doesn't exist yet, a minimal stub record is created so that
    reviews can be submitted immediately for any URL.  The stub will be fully
    enriched (display_name, followers, photos, trust score, etc.) the next
    time GET /search/ is called with the same URL — create_analysis() in
    crud.py detects the existing row by profile_url and updates it in-place,
    so all reviews linked to the stub's id remain correctly associated.
    """
    seller = db.query(SellerProfile).filter(
        SellerProfile.profile_url == profile_url
    ).first()

    if not seller:
        seller = SellerProfile(
            id          = uuid.uuid4(),
            profile_url = profile_url,
            platform    = _detect_platform(profile_url),
            # display_name, profile_photo_url, account_age_days, etc. left NULL
            # — they will be populated on the first /search/ call.
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

    review = Review(
        seller_id       = seller.id,
        reviewer_id     = current_user.id,
        stars           = body.stars,
        comment         = body.comment,
        product_matched = body.product_matched,
        responded_fast  = body.responded_fast,
        item_received   = body.item_received,
        would_buy_again = body.would_buy_again,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return ReviewSubmitResponse(
        success   = True,
        review_id = str(review.id),
        message   = "تم تسجيل تقييمك بنجاح",
    )


# ── GET /api/reviews/?seller_id= ─────────────────────────────────────────────

@router.get("/", response_model=ReviewsListResponse)
def get_reviews(seller_id: str, db: Session = Depends(get_db)):
    try:
        seller_uuid = uuid.UUID(seller_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid seller_id format")

    reviews = (
        db.query(Review)
        .filter(Review.seller_id == seller_uuid)
        .order_by(Review.created_at.desc())
        .all()
    )

    result = []
    for r in reviews:
        reviewer = db.query(User).filter(User.id == r.reviewer_id).first()
        result.append(ReviewResponse(
            id              = str(r.id),
            seller_id       = str(r.seller_id),
            stars           = r.stars,
            comment         = r.comment,
            product_matched = r.product_matched,
            responded_fast  = r.responded_fast,
            item_received   = r.item_received,
            would_buy_again = r.would_buy_again,
            reviewer_email  = reviewer.email if reviewer else "unknown",
            created_at      = r.created_at.isoformat(),
        ))

    avg_stars = (
        round(sum(r.stars for r in reviews) / len(reviews), 2)
        if reviews else None
    )

    return ReviewsListResponse(
        reviews   = result,
        avg_stars = avg_stars,
        total     = len(result),
    )