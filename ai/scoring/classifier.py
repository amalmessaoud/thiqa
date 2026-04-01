"""
ai/category/classifier.py

Seller category classifier — LLM-powered via Groq.

Two-tier approach:
  1. Fast keyword pre-check (instant, no API call) → catches obvious cases
  2. LLM fallback (Groq) → handles ambiguous / mixed-language content

Improvements (v2):
  - Expanded keyword lists with Algerian Darija terms and French variants
  - Weighted keyword scoring: exact category name hits count double
  - Minimum confidence threshold raised to 3 hits (was 2)
  - Disambiguation: if top two categories are within 1 hit, escalate to LLM
  - Better LLM prompt with few-shot Algerian examples
  - New "متجر_إلكتروني" detection for mixed/general stores
"""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Category taxonomy ──────────────────────────────────────────────────────────
CATEGORIES = [
    "ملابس",
    "إلكترونيات",
    "منتجات_أطفال",
    "منتجات_غذائية",
    "مستحضرات_تجميل",
    "أثاث_وديكور",
    "فن_وحرف",
    "خدمات",
    "متجر_إلكتروني",
    "أخرى",
]

# Category descriptions for the LLM prompt
_CAT_DESCRIPTIONS = """
- ملابس: clothing, fashion, fabric, traditional Algerian dress (قندورة، حايك، جلابة، كسوة), robe, vêtements, mode, boutique, قماش, خياطة, تفصيل
- إلكترونيات: phones, laptops, gadgets, tech accessories, TV, électronique, هاتف, لابتوب, GSM, إصلاح, فلاشة, smatphone, tablette, accessoire
- منتجات_أطفال: baby products, toys (لعبة، ألعاب), diapers (حفاضات), children clothing, jouets, enfants, poussette, biberon, landau, berceau
- منتجات_غذائية: food, sweets, pastries, épicerie, honey, oil, gateau, groceries, أكل, حلويات, كسكس, طاجين, مربى, زيت زيتون, عسل, بقالة, قهوة, شاي, زبدة, جبن, سميد
- مستحضرات_تجميل: makeup, cosmetics, skincare, perfume, beauty, maquillage, soins, كريم, عطر, مكياج, روج, ماسكارا, serum, lotion, بشرة, شعر, تجميل, حلاقة, ناشف
- أثاث_وديكور: furniture, home decor, chairs, tables, meubles, décor, salon, chambre, كنبة, طاولة, خزانة, بيبان, بلاط, ستائر, مطبخ, غرفة
- فن_وحرف: handmade, art, pottery, embroidery, artisanat, woodwork, paintings, رسم, تصوير, يدوي, خزف, حرف تقليدية, تطريز, نحت, خشب, فخار
- خدمات: digital services, consulting, freelance, formation, agence, marketing, تسويق, تصميم, برمجة, تدريب, دورة, استشارة, صيانة, نقل, توصيل
- متجر_إلكتروني: general online store selling mixed product categories, livraison, commande, متجر, بيع, شراء, طلب, توصيل, dropshipping, grossiste
- أخرى: doesn't clearly fit any of the above categories
"""

