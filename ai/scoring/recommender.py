"""
ai/scoring/recommender.py

Trusted seller recommender.

When a user reports a seller in category X, fetch sellers in category X
with trust_score > 70 and return them as safer alternatives.
"""

from __future__ import annotations
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_CREDIBILITY_EXCLUSION_THRESHOLD = 0.6


def get_trusted_alternatives(
    db,
    category:          Optional[str],
    exclude_seller_id: str,
    limit:             int = 5,
) -> list[dict]:
    """
    Return up to `limit` trusted sellers in the same category where
    trust_score > 70, excluding the reported seller and any seller
    with credible reports (credibility >= threshold).

    Falls back to scoring by age + stars if trust_score is not stored yet.
    """
    if not category:
        return []

    try:
        from app.models.models import SellerProfile, Report, Review
        import uuid

        exclude_uuid = uuid.UUID(exclude_seller_id)

        # Sellers with at least one high-credibility report are excluded
        credible_report_seller_ids = {
            row[0]
            for row in db.query(Report.seller_id)
            .filter(Report.credibility_score >= _CREDIBILITY_EXCLUSION_THRESHOLD)
            .distinct()
            .all()
        }
        credible_report_seller_ids.add(exclude_uuid)

        # ── Primary: same category + trust_score > 70 + no credible reports ──
        candidates = (
            db.query(SellerProfile)
            .filter(
                SellerProfile.category == category,
                ~SellerProfile.id.in_(credible_report_seller_ids),
                SellerProfile.trust_score > 70,          # ← score filter
            )
            .order_by(SellerProfile.trust_score.desc())  # best first
            .limit(limit * 2)                            # over-fetch for re-rank
            .all()
        )

        # ── Fallback: same category, exclude reported seller, no score filter ─
        # (handles sellers that haven't been searched yet and have no score)
        if not candidates:
            logger.info(
                "No candidates with trust_score > 70 in category '%s', "
                "falling back to age+stars ranking.",
                category,
            )
            candidates = (
                db.query(SellerProfile)
                .filter(
                    SellerProfile.category == category,
                    ~SellerProfile.id.in_(credible_report_seller_ids),
                )
                .limit(50)
                .all()
            )

        if not candidates:
            return []

        def _score(seller: SellerProfile) -> float:
            # Use stored trust_score when available, otherwise age+stars heuristic
            if seller.trust_score is not None:
                return float(seller.trust_score)
            reviews   = db.query(Review).filter(Review.seller_id == seller.id).all()
            avg_stars = sum(r.stars for r in reviews) / len(reviews) if reviews else 3.0
            age_score  = min((seller.account_age_days or 0) / 365, 5) * 10
            star_score = avg_stars * 10
            return age_score + star_score

        ranked = sorted(candidates, key=_score, reverse=True)[:limit]

        return [
            {
                "id":           str(s.id),
                "display_name": s.display_name,
                "profile_url":  s.profile_url,
                "platform":     s.platform.value,
                "category":     s.category,
            }
            for s in ranked
        ]

    except Exception as exc:
        logger.error("get_trusted_alternatives failed: %s", exc)
        return []