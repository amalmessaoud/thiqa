from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.db.crud import get_record
from app.models.models import SellerProfile, Report

router = APIRouter(prefix="/seller", tags=["Seller"])


@router.get("/{seller_id}")
def get_seller_by_id(
    seller_id: str,
    db: Session = Depends(get_db),
):
    # ── Get seller ───────────────────────────────────────────────
    seller = get_record(db, seller_id)

    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    # ── Reports aggregation ──────────────────────────────────────
    report_stats = (
        db.query(
            func.count(Report.id).label("report_count"),
            func.max(Report.created_at).label("latest_report"),
            func.array_agg(Report.scam_type.distinct()).label("scam_types"),
        )
        .filter(Report.seller_id == seller.id)
        .first()
    )

    report_count, latest_report, scam_types = report_stats or (0, None, [])

    # ── Contacts ────────────────────────────────────────────────
    contacts = [
        {
            "type": c.contact_type.value,
            "value": c.contact_value
        }
        for c in seller.contacts
    ] if hasattr(seller, "contacts") else []

    # ── Response ────────────────────────────────────────────────
    return {
        "id": str(seller.id),
        "profile_url": seller.profile_url,
        "platform": seller.platform.value,
        "display_name": seller.display_name,
        "category": seller.category,
        "account_age_days": seller.account_age_days,
        "post_count": seller.post_count,
        "profile_photo_url": seller.profile_photo_url,

        "contacts": contacts,

    }