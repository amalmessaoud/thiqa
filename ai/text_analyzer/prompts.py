import json

FEW_SHOT_EXAMPLES = [
    # --- ADVANCE PAYMENT ---
    {
        "text": "حول ألفين دينار على البريدي موب وراه نبعث ليك الطرد بكري",
        "label": "scam",
        "scam_type": "advance_payment",
        "red_flags": ["طلب تحويل مسبق قبل الشحن", "لا دفع عند الاستلام"],
        "verdict_darija": "يطلب فلوس قبل ما يبعث — نصب واضح",
        "safe_to_proceed": False
    },
    {
        "text": "والله صاحبي ما عندي مشكل، غير دير التحويل على البريدي وراه نكملو، ثق فيا خويا ربي يوفق",
        "label": "scam",
        "scam_type": "advance_payment",
        "red_flags": ["طلب تحويل مسبق", "ضغط نفسي بكلام الثقة والدين"],
        "verdict_darija": "يستعمل كلام الثقة والدين باش يطلب فلوس قبل — علامة نصب",
        "safe_to_proceed": False
    },
    # --- GHOST SELLER ---
    {
        "text": "أنا في فرنسا دابا، نبعث ليك البضاعة بـ أمانة، غير دير التحويل الأول على البريدي موب",
        "label": "scam",
        "scam_type": "ghost_seller",
        "red_flags": ["البائع يدعي أنه في الخارج", "طلب تحويل مسبق", "شحن بدون لقاء"],
        "verdict_darija": "قصة أنا في الخارج مع طلب تحويل — نصب كلاسيكي معروف",
        "safe_to_proceed": False
    },
    {
        "text": "ما نقدرش نتلاقاو، أنا بعيد، نبعث ليك غير حول لي الفلوس على الحساب",
        "label": "scam",
        "scam_type": "ghost_seller",
        "red_flags": ["رفض اللقاء الشخصي", "طلب تحويل بدون ضمان"],
        "verdict_darija": "يرفض اللقاء ويطلب تحويل — خطر كبير",
        "safe_to_proceed": False
    },
    # --- FAKE PRODUCT ---
    {
        "text": "عندي آيفون أوريجينال بكاش تشري؟ السعر مناسب والصورة واضحة",
        "label": "scam",
        "scam_type": "fake_product",
        "red_flags": ["سعر مشبوه منخفض جداً", "لا إمكانية فحص المنتج", "صور من الأنترنت"],
        "verdict_darija": "سعر رخيص بزاف على منتج غالي — احتمال كبير منتج مزور",
        "safe_to_proceed": False
    },
    {
        "text": "جديد في الكرتون ما فتحتوش، جبته من الخارج، ما نقدرش تجي تشوفه، نبعث ليك غير",
        "label": "scam",
        "scam_type": "fake_product",
        "red_flags": ["رفض الفحص قبل الشراء", "ادعاء أنه جديد بدون إثبات"],
        "verdict_darija": "يرفض الفحص ويدعي أنه جديد — علامة منتج مزور",
        "safe_to_proceed": False
    },
    # --- WRONG ITEM ---
    {
        "text": "البضاعة جات مش هي لي طلبت، كلمته ما ردش، رقمه ما يرد",
        "label": "scam",
        "scam_type": "wrong_item",
        "red_flags": ["منتج مختلف عن الإعلان", "البائع لا يرد بعد البيع"],
        "verdict_darija": "بعث منتج غلط وقطع التواصل — نصب واضح",
        "safe_to_proceed": False
    },
    # --- NO RESPONSE ---
    {
        "text": "حولت الفلوس وراه ما ردش، الحساب مازال موجود بصح ما يقراش",
        "label": "scam",
        "scam_type": "no_response",
        "red_flags": ["اختفى بعد استلام الأموال", "لا رد على الرسائل"],
        "verdict_darija": "أخذ الفلوس وغاب — نصب مؤكد",
        "safe_to_proceed": False
    },
    # --- LEGIT ---
    {
        "text": "البضاعة عندي في الدار، تقدر تجي تشوفها وتخلص كاش، ما نقبلش تحويل مسبق",
        "label": "legit",
        "scam_type": None,
        "red_flags": [],
        "verdict_darija": "البائع يقبل الكاش عند الاستلام ويقدر المشتري يشوف — علامة إيجابية",
        "safe_to_proceed": True
    },
    {
        "text": "نبعث بياليدين، تخلص عند الاستلام، ما فيها مشكل، عندي سجل تجاري",
        "label": "legit",
        "scam_type": None,
        "red_flags": [],
        "verdict_darija": "دفع عند الاستلام مع شحن موثوق — بائع جدي",
        "safe_to_proceed": True
    },
    {
        "text": "عندي محل في باب الزوار، تعال تشوف البضاعة بعينك وتخلص في المحل",
        "label": "legit",
        "scam_type": None,
        "red_flags": [],
        "verdict_darija": "محل حقيقي مع دفع عند الاستلام — موثوق",
        "safe_to_proceed": True
    },
]

MAX_TEXT_CHARS = 3000


def build_analysis_prompt(text: str) -> str:
    if len(text) > MAX_TEXT_CHARS:
        text = "...[محذوف]...\n" + text[-MAX_TEXT_CHARS:]

    examples_str = json.dumps(FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2)

    return f"""أنت نظام ذكاء اصطناعي متخصص في كشف عمليات النصب في أسواق البيع أونلاين في الجزائر.
المدخلات دائماً باللغة العربية أو الدارجة الجزائرية المكتوبة بالحروف العربية.

أنواع النصب الشائعة في الجزائر:
- ghost_seller: البائع يدعي أنه في الخارج ويطلب تحويل مسبق
- advance_payment: يطلب تحويل فلوس على البريدي موب أو CCP قبل الشحن
- fake_product: منتج مزور أو صور مسروقة من الأنترنت
- wrong_item: بعث منتج مختلف عن الإعلان
- no_response: اختفى بعد استلام الأموال

علامات الخطر الشائعة:
- طلب تحويل مسبق على البريدي موب أو CCP أو باي كونترول
- عبارات الضغط النفسي: "ثق فيا"، "والله ما نكذبك"، "ربي يوفق"، "اليوم فقط"
- رفض اللقاء الشخصي أو الفحص قبل الشراء
- ادعاء وجود البائع في الخارج
- سعر منخفض جداً مقارنة بالسوق

أمثلة:
{examples_str}

الآن حلل هذا الإدخال (قد يكون رسالة واحدة أو محادثة كاملة):
---
{text}
---

أعد JSON فقط بهذه المفاتيح بالضبط:
- label: "scam" أو "legit" أو "unknown"
- scam_type: واحد من ["ghost_seller", "advance_payment", "fake_product", "wrong_item", "no_response"] أو null
- red_flags: قائمة جمل قصيرة بالعربية تصف كل علامة خطر (قائمة فارغة إذا لم توجد)
- verdict_darija: جملة واحدة بالدارجة الجزائرية تلخص الحكم على كامل المحادثة
- safe_to_proceed: true أو false

قواعد:
- إذا كانت المحادثة غامضة أو ناقصة أعد "unknown" وليس "legit"
- ركز على رسائل البائع وليس المشتري
- لا تضيف أي شيء خارج JSON، لا شرح، لا markdown، لا backticks"""