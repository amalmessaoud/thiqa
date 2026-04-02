from fastapi import APIRouter, Depends, Query ,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.crud import get_record

from app.db.database import get_db
from app.models.models import SellerProfile, Report, Platform, ScamType

router = APIRouter()

PAGE_SIZE = 20


@router.get("/")
def get_blacklist(
    page:      int            = Query(1, ge=1),
    scam_type: str            = Query(None),
    platform:  str            = Query(None),
    search:    str            = Query(None),
    db:        Session        = Depends(get_db),
):
    # ── Base query: sellers who have at least one report ──────────────────────
    query = (
        db.query(
            SellerProfile,
            func.count(Report.id).label("report_count"),
            func.max(Report.created_at).label("latest_report"),
            func.array_agg(Report.scam_type.distinct()).label("scam_types"),
        )
        .join(Report, Report.seller_id == SellerProfile.id)
        .group_by(SellerProfile.id)
        .filter(
            (SellerProfile.trust_score < 55) | (SellerProfile.trust_score.is_(None))
        )
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    if platform and platform in Platform._value2member_map_:
        query = query.filter(SellerProfile.platform == Platform(platform))

    if scam_type and scam_type in ScamType._value2member_map_:
        query = query.filter(
            Report.scam_type == ScamType(scam_type)
        )

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (SellerProfile.profile_url.ilike(term)) |
            (SellerProfile.display_name.ilike(term))
        )

    # ── Count before pagination ───────────────────────────────────────────────
    total = query.count()

    # ── Pagination ────────────────────────────────────────────────────────────
    offset = (page - 1) * PAGE_SIZE
    rows = (
        query
        .order_by(func.max(Report.created_at).desc())
        .offset(offset)
        .limit(PAGE_SIZE)
        .all()
    )

    # ── Build response ────────────────────────────────────────────────────────
    results = [
        {
            "id":            str(seller.id),
            "profile_url":   seller.profile_url,
            "platform":      seller.platform.value,
            "display_name":  seller.display_name,
            "category":      seller.category,
            "scam_types":    [s.value for s in (scam_types or []) if s],
            "report_count":  report_count,
            "latest_report": latest_report.isoformat() if latest_report else None,
        }
        for seller, report_count, latest_report, scam_types in rows
    ]

    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    return {
        "results":  results,
        "count":    total,
        "page":     page,
        "pages":    total_pages,
        "next":     f"?page={page+1}" if page < total_pages else None,
        "previous": f"?page={page-1}" if page > 1 else None,
    }


