# app/routes/search.py
import re
import os
import logging
import tempfile
from datetime import datetime as _dt, timezone, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import SellerProfile, SellerContact, Report, Review
from app.db.crud import create_analysis
from ai import calculate_trust_score, generate_seller_verdict

router = APIRouter()
logger = logging.getLogger(__name__)

_STALE_DAYS = 7

MAX_IMAGES_TO_ANALYZE = 50
# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_stale(seller: SellerProfile) -> bool:
    if not seller.fb_fetched_at:
        return True
    age = _dt.now(timezone.utc) - seller.fb_fetched_at.replace(tzinfo=timezone.utc)
    return age > timedelta(days=_STALE_DAYS)


def _is_incomplete(seller: SellerProfile) -> bool:
    """
    Detect a bad/partial first scrape — or a stub created by a report/review
    submission — so we re-scrape even if the record is fresh.
    """
    followers  = getattr(seller, "followers",       None) or 0
    post_count = getattr(seller, "post_count",      None) or 0
    eng_rate   = getattr(seller, "engagement_rate", None) or 0

    # Stub record: created by report/review before any search
    if followers == 0 and post_count == 0 and eng_rate == 0 and not seller.display_name:
        return True
    # Partial scrape: posts exist but followers are missing
    if post_count > 0 and followers == 0 and eng_rate == 0:
        return True
    return False


def _coerce_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return " ".join(str(item) for item in val if item)
    return str(val)


def _estimate_age_from_bio(bio) -> int | None:
    if not bio:
        return None
    if isinstance(bio, list):
        bio = " ".join(str(item) for item in bio if item)
    if not bio:
        return None
    bold_digit_map = str.maketrans("𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗", "0123456789")
    normalized = bio.translate(bold_digit_map)
    match = re.search(
        r'(?:since|منذ|depuis|من)\s*(20\d{2}|19\d{2})',
        normalized, re.IGNORECASE
    )
    if match:
        year = int(match.group(1))
        current_year = _dt.now().year
        if 2005 <= year <= current_year:
            return (current_year - year) * 365
    return None


def _estimate_age_from_posts(scraped_data: dict) -> int | None:
    """
    Estimate account age from the oldest post date in the scraped sample.
    This is a lower bound — the account is at least this old.
    """
    posts = scraped_data.get("posts") or []
    if not posts:
        return None

    oldest_date = None
    for post in posts:
        date_val = post.get("date") or post.get("timestamp") or post.get("time")
        if not date_val:
            continue
        try:
            if isinstance(date_val, (int, float)):
                dt = _dt.fromtimestamp(date_val, tz=timezone.utc)
            elif isinstance(date_val, str):
                for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                    try:
                        dt = _dt.strptime(date_val[:19], fmt[:len(date_val[:19])].rstrip())
                        dt = dt.replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue
                else:
                    continue
            else:
                continue

            if oldest_date is None or dt < oldest_date:
                oldest_date = dt
        except Exception:
            continue

    if oldest_date:
        age_days = (_dt.now(timezone.utc) - oldest_date).days
        if age_days > 0:
            return age_days
    return None


def _extract_comments(scraped_data: dict) -> list[str]:
    comments = []
    for post in (scraped_data.get("posts") or []):
        for c in (post.get("comment_list") or []):
            text = c.get("text", "").strip()
            if text and len(text) > 2:
                comments.append(text)
            for reply in (c.get("replies") or []):
                rtext = reply.get("text", "").strip()
                if rtext and len(rtext) > 2:
                    comments.append(rtext)
    return comments


def _extract_comment_objects(scraped_data: dict):
    from ai.sentiment.comment_sentiment import Comment

    comment_objs = []
    for post in (scraped_data.get("posts") or []):
        for c in (post.get("comment_list") or []):
            text = c.get("text", "").strip()
            if text and len(text) > 2:
                comment_objs.append(Comment(
                    text=text,
                    author=c.get("author") or c.get("name"),
                    timestamp=c.get("timestamp") or c.get("date"),
                    likes=int(c.get("likes", 0) or 0),
                    is_reply=False,
                ))
            for reply in (c.get("replies") or []):
                rtext = reply.get("text", "").strip()
                if rtext and len(rtext) > 2:
                    comment_objs.append(Comment(
                        text=rtext,
                        author=reply.get("author") or reply.get("name"),
                        timestamp=reply.get("timestamp") or reply.get("date"),
                        likes=int(reply.get("likes", 0) or 0),
                        is_reply=True,
                    ))
    return comment_objs


