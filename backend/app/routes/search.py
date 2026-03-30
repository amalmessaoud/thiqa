# app/routes/search.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import SellerProfile, SellerContact, Report, Review
from ai import calculate_trust_score, generate_seller_verdict

router = APIRouter()


@router.get("/search/")
def search(q: str, db: Session = Depends(get_db)):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    seller = (
        db.query(SellerProfile)
        .filter(
            (SellerProfile.profile_url.ilike(f"%{q.strip()}%")) |
            (SellerProfile.display_name.ilike(f"%{q.strip()}%"))
        )
        .first()
    )

    if not seller:
        return {"found": False, "seller": None, "trust_score": None,
                "reports": [], "reviews": [], "avg_stars": None}

    contacts = db.query(SellerContact).filter(SellerContact.seller_id == seller.id).all()
    reports  = db.query(Report).filter(Report.seller_id == seller.id).order_by(Report.created_at.desc()).all()
    reviews  = db.query(Review).filter(Review.seller_id == seller.id).order_by(Review.created_at.desc()).all()

    avg_stars = round(sum(r.stars for r in reviews) / len(reviews), 1) if reviews else None

    signals = {
        "account_age_days": seller.account_age_days,
        "post_count":       seller.post_count,
        "reports": [{"scam_type": r.scam_type.value, "credibility_score": r.credibility_score} for r in reports],
    }
    trust = calculate_trust_score(signals)

    verdict_narrative = ""
    recommendation    = trust.get("verdict", "")

    if reports or reviews:
        try:
            verdict_result    = generate_seller_verdict({
                "display_name":    seller.display_name,
                "account_age_days": seller.account_age_days,
                "post_count":      seller.post_count,
                "reports":  [{"scam_type": r.scam_type.value, "description": r.description, "credibility_score": r.credibility_score} for r in reports],
                "reviews":  [{"stars": r.stars, "comment": r.comment} for r in reviews],
                "avg_stars":    avg_stars,
                "review_count": len(reviews),
            })
            verdict_narrative = verdict_result.get("verdict", "")
            recommendation    = verdict_result.get("recommendation", recommendation)
        except Exception:
            pass

    return {
        "found": True,
        "seller": {
            "id":                str(seller.id),
            "profile_url":       seller.profile_url,
            "platform":          seller.platform.value,
            "display_name":      seller.display_name,
            "profile_photo_url": seller.profile_photo_url,
            "account_age_days":  seller.account_age_days,
            "post_count":        seller.post_count,
            "category":          seller.category,
            "contacts": [{"type": c.contact_type.value, "value": c.contact_value} for c in contacts],
        },
        "trust_score": {
            "score":             trust.get("score", 0),
            "verdict_color":     trust.get("verdict_color", "grey"),
            "verdict_darija":    trust.get("verdict_darija", ""),
            "verdict_narrative": verdict_narrative,
            "recommendation":    recommendation,
        },
        "reports": [
            {
                "id":                 str(r.id),
                "scam_type":          r.scam_type.value,
                "description":        r.description,
                "screenshot_url":     r.screenshot_url,
                "credibility_score":  r.credibility_score,
                "credibility_reason": r.credibility_reason,
                "created_at":         r.created_at.isoformat(),
            }
            for r in reports
        ],
        "reviews": [
            {
                "id":              str(r.id),
                "stars":           r.stars,
                "comment":         r.comment,
                "product_matched": r.product_matched,
                "responded_fast":  r.responded_fast,
                "item_received":   r.item_received,
                "would_buy_again": r.would_buy_again,
                "created_at":      r.created_at.isoformat(),
            }
            for r in reviews
        ],
        "avg_stars": avg_stars,
    }