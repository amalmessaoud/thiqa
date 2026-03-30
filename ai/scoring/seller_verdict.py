# ai/scoring/seller_verdict.py
from ai.utils.llm_client import call_llm

def generate_seller_verdict(seller_data: dict) -> dict:
    """
    Generate a Darija verdict narrative for a seller based on reports and reviews.
    Returns: { verdict: str, recommendation: str }
    """
    reports      = seller_data.get("reports", [])
    reviews      = seller_data.get("reviews", [])
    display_name = seller_data.get("display_name", "هذا البائع")
    age          = seller_data.get("account_age_days")
    post_count   = seller_data.get("post_count")
    avg_stars    = seller_data.get("avg_stars")
    review_count = seller_data.get("review_count", 0)

    if not reports and not reviews:
        return {
            "verdict":        "ما كاينش معلومات كافية على هذا البائع بعد.",
            "recommendation": "احذر",
        }

    reports_text = "\n".join([
        f"- نوع النصب: {r.get('scam_type')} | المصداقية: {r.get('credibility_score', '?')} | {r.get('description') or ''}"
        for r in reports
    ]) or "لا توجد بلاغات"

    reviews_text = "\n".join([
        f"- {r.get('stars')}/5 نجوم | {r.get('comment') or 'بدون تعليق'}"
        for r in reviews
    ]) or "لا توجد تقييمات"

    prompt = f"""أنت مساعد تحقق من البائعين الجزائريين على الإنترنت.

معلومات البائع:
- الاسم: {display_name}
- عمر الحساب: {age or 'غير معروف'} يوم
- عدد المنشورات: {post_count or 'غير معروف'}
- متوسط التقييم: {avg_stars or 'لا يوجد'} ({review_count} تقييم)

البلاغات:
{reports_text}

التقييمات:
{reviews_text}

اكتب حكماً من 2-3 جمل بالدارجة الجزائرية على هذا البائع بناءً على المعلومات أعلاه.
ثم في السطر الأخير اكتب فقط كلمة واحدة من: تعامل | احذر | تجنب

مثال للرد:
هذا البائع عندو بلاغات متعددة على النصب ومصداقيتها عالية. الناس تشكي من أنه ياخذ الفلوس وما يبعتش. 
تجنب"""

    try:
        raw = call_llm(prompt).strip()
        lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]

        recommendation = "احذر"
        for word in ["تعامل", "احذر", "تجنب"]:
            if word in lines[-1]:
                recommendation = word
                break

        verdict = raw.replace(lines[-1], "").strip() if recommendation in lines[-1] else raw

        return {"verdict": verdict, "recommendation": recommendation}

    except Exception as e:
        return {
            "verdict":        "تعذر توليد الحكم تلقائياً.",
            "recommendation": "احذر",
        }