def _resolve_followers(scraped_data: dict) -> int:
    """
    Extract follower count with multi-platform fallback chain.
    All values come directly from the platform profile — not computed from sample.
    """
    val = scraped_data.get("followers") or scraped_data.get("followersCount")
    if val and int(val) > 0:
        return int(val)

    stats = scraped_data.get("stats") or {}
    val = stats.get("followers") or stats.get("followersCount") or stats.get("fans")
    if val and int(val) > 0:
        return int(val)

    author_meta = scraped_data.get("authorMeta") or {}
    val = author_meta.get("fans") or author_meta.get("followers")
    if val and int(val) > 0:
        return int(val)

    val = scraped_data.get("likes")
    if val and isinstance(val, int) and val > 0:
        return val

    val = (scraped_data.get("edge_followed_by") or {}).get("count")
    if val and int(val) > 0:
        return int(val)

    return 0


def _compute_engagement_rate_from_posts(scraped_data: dict, followers: int) -> float:
    """
    Fallback: compute engagement rate from the scraped post sample when the
    platform does not report it natively (e.g. Instagram via Apify).

    engagement_rate = avg(likes + comments) per post / followers

    Only used when the platform-reported value is 0.
    Capped at 1.0 to avoid absurd values on tiny follower counts.
    """
    if followers <= 0:
        return 0.0

    posts = scraped_data.get("posts") or []
    if not posts:
        return 0.0

    total_interactions = 0
    counted = 0
    for post in posts:
        likes    = int(post.get("likes",    0) or post.get("likesCount",    0) or 0)
        comments = int(post.get("comments", 0) or post.get("commentsCount", 0) or 0)
        total_interactions += likes + comments
        counted += 1

    if counted == 0:
        return 0.0

    avg_interactions = total_interactions / counted
    rate = avg_interactions / followers
    rate = round(min(rate, 1.0), 6)

    logger.info(
        "Computed engagement_rate from %d posts: avg_interactions=%.1f, followers=%d → rate=%.4f",
        counted, avg_interactions, followers, rate,
    )
    return rate


def _build_engagement_signals(scraped_data: dict) -> dict:
    """
    Extract engagement signals using platform-reported data where available,
    falling back to sample-computed engagement rate when the platform omits it.
    """
    stats = scraped_data.get("stats") or {}
    posts = scraped_data.get("posts") or []

    followers = _resolve_followers(scraped_data)

    post_count = (
        scraped_data.get("post_count")
        or scraped_data.get("postsCount")
        or scraped_data.get("mediaCount")
        or (scraped_data.get("edge_owner_to_timeline_media") or {}).get("count")
        or stats.get("post_count")
        or len(posts)
    )
    if post_count == len(posts) and len(posts) < 100:
        logger.warning(
            "post_count falling back to sample size (%d) — "
            "profile scraper did not return a real total post count.",
            len(posts),
        )

    # ── Engagement rate: platform-reported first, compute from posts as fallback ──
    engagement_rate = float(
        scraped_data.get("engagement_rate")
        or scraped_data.get("engagementRate")
        or stats.get("engagement_rate")
        or 0
    )
    if engagement_rate == 0:
        engagement_rate = _compute_engagement_rate_from_posts(scraped_data, followers)

    total_react = max(stats.get("total_reactions", 0) or 0, 1)
    total_angry = stats.get("total_angry_reactions", 0) or 0
    total_sad   = stats.get("total_sad_reactions",   0) or 0
    angry_ratio = round(total_angry / total_react, 4)
    sad_ratio   = round(total_sad   / total_react, 4)

    return {
        "followers":       followers,
        "post_count":      int(post_count),
        "engagement_rate": round(engagement_rate, 4),
        "angry_ratio":     angry_ratio,
        "sad_ratio":       sad_ratio,
        "has_website":     int(bool(scraped_data.get("website"))),
        "has_phone":       int(bool(scraped_data.get("phone"))),
    }


