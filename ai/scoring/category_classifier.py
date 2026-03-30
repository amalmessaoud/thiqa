"""
Seller category classifier — rule-based fallback (no LLM required).
Classifies based on keywords found in seller name + post texts.
"""

import random

CATEGORIES = [
    "ملابس",
    "إلكترونيات",
    "منتجات_أطفال",
    "منتجات_غذائية",
    "مستحضرات_تجميل",
    "أثاث_وديكور",
    "متجر_إلكتروني",
    "فن_وحرف",
    "خدمات",
    "أخرى",
]

# keyword → category (Arabic, French, English mixed — mirrors real Algerian seller content)
_RULES: list[tuple[list[str], str]] = [
    (["قندورة", "حايك", "جلابة", "كسوة", "خياطة", "mode", "fashion", "robe", "vêtement",
      "ملابس", "فساتين", "بلوزة", "تنورة", "clothing", "boutique"], "ملابس"),

    (["هاتف", "تلفون", "لابتوب", "كمبيوتر", "phone", "iphone", "samsung", "laptop",
      "électronique", "تقنية", "إلكترونيات", "tech", "istore", "gsm"], "إلكترونيات"),

    (["أطفال", "بيبي", "baby", "enfant", "jouet", "لعبة", "حفاضات", "poussette",
      "منتجات أطفال", "kids"], "منتجات_أطفال"),

    (["أكل", "طبخ", "حلويات", "كسكس", "مأكولات", "food", "épicerie", "chocolat",
      "gateau", "منتجات غذائية", "بقالة", "مربى", "زيت", "عسل", "tartelette"], "منتجات_غذائية"),

    (["كريم", "عطر", "مكياج", "beauty", "makeup", "cosmétique", "parfum", "soin",
      "مستحضرات", "تجميل", "روج", "ماسكارا", "skincare"], "مستحضرات_تجميل"),

    (["أثاث", "ديكور", "كنبة", "طاولة", "meuble", "décor", "salon", "chambre",
      "mobilier", "منزل", "بيت"], "أثاث_وديكور"),

    (["متجر", "بيع وشراء", "souq", "market", "store", "shop", "vente en ligne",
      "online", "livraison", "توصيل", "commande", "طلب"], "متجر_إلكتروني"),

    (["رسم", "يدوي", "حرف", "صناعة تقليدية", "artisanat", "art", "handmade",
      "broderie", "poterie", "فن", "خزف"], "فن_وحرف"),

    (["خدمة", "استشارة", "service", "conseil", "formation", "تدريب", "startup",
      "agence", "وكالة", "freelance"], "خدمات"),
]


def classify_seller_category(text: str) -> str:
    """
    Classify a seller into one Arabic category based on their name/post text.

    Strategy:
      1. Keyword matching (deterministic, fast)
      2. Falls back to 'متجر_إلكتروني' for generic Algerian market names
      3. Returns 'أخرى' if nothing matches

    Args:
        text: seller name + bio + post captions concatenated (any language)

    Returns:
        One of the CATEGORIES strings.
    """
    if not text or not text.strip():
        return "أخرى"

    lower = text.lower()

    scores: dict[str, int] = {cat: 0 for cat in CATEGORIES}

    for keywords, category in _RULES:
        for kw in keywords:
            if kw.lower() in lower:
                scores[category] += 1

    best_cat = max(scores, key=lambda c: scores[c])
    best_score = scores[best_cat]

    if best_score > 0:
        return best_cat

    # Generic Algerian market fallback
    market_hints = ["algeria", "algérie", "dz", "جزائر", "وهران", "قسنطينة", "algiers"]
    if any(h in lower for h in market_hints):
        return "متجر_إلكتروني"

    return "أخرى"