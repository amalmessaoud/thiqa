# backend/app/db/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from app.models.models import SellerProfile, SellerContact, Platform, ContactType, Report
import uuid
import re
from datetime import datetime, timezone

_PLATFORM_MAP = {
    "fb_page":    Platform.facebook,
    "fb_post":    Platform.facebook,
    "ig_profile": Platform.instagram,
    "ig_post":    Platform.instagram,
    "tt_profile": Platform.tiktok,
    "tt_post":    Platform.tiktok,
}


# ── FIX: Facebook scraper returns bio/about/website/phone as lists ────────────

def _coerce_str(val) -> str:
    """Flatten list-or-str fields — Facebook scraper returns some fields as a list."""
    if val is None:
        return ""
    if isinstance(val, list):
        return " ".join(str(item) for item in val if item)
    return str(val)


# ─────────────────────────────────────────────────────────────────────────────

def _age_from_creation_date(creation_date) -> int | None:
    if not creation_date:
        return None
    try:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(creation_date, fmt).replace(tzinfo=timezone.utc)
                return max(0, (datetime.now(timezone.utc) - dt).days)
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _age_from_bio(bio) -> int | None:
    """Extract account age from bio text like 'Since 2019' or 'منذ 2020'.
    FIX: accepts list or str — Facebook scraper returns bio as a list.
    """
    bio = _coerce_str(bio)  # ← FIX
    if not bio:
        return None
    match = re.search(r'(?:since|منذ|depuis)\s*(\d{4})', bio, re.IGNORECASE)
    if not match:
        match = re.search(r'\b(20[12]\d)\b', bio)
    if match:
        year = int(match.group(1))
        try:
            dt = datetime(year, 1, 1, tzinfo=timezone.utc)
            return max(0, (datetime.now(timezone.utc) - dt).days)
        except Exception:
            pass
    return None


def _extract_age(data: dict) -> int | None:
    age = _age_from_creation_date(data.get("creation_date"))
    if age is not None:
        return age
    # FIX: coerce list → str before any string operations
    bio = _coerce_str(data.get("bio") or data.get("intro") or "")
    return _age_from_bio(bio)


def _map_category(data: dict) -> str | None:
    # FIX: coerce list fields before string operations
    raw_cat = _coerce_str(data.get("category") or "")
    bio     = _coerce_str(data.get("bio") or "") + " " + _coerce_str(data.get("title") or "")
    cat_lower = (raw_cat + " " + bio).lower()

    if any(k in cat_lower for k in ["cloth", "fashion", "vêtement", "robe", "mode", "ملابس", "boutique", "dressing"]):
        return "ملابس"
    if any(k in cat_lower for k in ["electron", "tech", "phone", "gsm", "إلكترون"]):
        return "إلكترونيات"
    if any(k in cat_lower for k in ["food", "épicerie", "manger", "أكل", "حلويات", "gateau", "cuisine"]):
        return "منتجات_غذائية"
    if any(k in cat_lower for k in ["beauty", "cosmetic", "makeup", "maquillage", "تجميل", "parfum", "soin"]):
        return "مستحضرات_تجميل"
    if any(k in cat_lower for k in ["baby", "enfant", "jouet", "أطفال", "bébé", "kids"]):
        return "منتجات_أطفال"
    if any(k in cat_lower for k in ["meuble", "décor", "furniture", "أثاث", "ديكور"]):
        return "أثاث_وديكور"
    if any(k in cat_lower for k in ["handmade", "artisanat", "art", "فن", "حرف", "poterie"]):
        return "فن_وحرف"
    if any(k in cat_lower for k in ["service", "conseil", "formation", "خدمة", "agence", "marketing"]):
        return "خدمات"

    if bio.strip():
        try:
            from ai.scoring.category_classifier import classify_seller_category
            return classify_seller_category(bio)
        except Exception:
            pass
    return None


def create_analysis(db: Session, url: str, platform: str, data: dict) -> SellerProfile:
    existing      = db.query(SellerProfile).filter(SellerProfile.profile_url == url).first()
    platform_enum = _PLATFORM_MAP.get(platform, Platform.facebook)
    stats         = data.get("stats") or {}
    account_age   = _extract_age(data)
    category      = _map_category(data)
    display_name  = _coerce_str(data.get("title") or data.get("page_name") or "")  # FIX
    profile_photo = data.get("profile_photo_url") or data.get("profilePicUrl")
    post_count    = stats.get("post_count") or data.get("post_count")

    if existing:
        existing.display_name      = display_name or existing.display_name
        existing.post_count        = post_count
        existing.account_age_days  = account_age or existing.account_age_days
        existing.category          = category or existing.category
        existing.profile_photo_url = profile_photo or existing.profile_photo_url
        existing.fb_fetched_at     = datetime.now(timezone.utc)
        db.commit()
        _upsert_contacts(db, existing.id, data)
        db.refresh(existing)
        return existing

    record = SellerProfile(
        id                = uuid.uuid4(),
        profile_url       = url,
        platform          = platform_enum,
        display_name      = display_name or None,
        profile_photo_url = profile_photo,
        post_count        = post_count,
        account_age_days  = account_age,
        category          = category,
        fb_fetched_at     = datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    _upsert_contacts(db, record.id, data)
    return record


def _upsert_contacts(db: Session, seller_id: uuid.UUID, data: dict) -> None:
    # FIX: coerce website/phone — Facebook scraper returns them as lists
    website = _coerce_str(data.get("website")) or None
    phone   = _coerce_str(data.get("phone"))   or None

    if website:
        exists = db.query(SellerContact).filter(
            SellerContact.seller_id     == seller_id,
            SellerContact.contact_value == website,
        ).first()
        if not exists:
            db.add(SellerContact(
                id            = uuid.uuid4(),
                seller_id     = seller_id,
                contact_type  = ContactType.other,
                contact_value = website,
            ))

    if phone:
        exists = db.query(SellerContact).filter(
            SellerContact.seller_id    == seller_id,
            SellerContact.contact_type == ContactType.phone,
        ).first()
        if not exists:
            db.add(SellerContact(
                id            = uuid.uuid4(),
                seller_id     = seller_id,
                contact_type  = ContactType.phone,
                contact_value = phone,
            ))

    db.commit()


def get_history(db: Session, limit: int = 20) -> list[SellerProfile]:
    return (
        db.query(SellerProfile)
        .order_by(SellerProfile.created_at.desc())
        .limit(limit)
        .all()
    )


def get_record(db: Session, record_id) -> SellerProfile | None:
    try:
        uid = uuid.UUID(str(record_id))
    except (ValueError, AttributeError):
        return None
    return db.query(SellerProfile).filter(SellerProfile.id == uid).first()


def delete_record(db: Session, record_id) -> None:
    record = get_record(db, record_id)
    if record:
        db.delete(record)
        db.commit()


def get_trusted_sellers_by_category(
    db: Session,
    category: str,
    exclude_seller_id: uuid.UUID,
    limit: int = 3,
) -> list[SellerProfile]:
    report_counts = (
        db.query(Report.seller_id, sa_func.count(Report.id).label("report_count"))
        .group_by(Report.seller_id)
        .subquery()
    )
    return (
        db.query(SellerProfile)
        .outerjoin(report_counts, SellerProfile.id == report_counts.c.seller_id)
        .filter(SellerProfile.category == category, SellerProfile.id != exclude_seller_id)
        .order_by(sa_func.coalesce(report_counts.c.report_count, 0).asc())
        .limit(limit)
        .all()
    )