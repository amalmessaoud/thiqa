"""
app/routes/reports.py

Report submission endpoint.
Changes vs original:
  • seller_id replaced by seller_url — caller passes the profile URL instead
    of an internal UUID.  The seller is created as a stub if not yet in DB,
    so reports can be submitted for any URL immediately.  The stub will be
    enriched the next time /search/ is called with the same URL.
  • screenshot uploaded as a real multipart file from the user's PC; the file
    is saved to disk under  media/screenshots/  and the relative URL is stored.
  • After a successful report, returns trusted seller recommendations from the
    same category as the reported seller.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Report, SellerProfile, ScamType, Platform
from app.schemas.schemas import ReportSubmitWithRecommendationsResponse, TrustedSellerItem
from app.routes.auth import get_current_user
from ai.scoring.recommender import get_trusted_alternatives

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Screenshot storage config ─────────────────────────────────────────────────
SCREENSHOT_DIR = Path("media") / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SCREENSHOT_SIZE = 10 * 1024 * 1024  # 10 MB


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_screenshot(file: UploadFile) -> str:
    """
    Validate and persist the uploaded screenshot.
    Returns the relative URL path (e.g. '/media/screenshots/<uuid>.jpg').
    Raises HTTPException on invalid file type or size.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: JPEG, PNG, WebP, GIF.",
        )

    contents = file.file.read()
    if len(contents) > MAX_SCREENSHOT_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Screenshot too large. Maximum allowed size is 10 MB.",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    dest = SCREENSHOT_DIR / filename

    with open(dest, "wb") as f:
        f.write(contents)

    return f"/media/screenshots/{filename}"


def _detect_platform(url: str) -> Platform:
    """Detect platform enum from a profile URL."""
    if "instagram.com" in url:
        return Platform.instagram
    if "tiktok.com" in url:
        return Platform.tiktok
    return Platform.facebook


def _lookup_or_create_seller(db: Session, seller_url: str) -> SellerProfile:
    """
    Find or create a SellerProfile by profile URL.

    If the seller doesn't exist yet, a minimal stub record is created so that
    reports can be submitted immediately for any URL.  The stub will be fully
    enriched (display_name, followers, photos, trust score, etc.) the next
    time GET /search/ is called with the same URL — create_analysis() in
    crud.py detects the existing row by profile_url and updates it in-place,
    so all reports linked to the stub's id remain correctly associated.
    """
    url = seller_url.strip()

    seller = (
        db.query(SellerProfile)
        .filter(SellerProfile.profile_url.ilike(f"%{url}%"))
        .first()
    )

    if seller:
        return seller

    # ── Create a minimal stub ─────────────────────────────────────────────
    seller = SellerProfile(
        id          = uuid.uuid4(),
        profile_url = url,
        platform    = _detect_platform(url),
        # display_name, profile_photo_url, account_age_days, etc. left NULL
        # — they will be populated on the first /search/ call.
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    logger.info("Created stub seller profile for %s (id=%s)", url, seller.id)
    return seller


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/reports/", response_model=ReportSubmitWithRecommendationsResponse)
async def submit_report(
    seller_url:  str           = Form(...,  description="Facebook / Instagram / TikTok profile URL"),
    scam_type:   str           = Form(...),
    description: Optional[str] = Form(None),
    screenshot:  UploadFile    = File(...,  description="Screenshot image (JPEG / PNG / WebP, max 10 MB)"),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    # ── 1. Resolve or create seller by URL ────────────────────────────────
    seller = _lookup_or_create_seller(db, seller_url)

    # ── 2. Validate scam_type ─────────────────────────────────────────────
    valid_types = {e.value for e in ScamType}
    if scam_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scam_type. Must be one of: {', '.join(sorted(valid_types))}",
        )

    # ── 3. Save screenshot ────────────────────────────────────────────────
    screenshot_url = _save_screenshot(screenshot)

    # ── 4. AI credibility scoring ─────────────────────────────────────────
    credibility_score  = None
    credibility_label  = None
    credibility_reason = None

    if description:
        try:
            from ai import analyze_text
            analysis          = analyze_text(description)
            is_scam           = analysis.get("label") == "scam"
            conf              = float(analysis.get("confidence", 0.5))
            credibility_score = round(conf if is_scam else conf * 0.4, 3)
            credibility_label = (
                "high"   if credibility_score >= 0.7 else
                "medium" if credibility_score >= 0.4 else "low"
            )
            credibility_reason = ", ".join(analysis.get("red_flags", [])) or None
        except Exception as exc:
            logger.warning("Credibility scoring failed: %s", exc)

    # ── 5. Persist report ─────────────────────────────────────────────────
    report = Report(
        seller_id          = seller.id,
        reporter_id        = current_user.id,
        scam_type          = ScamType(scam_type),
        description        = description,
        screenshot_url     = screenshot_url,
        credibility_score  = credibility_score,
        credibility_reason = credibility_reason,
    )
    db.add(report)

    # ── 6. Auto-classify seller category if not already set ───────────────
    if not seller.category:
        try:
            from ai.category.classifier import classify_seller_category

            text_for_cat = " ".join(filter(None, [
                seller.display_name,
                seller.profile_url,
                description,
            ]))
            if text_for_cat.strip():
                seller.category = classify_seller_category(text_for_cat)
        except Exception as exc:
            logger.warning("Category classification failed: %s", exc)

    db.commit()
    db.refresh(report)

    # ── 7. Trusted seller recommendations ────────────────────────────────
    recommendations = get_trusted_alternatives(
        db=db,
        category=seller.category,
        exclude_seller_id=str(seller.id),
        limit=5,
    )

    return ReportSubmitWithRecommendationsResponse(
        success           = True,
        report_id         = str(report.id),
        credibility_score = credibility_score,
        credibility_label = credibility_label,
        message           = "تم تسجيل البلاغ بنجاح",
        recommendations   = [TrustedSellerItem(**r) for r in recommendations],
    )


@router.get("/reports/")
def get_reports(seller_url: str, db: Session = Depends(get_db)):
    """Return all reports for a seller identified by profile URL."""
    url = seller_url.strip()
    seller = (
        db.query(SellerProfile)
        .filter(SellerProfile.profile_url.ilike(f"%{url}%"))
        .first()
    )
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    reports = (
        db.query(Report)
        .filter(Report.seller_id == seller.id)
        .order_by(Report.created_at.desc())
        .all()
    )

    return {
        "reports": [
            {
                "id":                 str(r.id),
                "seller_id":          str(r.seller_id),
                "scam_type":          r.scam_type.value,
                "description":        r.description,
                "screenshot_url":     r.screenshot_url,
                "credibility_score":  r.credibility_score,
                "credibility_reason": r.credibility_reason,
                "created_at":         r.created_at.isoformat(),
            }
            for r in reports
        ]
    }