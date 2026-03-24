from ai.constants import ScamType, NO_RESPONSE_PATTERNS

# What each scam type looks like as screenshot evidence
SCAM_TYPE_SCREENSHOT_HINTS = {
    ScamType.ADVANCE_PAYMENT: [
        "طلب تحويل على البريدي موب أو CCP",
        "رقم حساب أو RIP",
        "كلمات مثل: حول، تحويل، BaridiMob، CCP، PayControl",
    ],
    ScamType.GHOST_SELLER: [
        "ادعاء وجود البائع في الخارج",
        "طلب تحويل مع وعد بالشحن",
        "كلمات مثل: فرنسا، الخارج، أمانة، Amana",
    ],
    ScamType.FAKE_PRODUCT: [
        "صور مسروقة أو منتج لا يطابق الوصف",
        "رفض الفحص قبل الشراء",
        "سعر منخفض جداً",
    ],
    ScamType.WRONG_ITEM: [
        "صور تثبت أن المنتج المستلم مختلف عن الإعلان",
        "شكوى المشتري من المنتج الخاطئ",
    ],
    ScamType.NO_RESPONSE: [
        "رسائل المشتري بدون رد",
        "إشعار الحظر أو عدم إمكانية الرد",
        *NO_RESPONSE_PATTERNS,
    ],
    ScamType.OTHER: [
        "أي دليل على سلوك مشبوه",
    ],
}


def build_credibility_prompt(
    scam_type: str,
    description: str | None,
    screenshot_text: str,
) -> str:
    hints = SCAM_TYPE_SCREENSHOT_HINTS.get(
        ScamType(scam_type) if scam_type in ScamType._value2member_map_ else ScamType.OTHER,
        SCAM_TYPE_SCREENSHOT_HINTS[ScamType.OTHER]
    )
    hints_str = "\n".join(f"- {h}" for h in hints)
    description_str = description.strip() if description else "لم يقدم المبلغ وصفاً"
    screenshot_str = screenshot_text.strip() if screenshot_text else "لم يتم استخراج نص من لقطة الشاشة"

    return f"""أنت نظام تقييم مصداقية بلاغات النصب في الجزائر.
مهمتك: تقييم مدى مصداقية بلاغ مقدم من مشترٍ ضد بائع أونلاين.

نوع النصب المُبلَّغ عنه: {scam_type}

ما الذي تبدو عليه لقطة الشاشة الداعمة لهذا النوع من النصب:
{hints_str}

وصف المبلغ:
{description_str}

النص المستخرج من لقطة الشاشة بالـ OCR:
{screenshot_str}

قيّم مصداقية هذا البلاغ بناءً على:
1. هل النص في لقطة الشاشة يدعم نوع النصب المُبلَّغ عنه؟
2. هل الوصف محدد وتفصيلي أم غامض؟
3. هل الوصف يتطابق مع محتوى لقطة الشاشة؟
4. في حالة no_response: وجود إشعار الحظر أو رسائل بدون رد يُعدّ دليلاً قوياً

أعد JSON فقط بهذه المفاتيح بالضبط:
- credibility_score: رقم من 0.0 إلى 1.0
  * 0.8–1.0: لقطة الشاشة تدعم البلاغ بشكل واضح والوصف تفصيلي
  * 0.5–0.7: لقطة الشاشة تدعم جزئياً أو الوصف غامض نوعاً ما
  * 0.3–0.4: لا يوجد نص في لقطة الشاشة لكن الوصف معقول
  * 0.0–0.2: تناقض بين الوصف ولقطة الشاشة أو بلاغ مشبوه
- credibility_label: "high" إذا كان Score >= 0.7، "medium" إذا كان >= 0.4، "low" إذا كان < 0.4
- reason: جملة واحدة بالدارجة الجزائرية تشرح التقييم
- screenshot_supports_claim: true أو false

لا تضيف أي شيء خارج JSON، لا شرح، لا markdown، لا backticks"""