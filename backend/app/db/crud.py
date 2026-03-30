# backend/app/crud.py
# ---------------------------------------------------------------------------
# Replaces your old crud.py (which used SQLite + an `analyses` table).
# Now writes scraping results into `seller_profiles` — the table that already
# exists in the setup's PostgreSQL database.
#
# Your main.py calls:
#   crud.create_analysis(db, url, platform, normalized)
#   crud.get_history(db, limit)
#   crud.get_record(db, record_id)
#   crud.delete_record(db, record_id)
#
# All four functions kept with the exact same signatures — main.py untouched.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.models import SellerProfile, Platform, Report

import uuid


# ── Map scraping platform string → Platform enum ──────────────────────────────

_PLATFORM_MAP = {
    "fb_page":    Platform.facebook,
    "fb_post":    Platform.facebook,
    "ig_profile": Platform.instagram,
    "ig_post":    Platform.instagram,
    "tt_profile": Platform.tiktok,
    "tt_post":    Platform.tiktok,
}


# ── create_analysis ───────────────────────────────────────────────────────────
# Called by main.py after normalize() returns the cleaned data dict.
# Upserts a SellerProfile row (insert or update if the URL already exists).

def create_analysis(db: Session, url: str, platform: str, data: dict) -> SellerProfile:
    existing = (
        db.query(SellerProfile)
        .filter(SellerProfile.profile_url == url)
        .first()
    )

    platform_enum = _PLATFORM_MAP.get(platform, Platform.facebook)

    if existing:
        existing.display_name = data.get("title") or data.get("page_name")
        existing.post_count   = (data.get("stats") or {}).get("post_count")
        db.commit()
        db.refresh(existing)
        return existing

    record = SellerProfile(
        id           = uuid.uuid4(),
        profile_url  = url,
        platform     = platform_enum,
        display_name = data.get("title") or data.get("page_name"),
        post_count   = (data.get("stats") or {}).get("post_count"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── get_history ───────────────────────────────────────────────────────────────

def get_history(db: Session, limit: int = 20) -> list[SellerProfile]:
    return (
        db.query(SellerProfile)
        .order_by(SellerProfile.created_at.desc())
        .limit(limit)
        .all()
    )


# ── get_record ────────────────────────────────────────────────────────────────
# main.py passes record_id from the URL — converted to UUID here.

def get_record(db: Session, record_id) -> SellerProfile | None:
    try:
        uid = uuid.UUID(str(record_id))
    except (ValueError, AttributeError):
        return None
    return db.query(SellerProfile).filter(SellerProfile.id == uid).first()


# ── delete_record ─────────────────────────────────────────────────────────────

def delete_record(db: Session, record_id) -> None:
    record = get_record(db, record_id)
    if record:
        db.delete(record)
        db.commit()
        
        
# ── get_trusted_sellers_by_category ──────────────────────────────────────────
# Returns up to `limit` sellers in the same category as the reported seller,
# excluding the reported seller itself, ordered by fewest reports first.

from sqlalchemy import func as sa_func

def get_trusted_sellers_by_category(
    db: Session,
    category: str,
    exclude_seller_id: uuid.UUID,
    limit: int = 3,
) -> list[SellerProfile]:
    # Subquery: count reports per seller
    report_counts = (
        db.query(
            Report.seller_id,
            sa_func.count(Report.id).label("report_count"),
        )
        .group_by(Report.seller_id)
        .subquery()
    )

    results = (
        db.query(SellerProfile)
        .outerjoin(report_counts, SellerProfile.id == report_counts.c.seller_id)
        .filter(
            SellerProfile.category == category,
            SellerProfile.id != exclude_seller_id,
        )
        .order_by(
            sa_func.coalesce(report_counts.c.report_count, 0).asc()
        )
        .limit(limit)
        .all()
    )
    return results