# ── Keyword rules (expanded) ──────────────────────────────────────────────────
# Each entry: (keyword_list, category, weight)
# weight=2 means the keyword is a strong signal (e.g. category name itself)
_RULES: list[tuple[list[str], str, int]] = [
    # ── ملابس ──────────────────────────────────────────────────────────────
    ([
        "قندورة", "حايك", "جلابة", "كسوة", "خياطة", "تفصيل",
        "mode", "fashion", "robe", "vêtement", "vêtements",
        "ملابس", "فساتين", "بلوزة", "تنورة", "قميص",
        "جينز", "تيشرت", "سروال", "عباية", "حجاب",
        "clothing", "boutique", "قماش", "نسيج", "tissu",
        "prêt-à-porter", "collection", "saison",
    ], "ملابس", 1),
    (["ملابس", "fashion boutique", "mode algérie"], "ملابس", 2),

    # ── إلكترونيات ────────────────────────────────────────────────────────
    ([
        "هاتف", "تلفون", "لابتوب", "كمبيوتر",
        "phone", "iphone", "samsung", "laptop", "huawei", "xiaomi", "oppo",
        "électronique", "تقنية", "إلكترونيات", "tech",
        "istore", "gsm", "écran", "clavier", "chargeur", "شاحن",
        "tablette", "accessoire", "سماعة", "écouteur", "airpods",
        "tv", "télévision", "شاشة", "console", "playstation",
        "فلاشة", "usb", "batterie", "بطارية", "إصلاح", "réparation",
        "smatphone", "smartphone",
    ], "إلكترونيات", 1),
    (["إلكترونيات", "electronics store", "magasin gsm"], "إلكترونيات", 2),

    # ── منتجات_أطفال ──────────────────────────────────────────────────────
    ([
        "أطفال", "بيبي", "baby", "enfant", "jouet", "jouets",
        "لعبة", "ألعاب", "حفاضات", "poussette", "kids",
        "biberon", "landau", "berceau", "trotteur",
        "مولود", "رضيع", "حضانة", "maternité",
        "ملابس أطفال", "vêtements bébé",
    ], "منتجات_أطفال", 1),
    (["منتجات أطفال", "baby store", "puériculture"], "منتجات_أطفال", 2),

    # ── منتجات_غذائية ─────────────────────────────────────────────────────
    ([
        "أكل", "طبخ", "حلويات", "كسكس", "مأكولات", "food",
        "épicerie", "chocolat", "gateau", "gâteau",
        "منتجات غذائية", "بقالة", "مربى", "زيت", "عسل",
        "tartelette", "cuisine", "وصفة", "recette",
        "قهوة", "شاي", "زبدة", "جبن", "سميد", "دقيق",
        "لحم", "سمك", "خضرة", "فواكه", "épices", "بهارات",
        "زيت زيتون", "تمر", "couscous", "baklava", "makroud",
        "msemen", "مسمن", "بغرير",
    ], "منتجات_غذائية", 1),
    (["منتجات غذائية", "épicerie fine", "food store algérie"], "منتجات_غذائية", 2),

    # ── مستحضرات_تجميل ────────────────────────────────────────────────────
    ([
        "كريم", "عطر", "مكياج", "beauty", "makeup",
        "cosmétique", "cosmétiques", "parfum", "soin", "soins",
        "مستحضرات", "تجميل", "روج", "ماسكارا",
        "skincare", "serum", "lotion", "fond de teint",
        "بشرة", "شعر", "حلاقة", "ناشف", "مزيل",
        "eye shadow", "contour", "highlighter",
        "شامبو", "conditioner", "huile", "زيت الشعر",
        "تبييض", "نضارة", "anti-âge",
    ], "مستحضرات_تجميل", 1),
    (["مستحضرات تجميل", "beauty store", "cosmétique algérie"], "مستحضرات_تجميل", 2),

    # ── أثاث_وديكور ───────────────────────────────────────────────────────
    ([
        "أثاث", "ديكور", "كنبة", "طاولة", "meuble", "meubles",
        "décor", "décoration", "salon", "chambre",
        "mobilier", "منزل", "بيت", "canapé", "bibliothèque",
        "خزانة", "بيبان", "بلاط", "ستائر", "مطبخ", "غرفة",
        "تصميم داخلي", "intérieur", "luminaire", "مصباح",
        "tapis", "سجادة", "rideau", "لوحة", "tableau mural",
    ], "أثاث_وديكور", 1),
    (["أثاث وديكور", "décoration maison", "meubles algérie"], "أثاث_وديكور", 2),

    # ── فن_وحرف ───────────────────────────────────────────────────────────
    ([
        "رسم", "يدوي", "حرف", "صناعة تقليدية", "artisanat",
        "art", "handmade", "broderie", "poterie",
        "فن", "خزف", "tableau", "peinture", "نحت",
        "تطريز", "خشب", "woodwork", "macramé", "résine",
        "calligraphie", "خط عربي", "لوحة يدوية",
        "illustration", "aquarelle",
    ], "فن_وحرف", 1),
    (["فن وحرف", "artisanat algérien", "art handmade"], "فن_وحرف", 2),

    # ── خدمات ─────────────────────────────────────────────────────────────
    ([
        "خدمة", "استشارة", "service", "conseil", "formation",
        "تدريب", "startup", "agence", "وكالة",
        "freelance", "digital", "تسويق", "marketing",
        "تصميم", "برمجة", "موقع", "développement", "design",
        "photographie", "تصوير", "vidéo", "مونتاج",
        "dépannage", "صيانة", "installation", "نقل", "déménagement",
        "coaching", "cours", "دورة", "تعليم",
    ], "خدمات", 1),
    (["خدمات رقمية", "agence digitale", "freelance algérie"], "خدمات", 2),

    # ── متجر_إلكتروني ─────────────────────────────────────────────────────
    ([
        "توصيل", "livraison", "commande", "طلب", "بيع",
        "متجر", "store", "boutique en ligne", "shop",
        "dropshipping", "grossiste", "gros", "جملة",
        "كتالوج", "catalogue", "prix", "سعر", "promo",
    ], "متجر_إلكتروني", 1),
    (["متجر إلكتروني", "online store", "vente en ligne"], "متجر_إلكتروني", 2),
]