def _derive_comment_sentiment_score(sentiment_result) -> float:
    if sentiment_result is None:
        return 0.5

    if hasattr(sentiment_result, "positive_pct"):
        total = (
            sentiment_result.positive_pct
            + sentiment_result.negative_pct
            + sentiment_result.neutral_pct
        )
        if total == 0:
            return 0.5
        score = (
            (sentiment_result.positive_pct * 1.0)
            + (sentiment_result.neutral_pct  * 0.5)
            + (sentiment_result.negative_pct * 0.0)
        ) / total
        return round(max(0.0, min(1.0, score)), 4)

    if isinstance(sentiment_result, dict):
        hint = sentiment_result.get("sentiment_hint", "mixed")
        return {"mostly_positive": 0.8, "mixed": 0.5, "mostly_negative": 0.2}.get(hint, 0.5)

    return 0.5


def _persist_scraped_signals(db: Session, seller: SellerProfile,
                              engagement: dict, resolved_age: int | None,
                              profile_photo_url: str | None = None):
    try:
        updated = False

        new_followers = engagement.get("followers", 0)
        if new_followers and getattr(seller, "followers", None) != new_followers:
            seller.followers = new_followers
            updated = True

        new_eng = engagement.get("engagement_rate", 0)
        if new_eng and getattr(seller, "engagement_rate", None) != new_eng:
            seller.engagement_rate = new_eng
            updated = True

        if resolved_age and not seller.account_age_days:
            seller.account_age_days = resolved_age
            updated = True

        if profile_photo_url and not getattr(seller, "profile_photo_url", None):
            seller.profile_photo_url = profile_photo_url
            updated = True

        if updated:
            db.add(seller)
            db.commit()
            db.refresh(seller)
            logger.info("Persisted fresh signals for seller %s", seller.display_name)

    except Exception as exc:
        logger.warning("Failed to persist scraped signals: %s", exc)
        db.rollback()


def _run_full_sentiment_analysis(
    scraped_data: dict,
    seller_profile_url: str,
    platform: str,
) -> tuple:
    from ai.sentiment.comment_sentiment import (
        analyze_sentiment,
        ScrapeResult,
        Comment,
    )

    comment_objs = _extract_comment_objects(scraped_data)
    if not comment_objs:
        return None, 0.5

    post_url = seller_profile_url
    for post in (scraped_data.get("posts") or []):
        url = post.get("url") or post.get("post_url")
        if url:
            post_url = url
            break

    post_text = None
    for post in (scraped_data.get("posts") or []):
        t = post.get("text") or post.get("message") or post.get("caption")
        if t:
            post_text = t
            break

    scrape_result = ScrapeResult(
        profile_url=seller_profile_url,
        post_url=post_url,
        comments=comment_objs,
        platform=platform,
        post_text=post_text,
    )

    try:
        result = analyze_sentiment(scrape_result)
        score  = _derive_comment_sentiment_score(result)
        return result, score
    except Exception as exc:
        logger.warning("Full sentiment pipeline failed: %s", exc)
        return None, 0.5


def _sentiment_result_to_dict(result) -> dict | None:
    if result is None:
        return None
    return {
        "positive_pct":   result.positive_pct,
        "negative_pct":   result.negative_pct,
        "neutral_pct":    result.neutral_pct,
        "irrelevant_pct": result.irrelevant_pct,
        "total_comments": result.total_comments,
        "total_analyzed": result.total_analyzed,
        "summary":        result.summary,
        "top_positive":   result.top_positive,
        "top_negative":   result.top_negative,
        "sentiment_hint": (
            "mostly_positive" if result.positive_pct >= 60
            else "mostly_negative" if result.negative_pct >= 40
            else "mixed"
        ),
        "total_count": result.total_comments,
    }


# ── AI Image Analysis ─────────────────────────────────────────────────────────

