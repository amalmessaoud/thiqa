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
from app.models.models import SellerProfile, Platform
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