# Minimum total score to trust keyword result without LLM confirmation
_MIN_CONFIDENCE = 3
# If top two categories are within this margin, escalate to LLM
_AMBIGUITY_MARGIN = 2


def _keyword_classify(text: str) -> Optional[str]:
    """
    Returns a category if keywords are confident enough, else None.

    Scoring:
      - Each keyword hit adds its rule weight (1 or 2) to the category score.
      - Result is trusted only if:
          a) top score >= _MIN_CONFIDENCE  AND
          b) top score leads second-best by > _AMBIGUITY_MARGIN
    """
    lower = text.lower()
    scores: dict[str, int] = {}

    for keywords, category, weight in _RULES:
        for kw in keywords:
            if kw.lower() in lower:
                scores[category] = scores.get(category, 0) + weight

    if not scores:
        return None

    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_cats[0]
    second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0

    # Require minimum confidence
    if best_score < _MIN_CONFIDENCE:
        return None

    # Require clear winner (avoid ambiguous ties)
    if (best_score - second_score) <= _AMBIGUITY_MARGIN and len(sorted_cats) > 1:
        logger.debug(
            "Ambiguous keyword match: %s=%d vs %s=%d — escalating to LLM",
            best_cat, best_score, sorted_cats[1][0], second_score,
        )
        return None

    return best_cat


# ── LLM classifier ─────────────────────────────────────────────────────────────

_FEW_SHOT_EXAMPLES = """
Examples:
- "قندورة عصرية، بلوزة، تفصيل على القياس، Robe kabyle" → ملابس
- "iPhone 15 Pro neuf, Samsung S24, رسيفر, شاحن أصلي" → إلكترونيات
- "حلويات عيد، طرطة، makroud, مقروض, gateau sec" → منتجات_غذائية
- "كريم تبييض، parfum original, maquillage MAC" → مستحضرات_تجميل
- "كنبة salon, طاولة صالون, décoration maison" → أثاث_وديكور
- "صناعة يدوية، poterie kabyle, tableau aquarelle" → فن_وحرف
- "formation marketing digital, agence pub" → خدمات
- "متجر عام، livraison 58 ولاية, dropshipping" → متجر_إلكتروني
- "ألعاب أطفال، poussette, vêtements bébé" → منتجات_أطفال
"""


def _llm_classify(text: str) -> str:
    """Call Groq LLM to classify the seller's category."""
    try:
        from ai.utils.llm_client import call_llm
    except ImportError:
        logger.warning("llm_client not available, returning أخرى")
        return "أخرى"

    # Truncate to avoid burning tokens on huge texts
    snippet = text[:800].strip()

    prompt = f"""You are classifying Algerian online sellers. Content may be in Arabic (Darija or MSA), French, or mixed.
Given the seller's name and content below, output ONLY one category from this list:

{chr(10).join(CATEGORIES)}

Category descriptions:
{_CAT_DESCRIPTIONS}

{_FEW_SHOT_EXAMPLES}

Rules:
- Output ONLY the exact category name, nothing else
- No explanation, no punctuation, no extra words
- If genuinely mixed/unclear, prefer متجر_إلكتروني over أخرى
- أخرى is a last resort only

Seller content:
\"\"\"{snippet}\"\"\"

Category:"""

    try:
        result = call_llm(prompt).strip()
        # Strip any accidental punctuation / extra words
        result = result.split("\n")[0].strip()
        # Validate against known categories
        for cat in CATEGORIES:
            if cat in result or result in cat:
                return cat
        logger.warning("LLM returned unexpected category: %r — defaulting to أخرى", result)
        return "أخرى"
    except Exception as exc:
        logger.error("LLM category classification failed: %s", exc)
        return "أخرى"


# ── Public API ─────────────────────────────────────────────────────────────────

def classify_seller_category(text: str) -> str:
    """
    Classify a seller into one Arabic category.

    Strategy:
      1. Keyword match (fast, deterministic, weighted) — used when confident
      2. LLM fallback (Groq) — used for ambiguous/mixed-language content
      3. 'أخرى' if everything fails

    Args:
        text: seller name + bio + recent post captions (any language mix)

    Returns:
        One category string from CATEGORIES list.
    """
    if not text or not text.strip():
        return "أخرى"

    # Tier 1: weighted keyword match
    kw_result = _keyword_classify(text)
    if kw_result:
        logger.debug("Keyword classified as: %s", kw_result)
        return kw_result

    # Tier 2: LLM
    logger.debug("Escalating to LLM for classification")
    return _llm_classify(text)