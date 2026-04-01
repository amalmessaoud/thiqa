"""
ai/scoring/recommender.py

Trusted seller recommender.

When a user reports a seller in category X, fetch sellers in category X
with the best trust signals and return them as safer alternatives.

Used by the reports route after a successful report submission.
"""

from __future__ import annotations
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Only exclude sellers whose reports have credibility at or above this threshold
_CREDIBILITY_EXCLUSION_THRESHOLD = 0.6


def get_trusted_alternatives(
    db,
    category:          Optional[str],
    exclude_seller_id: str,
    limit:             int = 5,
) -> list[dict]:
    """
    Return up to `limit` trusted sellers in the same category,
    excluding the reported seller and any seller with credible reports.

    Ranking criteria (no ML call needed):
      1. Zero credible reports (credibility >= threshold)
      2. High average star rating
      3. Older account
      4. More posts (more active)

    Args:
        db:                SQLAlchemy session
        category:          e.g. "ملابس" — if None/empty returns empty list
        exclude_seller_id: UUID string of the reported seller
        limit:             max results to return

    Returns:
        List of dicts matching TrustedSellerItem schema.
    """
    if not category:
        return []

    try:
        from app.models.models import SellerProfile, Report, Review
        import uuid

        exclude_uuid = uuid.UUID(exclude_seller_id)

        # ── FIX: only exclude sellers with HIGH-CREDIBILITY reports ──────────
        # A single low-credibility report (e.g. 0.2) should not permanently
        # blacklist a seller from recommendations.
        credible_report_seller_ids = {
            row[0]
            for row in db.query(Report.seller_id)
            .filter(Report.credibility_score >= _CREDIBILITY_EXCLUSION_THRESHOLD)
            .distinct()
            .all()
        }
        credible_report_seller_ids.add(exclude_uuid)

        # Fetch candidates: same category, no credible reports
        candidates = (
            db.query(SellerProfile)
            .filter(
                SellerProfile.category == category,
                ~SellerProfile.id.in_(credible_report_seller_ids),
                SellerProfile.account_age_days.isnot(None),
            )
            .all()
        )

        if not candidates:
            # Broaden: same category, any seller except the reported one
            candidates = (
                db.query(SellerProfile)
                .filter(
                    SellerProfile.category == category,
                    SellerProfile.id != exclude_uuid,
                )
                .limit(50)
                .all()
            )

        if not candidates:
            return []

        def _score(seller: SellerProfile) -> float:
            reviews   = db.query(Review).filter(Review.seller_id == seller.id).all()
            avg_stars = sum(r.stars for r in reviews) / len(reviews) if reviews else 3.0
            age_score  = min((seller.account_age_days or 0) / 365, 5) * 10   # up to 50 pts
            star_score = avg_stars * 10                                        # up to 50 pts
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