async def _download_image_temp(url: str) -> str | None:
    """Download an image URL to a temp file. Returns local path or None on failure."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            suffix = ".jpg"
            ct = resp.headers.get("content-type", "")
            if "png" in ct:
                suffix = ".png"
            elif "webp" in ct:
                suffix = ".webp"

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(resp.content)
                return f.name
    except Exception as exc:
        logger.warning("Image download failed (%s): %s", url, exc)
        return None


async def _analyze_post_images(scraped_data: dict) -> dict:
    """
    Download and run AI-image detection on post images.
    Checks up to MAX_IMAGES_TO_ANALYZE still images — videos and reels are skipped.
    """
    from ai.image_analyzer.fake_detector import check_image_authenticity

    posts = scraped_data.get("posts") or []

    result = {
        "total_images_checked": 0,
        "ai_generated_count":   0,
        "uncertain_count":      0,
        "ai_ratio":             0.0,
        "flagged_posts":        [],
    }

    image_tasks: list[tuple[str, str]] = []
    for post in posts:
        post_type = (
            post.get("type") or
            post.get("media_type") or
            post.get("product_type") or
            ""
        ).lower()
        if "video" in post_type or "reel" in post_type:
            continue

        img_url = (
            post.get("display_url") or
            post.get("displayUrl") or
            post.get("media_url") or
            post.get("image_url") or
            post.get("imageUrl") or
            post.get("thumbnail_url") or
            post.get("thumbnailUrl") or
            post.get("full_picture") or
            post.get("picture") or
            (post.get("media_url") if not (
                post.get("display_url") or post.get("displayUrl")
            ) else None)
        )

        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
            if any(img_url.lower().endswith(ext) for ext in (".mp4", ".m3u8", ".mov", ".avi")):
                img_url = None

        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
            post_url = post.get("post_url") or post.get("url") or post.get("link") or ""
            image_tasks.append((img_url, post_url))

    if not image_tasks:
        logger.info("_analyze_post_images: no image URLs found in %d posts", len(posts))
        return result

    for img_url, post_url in image_tasks[:MAX_IMAGES_TO_ANALYZE]:
        tmp_path = await _download_image_temp(img_url)
        if not tmp_path:
            continue

        try:
            analysis = check_image_authenticity(tmp_path)
            result["total_images_checked"] += 1

            if analysis.get("is_ai_generated"):
                result["ai_generated_count"] += 1
                result["flagged_posts"].append({
                    "post_url":       post_url,
                    "confidence":     analysis.get("confidence", 0.0),
                    "verdict_arabic": analysis.get("verdict_arabic", ""),
                    "reasons":        analysis.get("reasons", []),
                })
            elif analysis.get("is_uncertain"):
                result["uncertain_count"] += 1

        except Exception as exc:
            logger.warning("Image analysis failed for %s: %s", img_url, exc)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    checked = result["total_images_checked"]
    if checked > 0:
        result["ai_ratio"] = round(result["ai_generated_count"] / checked, 4)

    logger.info(
        "Image analysis: %d checked, %d AI-flagged, %d uncertain (ratio=%.2f)",
        result["total_images_checked"],
        result["ai_generated_count"],
        result["uncertain_count"],
        result["ai_ratio"],
    )

    return result


# ── Bonus cap helper ──────────────────────────────────────────────────────────

def _post_bonus_cap(score: int, has_reviews: bool, has_age: bool, followers: int) -> int:
    if has_reviews:
        return score

    if not has_age:
        if followers < 10_000:
            cap = 72
        elif followers < 50_000:
            cap = 75
        else:
            cap = 78
    else:
        cap = 76 if followers < 10_000 else 82

    return min(score, cap)


# ── Verdict signals builder ───────────────────────────────────────────────────

def _build_verdict_signals(
    seller: SellerProfile,
    resolved_age: int | None,
    engagement: dict,
    has_web: bool,
    has_phone: bool,
    trust_score: int,
    image_analysis: dict,
    reports: list,
    reviews: list,
    avg_stars: float | None,
    reports_summary,
    reviews_summary,
    raw_comments: list[str],
) -> dict:
    """
    Build the signals dict passed to generate_seller_verdict(), including ONLY
    fields that have real, non-zero data.  Zero/None fields are omitted so the
    LLM does not hallucinate commentary about missing information.
    """
    signals: dict = {
        "display_name": seller.display_name,
        "trust_score":  trust_score,
        "platform":     seller.platform.value if seller.platform else None,
    }

    # Only include numeric signals when they carry real information
    if resolved_age:
        signals["account_age_days"] = resolved_age

    post_count = engagement.get("post_count", 0)
    if post_count:
        signals["post_count"] = post_count

    followers = engagement.get("followers", 0)
    if followers:
        signals["followers"] = followers

    eng_rate = engagement.get("engagement_rate", 0)
    if eng_rate:
        signals["engagement_rate"] = round(eng_rate, 4)

    if has_web:
        signals["has_website"] = 1
    if has_phone:
        signals["has_phone"] = 1

    # AI image data — only include when images were actually checked
    ai_checked = image_analysis.get("total_images_checked", 0)
    if ai_checked > 0:
        signals["ai_images_checked"] = ai_checked
        signals["ai_images_flagged"] = image_analysis.get("ai_generated_count", 0)
        signals["ai_image_ratio"]    = image_analysis.get("ai_ratio", 0.0)

    # Reports — always include when present (even one report matters)
    if reports:
        signals["reports"] = [
            {
                "scam_type":         r.scam_type.value,
                "description":       r.description,
                "credibility_score": r.credibility_score,
            }
            for r in reports
        ]
    if reports_summary:
        signals["reports_summary"] = reports_summary

    # Reviews — only include when present
    if reviews:
        signals["reviews"]      = [{"stars": r.stars, "comment": r.comment} for r in reviews]
        signals["review_count"] = len(reviews)
    if avg_stars is not None:
        signals["avg_stars"] = avg_stars
    if reviews_summary:
        signals["reviews_summary"] = reviews_summary

    # Comments — only include when present
    if raw_comments:
        signals["scraped_comments"] = raw_comments[:20]

    return signals


# ── Main route ────────────────────────────────────────────────────────────────

@router.get("/search/")
async def search(q: str, force_rescrape: bool = False, db: Session = Depends(get_db)):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    q = q.strip()
    scraped_data    = None
    scrape_platform = None

    # ── 1. Try DB first ───────────────────────────────────────────────────────
    seller = (
        db.query(SellerProfile)
        .filter(
            (SellerProfile.profile_url.ilike(f"%{q}%")) |
            (SellerProfile.display_name.ilike(f"%{q}%"))
        )
        .first()
    )

    # ── 2. Scrape if: not found / stale / incomplete / forced ─────────────────
    is_url = (
        q.startswith("http") or
        "instagram.com" in q or
        "facebook.com"  in q or
        "tiktok.com"    in q
    )

    if is_url and (not seller or _is_stale(seller) or _is_incomplete(seller) or force_rescrape):
        try:
            from app.config import APIFY_API_KEY
            from app.services.scraping import detect_platform, normalize
            from app.services.scraping import (
                scrape_fb_page, scrape_ig_profile, scrape_tt_profile,
                scrape_fb_post, scrape_ig_post, scrape_tt_post,
            )

            platform = detect_platform(q)
            if platform:
                scrape_fn = {
                    "fb_page":    scrape_fb_page,
                    "fb_post":    scrape_fb_post,
                    "ig_profile": scrape_ig_profile,
                    "ig_post":    scrape_ig_post,
                    "tt_profile": scrape_tt_profile,
                    "tt_post":    scrape_tt_post,
                }.get(platform)

                if scrape_fn and APIFY_API_KEY:
                    raw = await scrape_fn(APIFY_API_KEY, q)
                    if raw:
                        try:
                            scraped_data = normalize(platform, raw)
                        except (TypeError, AttributeError) as exc:
                            logger.warning(
                                "normalize() failed for platform=%s: %s",
                                platform, exc,
                            )
                            scraped_data = None
                    if scraped_data:
                        scrape_platform = platform
                        seller = create_analysis(db, q, platform, scraped_data)

                        photo = scraped_data.get("profile_photo_url") or ""
                        if photo and seller and not getattr(seller, "profile_photo_url", None):
                            try:
                                seller.profile_photo_url = photo
                                db.add(seller)
                                db.commit()
                                db.refresh(seller)
                            except Exception as exc:
                                logger.warning("Could not persist profile_photo_url: %s", exc)
                                db.rollback()

        except Exception as exc:
            logger.warning("Scrape-on-search failed: %s", exc)

    if not seller:
        return {
            "found": False, "seller": None, "trust_score": None,
            "sentiment_summary": None,
            "image_analysis": {
                "total_images_checked": 0,
                "ai_generated_count": 0,
                "uncertain_count": 0,
                "ai_ratio": 0.0,
                "flagged_posts": [],
            },
            "reports": [], "reviews": [],
            "reports_summary": None, "reviews_summary": None,
            "avg_stars": None,
        }

    # ── 3. Load DB relations ──────────────────────────────────────────────────
    contacts  = db.query(SellerContact).filter(SellerContact.seller_id == seller.id).all()
    reports   = db.query(Report).filter(Report.seller_id == seller.id).order_by(Report.created_at.desc()).all()
    reviews   = db.query(Review).filter(Review.seller_id == seller.id).order_by(Review.created_at.desc()).all()
    avg_stars = round(sum(r.stars for r in reviews) / len(reviews), 1) if reviews else None

    # ── 4. Resolve account age: DB → bio → oldest post date ──────────────────
    resolved_age = seller.account_age_days
    if resolved_age is None and scraped_data:
        raw_bio = scraped_data.get("bio") or scraped_data.get("biography")
        bio = _coerce_str(raw_bio) if raw_bio else None
        resolved_age = _estimate_age_from_bio(bio)

    if resolved_age is None and scraped_data:
        resolved_age = _estimate_age_from_posts(scraped_data)
        if resolved_age:
            logger.info(
                "Estimated account age from oldest post: %d days for %s",
                resolved_age, getattr(seller, "display_name", q),
            )

    # ── 5. Build engagement signals ───────────────────────────────────────────
    has_phone = any(c.contact_type.value == "phone"              for c in contacts)
    has_web   = any(c.contact_type.value in ("website", "other") for c in contacts)

    if scraped_data:
        engagement = _build_engagement_signals(scraped_data)

        scraped_photo = scraped_data.get("profile_photo_url") or ""

        _persist_scraped_signals(
            db, seller, engagement, resolved_age,
            profile_photo_url=scraped_photo,
        )

        if engagement.get("followers", 0) > 0 and (getattr(seller, "followers", 0) or 0) == 0:
            logger.info(
                "Resolved previously-zero followers for %s → %d",
                seller.display_name, engagement["followers"],
            )
    else:
        engagement = {
            "followers":       getattr(seller, "followers",       None) or 0,
            "post_count":      getattr(seller, "post_count",      None) or 0,
            "engagement_rate": getattr(seller, "engagement_rate", None) or 0,
            "angry_ratio":     0.0,
            "sad_ratio":       0.0,
            "has_website":     int(bool(has_web)),
            "has_phone":       int(bool(has_phone)),
        }

    # ── 5b. AI image analysis ─────────────────────────────────────────────────
    image_analysis = {
        "total_images_checked": 0,
        "ai_generated_count":   0,
        "uncertain_count":      0,
        "ai_ratio":             0.0,
        "flagged_posts":        [],
    }
    if scraped_data:
        try:
            image_analysis = await _analyze_post_images(scraped_data)
        except Exception as exc:
            logger.warning("Post image analysis failed entirely: %s", exc)

    # ── 6. Sentiment analysis ─────────────────────────────────────────────────
    sentiment_result_obj    = None
    sentiment_summary       = None
    comment_sentiment_score = 0.5

    if scraped_data:
        platform_name = (
            (scrape_platform or "")
            .replace("_page", "")
            .replace("_profile", "")
            .replace("_post", "")
        )
        if not platform_name:
            platform_name = seller.platform.value if seller.platform else "unknown"

        try:
            sentiment_result_obj, comment_sentiment_score = _run_full_sentiment_analysis(
                scraped_data,
                seller_profile_url=seller.profile_url or q,
                platform=platform_name,
            )
            sentiment_summary = _sentiment_result_to_dict(sentiment_result_obj)
        except Exception as exc:
            logger.warning("Sentiment analysis failed entirely: %s", exc)

        if sentiment_summary is None:
            raw_comments = _extract_comments(scraped_data)
            if raw_comments:
                try:
                    from ai.feedback.summarizer import summarize_feedbacks
                    sentiment_summary = summarize_feedbacks(raw_comments[:30])
                    comment_sentiment_score = _derive_comment_sentiment_score(sentiment_summary)
                except Exception as exc:
                    logger.warning("Fallback sentiment summarizer failed: %s", exc)

    # ── 7. Build trust signals ────────────────────────────────────────────────
    signals = {
        "account_age_days":        resolved_age,
        "post_count":              engagement.get("post_count", 0),
        "followers":               engagement.get("followers", 0),
        "platform":                seller.platform.value,
        "has_phone_contact":       int(has_phone or bool(engagement.get("has_phone", 0))),
        "has_website":             int(has_web   or bool(engagement.get("has_website", 0))),
        "engagement_rate":         engagement.get("engagement_rate", 0),
        "angry_ratio":             engagement.get("angry_ratio", 0),
        "ai_image_ratio":          image_analysis.get("ai_ratio", 0.0),
        "comment_sentiment_score": comment_sentiment_score,
        "reports": [
            {"scam_type": r.scam_type.value, "credibility_score": r.credibility_score}
            for r in reports
        ],
        "reviews": [{"stars": r.stars} for r in reviews],
    }

    trust = calculate_trust_score(signals)

    # ── 8. Engagement bonus ───────────────────────────────────────────────────
    engagement_bonus = 0
    eng_rate    = engagement.get("engagement_rate", 0)
    angry_ratio = engagement.get("angry_ratio", 0)
    followers   = engagement.get("followers", 0)

    if eng_rate > 0:
        if followers >= 100_000:
            plausible_ceiling = 0.05
            bonus_scale       = 1.0
        elif followers >= 10_000:
            plausible_ceiling = 0.08
            bonus_scale       = 0.75
        else:
            plausible_ceiling = 0.15
            bonus_scale       = 0.5

        eng_is_plausible = eng_rate <= plausible_ceiling

        if eng_is_plausible and eng_rate > 0.05 and not reports:
            engagement_bonus = round(8 * bonus_scale)
        elif eng_is_plausible and eng_rate > 0.02 and not reports:
            engagement_bonus = round(4 * bonus_scale)
        elif not eng_is_plausible:
            engagement_bonus = -8

    if angry_ratio > 0.1:
        engagement_bonus -= 10

    # ── 8b. AI image penalty ──────────────────────────────────────────────────
    ai_image_penalty = 0
    ai_ratio   = image_analysis.get("ai_ratio", 0.0)
    ai_checked = image_analysis.get("total_images_checked", 0)
    ai_count   = image_analysis.get("ai_generated_count", 0)

    confidence   = min(ai_checked / 10, 1.0)
    scaled_ratio = ai_ratio * confidence

    if ai_checked == 0:
        ai_image_penalty = 0
    elif ai_checked < 3:
        if ai_count >= 1:
            ai_image_penalty = -5
    else:
        if scaled_ratio >= 0.6:
            ai_image_penalty = -20
        elif scaled_ratio >= 0.4:
            ai_image_penalty = -12
        elif scaled_ratio >= 0.2:
            ai_image_penalty = -6
        elif scaled_ratio > 0:
            ai_image_penalty = -3

    logger.info(
        "AI penalty debug → checked=%d, ai_count=%d, ratio=%.2f, confidence=%.2f, scaled=%.2f, penalty=%d",
        ai_checked, ai_count, ai_ratio, confidence, scaled_ratio, ai_image_penalty,
    )

    # ── 8c. Summarise reviews and reports ─────────────────────────────────────
    reviews_summary = None
    reports_summary = None

    if reviews:
        review_texts = [r.comment for r in reviews if r.comment and r.comment.strip()]
        if review_texts:
            try:
                from ai.feedback.summarizer import summarize_feedbacks
                reviews_summary = summarize_feedbacks(review_texts)
            except Exception as exc:
                logger.warning("Review summarizer failed: %s", exc)

    if reports:
        report_texts = [r.description for r in reports if r.description and r.description.strip()]
        if report_texts:
            try:
                from ai.feedback.summarizer import summarize_feedbacks
                prefixed = [f"[بلاغ] {t}" for t in report_texts]
                reports_summary = summarize_feedbacks(prefixed)
            except Exception as exc:
                logger.warning("Report summarizer failed: %s", exc)

    # ── 9. LLM verdict narrative ──────────────────────────────────────────────
    # Only pass signals that have real data — zeros are excluded so the LLM
    # does not generate commentary about missing/unavailable information.
    raw_comments_for_verdict = _extract_comments(scraped_data) if scraped_data else []
    verdict_narrative = ""

    try:
        verdict_signals = _build_verdict_signals(
            seller         = seller,
            resolved_age   = resolved_age,
            engagement     = engagement,
            has_web        = has_web,
            has_phone      = has_phone,
            trust_score    = trust.get("score", 0),
            image_analysis = image_analysis,
            reports        = reports,
            reviews        = reviews,
            avg_stars      = avg_stars,
            reports_summary  = reports_summary,
            reviews_summary  = reviews_summary,
            raw_comments     = raw_comments_for_verdict,
        )
        verdict_result    = generate_seller_verdict(verdict_signals)
        verdict_narrative = verdict_result.get("verdict", "")
    except Exception as exc:
        logger.warning("Verdict LLM failed: %s", exc)

    # ── 10. Sentiment bonus ───────────────────────────────────────────────────
    sentiment_bonus = 0
    if sentiment_summary:
        total_count = (
            sentiment_summary.get("total_count", 0) or
            sentiment_summary.get("total_comments", 0)
        )
        if total_count >= 5:
            hint = sentiment_summary.get("sentiment_hint", "mixed")
            if hint == "mostly_positive":
                sentiment_bonus = 8
            elif hint == "mixed":
                sentiment_bonus = 2
            elif hint == "mostly_negative":
                sentiment_bonus = -12

    # ── 11. Apply bonuses, enforce data-richness cap ──────────────────────────
    pre_bonus_score = trust["score"]
    raw_score = max(0, min(100,
        pre_bonus_score + engagement_bonus + sentiment_bonus + ai_image_penalty
    ))

    has_reviews_flag = len(reviews) >= 5
    has_age_flag     = resolved_age is not None
    followers_count  = int(engagement.get("followers", 0))

    final_score = _post_bonus_cap(
        score       = raw_score,
        has_reviews = has_reviews_flag,
        has_age     = has_age_flag,
        followers   = followers_count,
    )

    trust["score"] = final_score
    from ai.scoring.trust_score import _score_to_verdict
    trust["verdict"], trust["verdict_color"], trust["verdict_darija"] = _score_to_verdict(final_score)

    # ── Persist trust score to DB ─────────────────────────────────────────────
    try:
        seller.trust_score = final_score
        db.add(seller)
        db.commit()
        db.refresh(seller)
    except Exception as exc:
        logger.warning("Failed to persist trust_score: %s", exc)
        db.rollback()

    recommendation = trust["verdict"]

    db.refresh(seller)

    # ── 12. Response ──────────────────────────────────────────────────────────
    return {
        "found": True,
        "seller": {
            "id":                str(seller.id),
            "profile_url":       seller.profile_url,
            "platform":          seller.platform.value,
            "display_name":      seller.display_name,
            "profile_photo_url": getattr(seller, "profile_photo_url", None) or (scraped_data.get("profile_photo_url") if scraped_data else None),
            "account_age_days":  resolved_age,
            "post_count":        engagement.get("post_count", 0),
            "category":          seller.category,
            "followers":         engagement.get("followers", 0),
            "engagement_rate":   engagement.get("engagement_rate", 0),
            "contacts": [
                {"type": c.contact_type.value, "value": c.contact_value}
                for c in contacts
            ],
        },
        "trust_score": {
            "score":                trust.get("score", 0),
            "verdict_color":        trust.get("verdict_color", "grey"),
            "verdict":              trust.get("verdict", ""),
            "verdict_darija":       trust.get("verdict_darija", ""),
            "verdict_narrative":    verdict_narrative,
            "recommendation":       recommendation,
            "model_used":           trust.get("model_used", ""),
            "rule_based_score":     trust.get("rule_based_score", 0),
            "engagement_bonus":     engagement_bonus,
            "sentiment_bonus":      sentiment_bonus,
            "ai_image_penalty":     ai_image_penalty,
            "pre_bonus_score":      pre_bonus_score,
            "feature_values":       trust.get("feature_values", {}),
            "reports_contribution": trust.get("reports_contribution", "لا توجد بلاغات"),
            "reviews_contribution": trust.get("reviews_contribution", "لا توجد تقييمات بعد"),
        },
        "sentiment_summary": sentiment_summary,
        "image_analysis":    image_analysis,
        "reports": [
            {
                "id":                 str(r.id),
                "scam_type":          r.scam_type.value,
                "description":        r.description,
                "screenshot_url":     r.screenshot_url,
                "credibility_score":  r.credibility_score,
                "credibility_reason": r.credibility_reason,
                "created_at":         r.created_at.isoformat(),
            }
            for r in reports
        ],
        "reports_summary": reports_summary,
        "reviews": [
            {
                "id":              str(r.id),
                "stars":           r.stars,
                "comment":         r.comment,
                "product_matched": r.product_matched,
                "responded_fast":  r.responded_fast,
                "item_received":   r.item_received,
                "would_buy_again": r.would_buy_again,
                "created_at":      r.created_at.isoformat(),
            }
            for r in reviews
        ],
        "reviews_summary": reviews_summary,
        "avg_stars":        avg_stars,
    }