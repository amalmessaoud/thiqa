# backend/app/routes/ai_features.py
# ---------------------------------------------------------------------------
# Routes for the 3 new AI features. Register in main.py with:
#   from app.routes import ai_features
#   app.include_router(ai_features.router, prefix="/api/ai", tags=["ai"])
#
# Endpoints:
#   POST /api/ai/reviews/summary     — Part 1: feedback summariser
#   POST /api/ai/analyze/image       — Part 2: AI-image detector
#   POST /api/ai/analyze/sentiment   — Part 3: comment sentiment
# ---------------------------------------------------------------------------

import os
import sys

# Fix: add thiqa root to path so the 'ai' package is discoverable
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

import uuid
import tempfile



from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import SellerProfile
from app.schemas.schemas import (
    FeedbackSummaryRequest,
    FeedbackSummaryResponse,
    ImageAuthenticityResponse,
    SentimentRequest,
    SentimentResponse,
)

from ai import summarize_feedbacks, check_image_authenticity, analyze_sentiment
from ai.sentiment.comment_sentiment import ScrapeResult, Comment

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


# ── Part 1: Feedback Summariser ───────────────────────────────────────────────

@router.post("/reviews/summary", response_model=FeedbackSummaryResponse)
def get_feedback_summary(
    body: FeedbackSummaryRequest,
    db: Session = Depends(get_db),
):
    """
    Pass a seller_id — the route loads all their reviews from the DB,
    extracts comment text, and returns a Groq LLaMA Darija summary.

    You can also pass feedbacks directly in the body for testing.
    No auth required.
    """
    try:
        seller_uuid = uuid.UUID(body.seller_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid seller_id format")

    seller = db.query(SellerProfile).filter(SellerProfile.id == seller_uuid).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    if body.feedbacks is not None:
        feedbacks = body.feedbacks
    else:
        # Import Review model here to avoid circular import issues
        from app.models.models import Review
        reviews = (
            db.query(Review)
            .filter(Review.seller_id == seller_uuid)
            .order_by(Review.created_at.desc())
            .all()
        )
        feedbacks = [r.comment for r in reviews if r.comment and r.comment.strip()]

    try:
        result = summarize_feedbacks(feedbacks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback summary failed: {str(e)}")

    return FeedbackSummaryResponse(
        seller_id=body.seller_id,
        summary=result["summary"],
        sentiment_hint=result["sentiment_hint"],
        language_used=result["language_used"],
        total_count=result["total_count"],
    )


# ── Part 2: AI-Image Detector ─────────────────────────────────────────────────

@router.post("/analyze/image", response_model=ImageAuthenticityResponse)
def analyze_image_authenticity(
    image: UploadFile = File(..., description="Product or post image to check"),
):
    """
    Upload a product photo or screenshot.
    EfficientNet extracts visual signals, Groq LLaMA reasons over them.
    Returns whether the image is AI-generated + Darija verdict.
    No auth required.
    """
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {image.content_type}. Only JPEG, PNG, WEBP allowed.",
        )

    temp_path = None
    try:
        suffix = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image.file.read())
            temp_path = tmp.name

        result = check_image_authenticity(temp_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    return ImageAuthenticityResponse(
        is_ai_generated=result["is_ai_generated"],
        confidence=result["confidence"],
        verdict_arabic=result["verdict_arabic"],
        reasons=result.get("reasons", []),
        safe_to_trust=result["safe_to_trust"],
    )


# ── Part 3: Sentiment Analysis ────────────────────────────────────────────────

@router.post("/analyse/sentiment", response_model=SentimentResponse)
async def sentiment(req: SentimentRequest):
    try:
        scrape = ScrapeResult(
            profile_url=req.profile_url,
            post_url=req.post_url,
            platform="unknown",
            comments=[Comment(text=c.text) for c in req.comments],
        )
        result = analyze_sentiment(scrape)
    except Exception as e:
        raise HTTPException(500, f"Sentiment analysis failed: {e}")

    return SentimentResponse(
        profile_url=result.profile_url,
        post_url=result.post_url,
        positive_pct=result.positive_pct,
        negative_pct=result.negative_pct,
        neutral_pct=result.neutral_pct,
        irrelevant_pct=result.irrelevant_pct,
        total_analyzed=result.total_analyzed,
        summary=result.summary,
        top_positive=result.top_positive,
        top_negative=result.top_negative,
    )