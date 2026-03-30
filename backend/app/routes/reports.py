import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.models.models import Report, SellerProfile, SellerContact, User, Platform, ScamType
from app.schemas.schemas import (
    ReportSubmitResponse,
    ReportsListResponse,
    ReportResponse,
    TrustedSellerItem,
    ReportSubmitWithRecommendationsResponse,
)
from app.services.cloudinary_service import upload_screenshot
from app.routes.auth import get_current_user
from app.db.crud import get_trusted_sellers_by_category
from ai import assess_report_credibility, classify_seller_category

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


def _detect_platform(profile_url: str) -> Platform:
    if "instagram.com" in profile_url:
        return Platform.instagram
    return Platform.facebook


def _upsert_seller(db: Session, profile_url: str) -> SellerProfile:
    """Find existing seller or create a minimal profile."""
    seller = db.query(SellerProfile).filter(
        SellerProfile.profile_url == profile_url
    ).first()

    if not seller:
        seller = SellerProfile(
            profile_url=profile_url,
            platform=_detect_platform(profile_url),
        )
        db.add(seller)
        db.commit()
        db.refresh(seller)

    return seller


def _save_contacts(db: Session, seller_id: uuid.UUID, contacts: list[str]):
    """
    Parse and save contact strings submitted with the report.
    Format expected: "phone:0661234567" or "telegram:@handle" or "other:value"
    """
    from app.models.models import SellerContact, ContactType

    for contact_str in contacts:
        try:
            contact_type_str, contact_value = contact_str.split(":", 1)
            try:
                contact_type = ContactType(contact_type_str.strip())
            except ValueError:
                contact_type = ContactType.other

            # Check for duplicate before inserting
            existing = db.query(SellerContact).filter(
                SellerContact.seller_id == seller_id,
                SellerContact.contact_value == contact_value.strip()
            ).first()

            if not existing:
                db.add(SellerContact(
                    seller_id=seller_id,
                    contact_type=contact_type,
                    contact_value=contact_value.strip(),
                ))
        except ValueError:
            continue  # skip malformed contact strings

    db.commit()


@router.post("/", response_model=ReportSubmitWithRecommendationsResponse)
def submit_report(
    profile_url: str = Form(...),
    scam_type: str = Form(...),
    description: Optional[str] = Form(None),
    screenshot: UploadFile = File(...),
    contacts: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate scam_type
    if scam_type not in ScamType._value2member_map_:
        raise HTTPException(status_code=400, detail=f"Invalid scam_type: {scam_type}")

    # Validate screenshot file type
    if screenshot.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {screenshot.content_type}. Only JPEG, PNG, WEBP allowed."
        )

    temp_path = None
    try:
        # Save screenshot to temp file — used for both Cloudinary and OCR
        suffix = os.path.splitext(screenshot.filename)[1] if screenshot.filename else ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(screenshot.file.read())
            temp_path = tmp.name

        # Upload to Cloudinary — permanent URL stored in DB
        try:
            screenshot_url = upload_screenshot(temp_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Screenshot upload failed: {str(e)}"
            )

        # Run credibility scoring — OCR + LLM
        try:
            credibility = assess_report_credibility(
                scam_type=scam_type,
                description=description,
                screenshot_path=temp_path,
            )
        except Exception:
            # Credibility scoring failure must not block report submission
            credibility = {
                "credibility_score": 0.3,
                "credibility_label": "low",
                "reason": "تعذر تحليل المصداقية تلقائياً",
                "screenshot_supports_claim": False,
            }

    finally:
        # Always delete temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    # Upsert seller profile
    seller = _upsert_seller(db, profile_url.strip())

    # Save optional contacts
    if contacts:
        _save_contacts(db, seller.id, contacts)

    # Insert report
    report = Report(
        seller_id=seller.id,
        reporter_id=current_user.id,
        scam_type=ScamType(scam_type),
        description=description,
        screenshot_url=screenshot_url,
        credibility_score=credibility["credibility_score"],
        credibility_reason=credibility["reason"],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # ── Classify reported seller's category & fetch recommendations ───────────
    seller_text = f"{seller.display_name or ''} {profile_url}"
    category = classify_seller_category(seller_text)

    # Persist category on the seller profile if not already set
    if not seller.category:
        seller.category = category
        db.add(seller)
        db.commit()

    trusted = get_trusted_sellers_by_category(
        db,
        category=category,
        exclude_seller_id=seller.id,
        limit=3,
    )

    recommendations = [
        TrustedSellerItem(
            id=str(s.id),
            display_name=s.display_name,
            profile_url=s.profile_url,
            platform=s.platform.value,
            category=s.category,
        )
        for s in trusted
    ]

    return ReportSubmitWithRecommendationsResponse(
        success=True,
        report_id=str(report.id),
        credibility_score=credibility["credibility_score"],
        credibility_label=credibility["credibility_label"],
        message="تم تسجيل بلاغك بنجاح",
        recommendations=recommendations,
    )

@router.get("/", response_model=ReportsListResponse)
def get_reports(seller_id: str, db: Session = Depends(get_db)):
    try:
        seller_uuid = uuid.UUID(seller_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid seller_id format")

    reports = (
        db.query(Report)
        .filter(Report.seller_id == seller_uuid)
        .order_by(Report.credibility_score.desc().nullslast())
        .all()
    )

    result = []
    for r in reports:
        reporter = db.query(User).filter(User.id == r.reporter_id).first()
        result.append(ReportResponse(
            id=str(r.id),
            seller_id=str(r.seller_id),
            scam_type=r.scam_type.value,
            description=r.description,
            screenshot_url=r.screenshot_url,
            credibility_score=r.credibility_score,
            credibility_reason=r.credibility_reason,
            reporter_email=reporter.email if reporter else "unknown",
            created_at=r.created_at.isoformat(),
        ))

    return ReportsListResponse(reports=result)