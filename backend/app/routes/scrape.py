# backend/app/routes/scrape.py
# ---------------------------------------------------------------------------
# Router for scraping endpoints.
# Registered in main.py with:
#   app.include_router(scrape.router, prefix="/api/scrape", tags=["scrape"])
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config import APIFY_API_KEY 

from app.db.database import get_db
from app.schemas.schemas import AnalyzeRequest, AnalyzeResponse, HistoryItem
from app.db import crud
from app.services.scraping import (
    detect_platform,
    normalize,
    get_apify_usage,
    scrape_fb_page,
    scrape_fb_post,
    scrape_ig_profile,
    scrape_ig_post,
    scrape_tt_profile,
    scrape_tt_post,
)


from app.schemas.schemas import SentimentRequest, SentimentResponse
from ai.sentiment.comment_sentiment import (
    analyze_sentiment,
    ScrapeResult,
    Comment,
)



router = APIRouter()


@router.post("/scraping", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, db: Session = Depends(get_db)):
    if not APIFY_API_KEY:
        raise HTTPException(500, "APIFY_API_KEY not configured in environment")

    platform = detect_platform(req.url)
    if not platform:
        raise HTTPException(400, "Unrecognised URL. Paste a Facebook, Instagram or TikTok link.")

    if platform == "fb_page":
        raw = await scrape_fb_page(APIFY_API_KEY, req.url)
    elif platform == "fb_post":
        raw = await scrape_fb_post(APIFY_API_KEY, req.url)
    elif platform == "ig_profile":
        raw = await scrape_ig_profile(APIFY_API_KEY, req.url)
    elif platform == "ig_post":
        raw = await scrape_ig_post(APIFY_API_KEY, req.url)
    elif platform == "tt_profile":
        raw = await scrape_tt_profile(APIFY_API_KEY, req.url)
    elif platform == "tt_post":
        raw = await scrape_tt_post(APIFY_API_KEY, req.url)
    else:
        raise HTTPException(400, f"Unsupported platform: {platform}")

    if not raw:
        raise HTTPException(404, "No data returned. Page may be private or URL invalid.")

    normalized = normalize(platform, raw)
    record = crud.create_analysis(db, req.url, platform, normalized)

    return AnalyzeResponse(
        id=str(record.id),
        platform=platform,
        url=req.url,
        data=normalized,
        created_at=str(record.created_at),
    )



@router.get("/history", response_model=list[HistoryItem])
def get_history(limit: int = 20, db: Session = Depends(get_db)):
    records = crud.get_history(db, limit)
    return [
        HistoryItem(
            id=str(r.id),
            url=r.profile_url,
            platform=r.platform.value,
            page_name=r.display_name,
            title=r.display_name,
            followers=None,
            created_at=str(r.created_at),
        )
        for r in records
    ]


@router.get("/history/{record_id}")
def get_record(record_id: str, db: Session = Depends(get_db)):
    r = crud.get_record(db, record_id)
    if not r:
        raise HTTPException(404, "Record not found")
    return r


@router.delete("/history/{record_id}")
def delete_record(record_id: str, db: Session = Depends(get_db)):
    crud.delete_record(db, record_id)
    return {"deleted": True}

