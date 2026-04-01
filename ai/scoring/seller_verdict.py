# ai/scoring/seller_verdict.py
from ai.utils.llm_client import call_llm


def generate_seller_verdict(seller_data: dict) -> dict:
    """
    Generate a Darija verdict narrative for a seller.
    Always produces output — falls back to profile-signal reasoning
    when there are no reports, reviews, or scraped comments.

    Returns: { verdict: str, recommendation: str }
    """
    reports          = seller_data.get("reports", [])
    reviews          = seller_data.get("reviews", [])
    scraped_comments = seller_data.get("scraped_comments", [])
    display_name     = seller_data.get("display_name", "هذا البائع")
    age              = seller_data.get("account_age_days")
    post_count       = seller_data.get("post_count")
    followers        = seller_data.get("followers", 0)
    engagement_rate  = seller_data.get("engagement_rate", 0)
    avg_stars        = seller_data.get("avg_stars")
    review_count     = seller_data.get("review_count", len(reviews))
    has_website      = seller_data.get("has_website", 0)
    has_phone        = seller_data.get("has_phone", 0)
    trust_score      = seller_data.get("trust_score")

    # ── Format each section ────────────────────────────────────────────────────

    # Account age: human-readable
    if age:
        if age >= 365:
            age_str = f"حوالي {age // 365} سنة"
        elif age >= 30:
            age_str = f"حوالي {age // 30} شهر"
        else:
            age_str = f"{age} يوم"
    else:
        age_str = "غير معروف"

    # Engagement
    eng_pct = round((engagement_rate or 0) * 100, 2)

    # Contact signals
    contact_parts = []
    if has_website:
        contact_parts.append("موقع رسمي")
    if has_phone:
        contact_parts.append("رقم هاتف")
    contact_str = " و".join(contact_parts) if contact_parts else "لا يوجد"

    # Trust score context (only include if available)
    score_str = f"نقطة الثقة المحسوبة: {trust_score}/100\n" if trust_score is not None else ""

    # Reports
    if reports:
        reports_text = "\n".join([
            f"- نوع النصب: {r.get('scam_type')} | "
            f"المصداقية: {r.get('credibility_score', '?')} | "
            f"{r.get('description') or 'بدون وصف'}"
            for r in reports
        ])
    else:
        reports_text = "لا توجد بلاغات مسجّلة"

    # Reviews
    if reviews:
        reviews_text = "\n".join([
            f"- {r.get('stars')}/5 نجوم | {r.get('comment') or 'بدون تعليق'}"
            for r in reviews
        ])
        reviews_text += f"\n(المتوسط: {avg_stars}/5 من {review_count} تقييم)"
    else:
        reviews_text = "لا توجد تقييمات من المشترين بعد"

    # Scraped comments — deduplicated, non-trivial
    seen: set[str] = set()
    sample_comments: list[str] = []
    for c in scraped_comments:
        c = c.strip()
        if c and c not in seen and len(c) > 3:
            seen.add(c)
            sample_comments.append(c)
        if len(sample_comments) >= 15:
            break

    if sample_comments:
        comments_text = "\n".join(f"- {c}" for c in sample_comments)
    else:
        comments_text = "لا توجد تعليقات مجمّعة من المنشورات"

    # ── Prompt ────────────────────────────────────────────────────────────────
    prompt = f"""أنت مساعد تحقق من البائعين الجزائريين على الإنترنت لمنصة "ثقة".

معلومات البائع:
- الاسم: {display_name}
- عمر الحساب: {age_str}
- عدد المنشورات: {post_count or 'غير معروف'}
- عدد المتابعين: {followers:,}
- معدل التفاعل: {eng_pct}%
- معلومات التواصل: {contact_str}
{score_str}
البلاغات:
{reports_text}

تقييمات المشترين:
{reviews_text}

تعليقات المتابعين على المنشورات:
{comments_text}

مهمتك:
اكتب حكماً واضحاً من 2-3 جمل بالدارجة الجزائرية على هذا البائع.
- إذا كانت المعلومات محدودة، اعتمد على إشارات الحساب (العمر، المتابعين، المنشورات، التواصل).
- لا تقل "معلومات غير كافية" — دائماً أعطِ رأياً بناءً على ما هو متاح.
- خذ بعين الاعتبار طبيعة التعليقات إن وُجدت: مدح، شكاوي، أسئلة عن الأسعار.
- اكتب فقط الحكم النصي، بدون أي كلمة توصية في الآخر.

مثال للرد:
هذا البائع عندو منشورات كثيرة وموقع رسمي، وما كاينش بلاغات. التعليقات إيجابية بصح ما عندناش معلومات عن عمر الحساب."""

    try:
        raw   = call_llm(prompt).strip()
        lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
        verdict = " ".join(lines).strip()

        # Sanity: if LLM returned nothing useful, build a minimal verdict
        if not verdict:
            verdict = _minimal_verdict(display_name, followers, post_count, has_website, reports)

        return {"verdict": verdict}

    except Exception:
        return {
            "verdict": _minimal_verdict(display_name, followers, post_count, has_website, reports),
        }


def _minimal_verdict(display_name: str, followers: int, post_count, has_website: int, reports: list) -> str:
    """Rule-based fallback verdict when the LLM is unavailable."""
    parts = []

    if reports:
        parts.append(f"كاينين {len(reports)} بلاغ على هذا البائع، خليك حذر.")
    else:
        parts.append("ما كاينش بلاغات على هذا البائع.")

    if followers and followers > 1000:
        parts.append(f"عندو {followers:,} متابع.")
    elif followers and followers > 0:
        parts.append(f"متابعينه قليلين ({followers:,}).")

    if has_website:
        parts.append("عندو موقع رسمي، هذا علامة إيجابية.")

    if not parts:
        parts.append("معلومات محدودة، كن حذراً في التعامل.")

    return " ".join(parts)