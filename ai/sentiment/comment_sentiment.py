# ai/sentiment/comment_sentiment.py
# ---------------------------------------------------------------------------
# Analyses scraped post comments for sentiment.
# Designed for Algerian content: Arabic, Darija, French, code-switching.
#
# Pipeline:
#   1. Input: ScrapeResult — profile_url, post_url, raw comments (list[Comment])
#   2. Pre-filter: price inquiries, greetings, and other non-sentiment noise
#      are tagged "inquiry" / "irrelevant" BEFORE reaching the ML classifier.
#      Key fix: bare Darija price words like "شحال", "بكم", "قداش" are caught
#      here so they can never be mislabelled as negative by the ML model.
#   3. Classification:
#      - If fine-tuned weights exist at models/marbert_final/, MARBERT
#        (UBC-NLP/MARBERTv2) is loaded with those weights.
#      - Fallback: CAMeL-Lab/bert-base-arabic-camelbert-da-sentiment
#   4. Aggregates counts → percentages.
#   5. Groq LLaMA (call_llm) — writes the final Darija summary paragraph
#      and picks the top representative comments.
# ---------------------------------------------------------------------------

from __future__ import annotations

import json
import logging
import re
import os
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    pipeline,
)
import torch
from ai.utils.llm_client import call_llm


logger = logging.getLogger(__name__)


# ── Input / Output schema ────────────────────────────────────────────────────

@dataclass
class Comment:
    """A single scraped comment."""
    text: str
    author: Optional[str] = None
    timestamp: Optional[str] = None
    likes: int = 0
    is_reply: bool = False


@dataclass
class ScrapeResult:
    profile_url: str
    post_url: str
    comments: list[Comment]
    platform: str = "unknown"
    post_text: Optional[str] = None
    post_id: Optional[str] = None


@dataclass
class SentimentResult:
    """Full output of analyze_sentiment()."""
    profile_url: str
    post_url: str
    platform: str

    positive_pct: float
    negative_pct: float
    neutral_pct: float
    irrelevant_pct: float   # includes price inquiries + true irrelevant

    total_comments: int
    total_analyzed: int     # comments that reached the ML classifier

    summary: str
    top_positive: list[str]
    top_negative: list[str]

    labeled: list[dict] = field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

_FINETUNED_WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "../../models/marbert_final"
)

_MARBERT_MODEL  = "UBC-NLP/MARBERTv2"
_FALLBACK_MODEL = "CAMeL-Lab/bert-base-arabic-camelbert-da-sentiment"

_MIN_MEANINGFUL_CHARS = 4
_MAX_COMMENT_CHARS    = 400
_CONFIDENCE_THRESHOLD = 0.55   # raised from 0.50 — short Darija needs higher confidence
_BATCH_SIZE           = 32

_LLM_MAX_RETRIES = 3
_LLM_RETRY_DELAY = 2.0


# ── Label maps ────────────────────────────────────────────────────────────────

_LABEL_MAP_MARBERT: dict[str, str] = {
    "LABEL_0": "negative",
    "LABEL_1": "positive",
}

_CAMEL_LABEL_MAP: dict[str, str] = {
    "positive": "positive",
    "negative": "negative",
    "neutral":  "neutral",
    "POSITIVE": "positive",
    "NEGATIVE": "negative",
    "NEUTRAL":  "neutral",
    "POS":      "positive",
    "NEG":      "negative",
    "NEU":      "neutral",
}


# ── Model loading (lazy, thread-safe) ─────────────────────────────────────────

_classifier = None
_lock       = threading.Lock()


def _get_classifier():
    global _classifier
    if _classifier is not None:
        return _classifier
    with _lock:
        if _classifier is not None:
            return _classifier
        device = 0 if torch.cuda.is_available() else -1
        if os.path.isdir(_FINETUNED_WEIGHTS_PATH):
            logger.info("Loading fine-tuned MARBERT weights from %s", _FINETUNED_WEIGHTS_PATH)
            tokenizer = AutoTokenizer.from_pretrained(_FINETUNED_WEIGHTS_PATH)
            model     = AutoModelForSequenceClassification.from_pretrained(_FINETUNED_WEIGHTS_PATH)
            model.eval()
            _classifier = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=device,
                truncation=True,
                max_length=128,
            )
        else:
            logger.info("Fine-tuned weights not found. Loading CAMeL fallback: %s", _FALLBACK_MODEL)
            _classifier = pipeline(
                "text-classification",
                model=_FALLBACK_MODEL,
                device=device,
                truncation=True,
                max_length=128,
            )
    return _classifier


def _is_finetuned() -> bool:
    return os.path.isdir(_FINETUNED_WEIGHTS_PATH)


# ── Emoji sentiment maps ──────────────────────────────────────────────────────

_EMOJI_SCORES: dict[str, int] = {
    # ── Strong positive ───────────────────────────────────────────────────────
    "❤️": 2, "❤": 2, "🧡": 2, "💛": 2, "💚": 2, "💙": 2, "💜": 2,
    "🖤": 1, "🤍": 1, "💕": 2, "💞": 2, "💓": 2, "💗": 2, "💖": 2,
    "💝": 2, "💘": 2, "😍": 3, "🥰": 3, "😻": 2, "🤩": 3,
    "😊": 2, "😄": 2, "😁": 2, "😀": 2, "🙂": 1, "😇": 2,
    "👍": 2, "👌": 2, "🤙": 1, "🙌": 2, "👏": 2, "🫶": 2,
    "✅": 1, "💯": 2, "🔥": 2, "⭐": 2, "🌟": 2, "✨": 2,
    "💪": 1, "🎉": 2, "🎊": 2, "🏆": 2, "👑": 2,
    "😘": 2, "🥳": 2, "😂": 1,
    "🤣": 1, "😆": 1,
    # ── Mild positive / hype ──────────────────────────────────────────────────
    "😮": 1, "😯": 1, "🤯": 1, "👀": 0,
    "💅": 1, "😎": 1, "🫡": 1,
    # ── Negative ─────────────────────────────────────────────────────────────
    "😡": -3, "🤬": -3, "😠": -2, "👎": -3,
    "😒": -2, "🙄": -2, "😤": -2, "😑": -1,
    "💔": -2, "😢": -2, "😭": -2,
    "🤮": -3, "🤢": -2, "😖": -2, "😣": -2,
    "🚫": -2, "❌": -2, "⛔": -2, "🛑": -2,
    "😴": -1,
    # ── Neutral / ambiguous ───────────────────────────────────────────────────
    "🤔": 0, "😐": 0, "😶": 0, "🤷": 0, "❓": 0, "❔": 0,
    "👋": 0, "✋": 0, "🙏": 1,
}

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U0001FA00-\U0001FA9F"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def _score_emojis(text: str) -> tuple[int, int]:
    score = 0
    count = 0
    for char in text:
        cp = ord(char)
        if cp > 0x2600:
            val = _EMOJI_SCORES.get(char) or _EMOJI_SCORES.get(char + "\uFE0F") or 0
            if val != 0:
                score += val
                count += 1
            elif _EMOJI_RE.match(char):
                count += 1
    return score, count


def _emoji_only_label(text: str) -> str | None:
    has_arabic = bool(re.search(r'[\u0600-\u06FF]', text))
    has_latin  = bool(re.search(r'[a-zA-Z]', text))
    if has_arabic or has_latin:
        return None

    score, count = _score_emojis(text)
    if count == 0:
        return None

    if score >= 2:
        return "positive"
    if score <= -2:
        return "negative"
    return "neutral"


def _emoji_boost(text: str) -> int:
    score, _ = _score_emojis(text)
    return score


# ── Pre-classification filters ────────────────────────────────────────────────
#
# These patterns are intercepted BEFORE the ML model sees them.
#
# Critical fix: bare Darija price words ("شحال", "بكم", "قداش", etc.) MUST
# be caught here. The ML models see these short isolated words as negative
# because they appear in complaint-heavy training data. They are always
# neutral inquiries and must never affect the seller's negative percentage.
#
# Strategy:
#   - "inquiry"    → excluded from sentiment % (shown to LLM for context)
#   - "irrelevant" → discarded entirely
#   - None         → send to ML classifier

# ── Exact-match Darija inquiry words ──────────────────────────────────────────
# These words ON THEIR OWN are ALWAYS inquiries.
# Matched before regex to avoid false positives inside longer sentences.
_EXACT_INQUIRY_WORDS: frozenset[str] = frozenset({
    # Price inquiry words
    "شحال", "شحاله", "شحالها",
    "قداش", "قداشه", "قداشها",
    "بكم", "بكمه", "بكمها",
    "بقداش",
    "الثمن", "ثمنو", "ثمنها", "ثمنه",
    "السعر", "سعرو", "سعرها", "سعره",
    # French price words
    "combien", "prix", "tarif",
    # Common greeting-only comments (no sentiment)
    "واش", "اهلا", "سلام", "هههه", "ههههه", "hhhh", "hhh",
})

# ── Regex for price/availability phrases ──────────────────────────────────────
_PRICE_INQUIRY_RE = re.compile(
    r"""
    (?:
        # Darija price questions — bare words OR in a phrase
        ب?شحال | شحال\s*(?:ثمن|يدير|يكلف|ديرو|دارت|دار|هاد|يبيع|هي|هو)? |
        ب?قداش | قداش\s*(?:ثمن|يدير|يكلف)? |
        ب?كم   | كم\s*(?:ثمنو|يكلف|يدير|سعرو)? |
        بقداش  |
        # Explicit price noun phrases
        ثمن(?:و|ها|ه)?\s*(?:شحال|قداش|كم|واش|ديرو)? |
        سعر(?:و|ها|ه)?\s*(?:شحال|قداش|كم|واش)? |
        # French price questions
        \bc(?:'|')est\s+combien\b | \bcombien\b | \bprix\b |
        \btarif\b | \bla\s+valeur\b |
        # Arabic price questions
        بكم\b | كم\s*(?:سعره|ثمنه|يساوي|تكلف) | (?:ما\s+)?السعر\b |
        # Availability/delivery/contact questions — neutral, never complaints
        واش\s+(?:كاين|عندكم|تبعتو|تصيب|فيه|تبيعو) |
        فين\s+(?:تشري|نلقاه|تلقاه|نصيبو|تباع) |
        كيفاش\s+(?:نطلب|نشري|الطلب|يتعامل) |
        رقم\s+(?:الهاتف|التواصل|واتساب|هاتف) |
        (?:livraison|commande|disponible?|stock|wach|wach\s+kayen)\b |
        # Short greeting-only patterns
        ^(?:اهلا|سلام|مرحبا|bonjour|salam)\s*$
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Pure sentiment words — meaningful even when short
_DARIJA_POSITIVE_WORDS: frozenset[str] = frozenset({
    "مزيان", "زوين", "بركاتك", "شكرا", "ممتاز", "باهي", "مليح",
    "برك", "واو", "تبارك", "ماشاء", "mashallah", "bravo",
    "نعم", "صح", "أحسن", "لابأس",
})
_DARIJA_NEGATIVE_WORDS: frozenset[str] = frozenset({
    "نصاب", "كذاب", "خايب", "سارق", "غاشوش",
    "مادفعتش", "ماوصلش", "arnaque", "escroquerie",
})

# Words that are ALWAYS inquiries regardless of surrounding context
_ALWAYS_INQUIRY_RE = re.compile(
    r'^\s*(?:شحال|قداش|بكم|بقداش|ب?شحال|ب?قداش|ب?كم)\s*[؟?!]*\s*$',
    re.UNICODE,
)


def _classify_pre_filter(text: str) -> str | None:
    """
    Returns a pre-classification label or None (→ send to ML).

    Order:
      1. Pure emoji → emoji-scored label
      2. Too short / bare URL → irrelevant
      3. Bare price/inquiry word (exact match, with/without ب prefix) → inquiry
      4. Sentiment allow-list → ML
      5. Price/inquiry phrase regex → inquiry
      6. Everything else → ML

    Returns: "positive" | "negative" | "neutral" | "inquiry" | "irrelevant" | None
    """
    stripped = text.strip()

    # ── 1. Pure emoji ─────────────────────────────────────────────────────────
    emoji_label = _emoji_only_label(stripped)
    if emoji_label is not None:
        return emoji_label

    # ── 2. Structural irrelevance ─────────────────────────────────────────────
    if len(stripped) < _MIN_MEANINGFUL_CHARS:
        return "irrelevant"
    if re.fullmatch(r'https?://\S+', stripped):
        return "irrelevant"

    has_arabic = bool(re.search(r'[\u0600-\u06FF]', stripped))
    has_latin  = bool(re.search(r'[a-zA-Z]', stripped))
    if not has_arabic and not has_latin:
        return "irrelevant"

    lower         = stripped.lower()
    stripped_norm = stripped.strip("؟?! \t\n\r")

    # ── 3a. Bare price word — always an inquiry ───────────────────────────────
    # Strip leading ب (price prefix: "بشحال" = "for how much")
    core = stripped_norm.lstrip("ب").strip()
    if core in _EXACT_INQUIRY_WORDS or stripped_norm in _EXACT_INQUIRY_WORDS:
        return "inquiry"

    # ── 3b. Regex: comment is ENTIRELY a price/inquiry expression ─────────────
    if _ALWAYS_INQUIRY_RE.match(stripped):
        return "inquiry"

    lower_stripped = lower.strip("؟?! \t\n\r")
    if lower_stripped in _EXACT_INQUIRY_WORDS:
        return "inquiry"

    # ── 4. Short Darija sentiment allow-list ──────────────────────────────────
    if lower_stripped in _DARIJA_POSITIVE_WORDS or lower_stripped in _DARIJA_NEGATIVE_WORDS:
        return None   # meaningful — send to ML

    # ── 5. Price / availability phrase (longer phrases with context) ──────────
    if _PRICE_INQUIRY_RE.search(stripped):
        return "inquiry"

    return None   # → ML classifier


def _guard_length(text: str) -> str:
    return text[:_MAX_COMMENT_CHARS] if len(text) > _MAX_COMMENT_CHARS else text


# ── ML inference ──────────────────────────────────────────────────────────────

def _classify_batch(texts: list[str]) -> list[str]:
    """Returns labels parallel to texts: positive | negative | neutral"""
    if not texts:
        return []

    clf   = _get_classifier()
    texts = [_guard_length(t) for t in texts]

    try:
        results = clf(texts, batch_size=_BATCH_SIZE, truncation=True)
        if _is_finetuned():
            return [
                _LABEL_MAP_MARBERT.get(r["label"], "neutral")
                if r["score"] >= _CONFIDENCE_THRESHOLD else "neutral"
                for r in results
            ]
        else:
            return [
                _CAMEL_LABEL_MAP.get(r["label"], "neutral")
                if r["score"] >= _CONFIDENCE_THRESHOLD else "neutral"
                for r in results
            ]
    except Exception as exc:
        logger.error("Classification batch failed: %s — defaulting to neutral.", exc)
        return ["neutral"] * len(texts)


# ── LLM summary ───────────────────────────────────────────────────────────────

def _build_summary_prompt(
    scrape: ScrapeResult,
    label_pairs: list[tuple[Comment, str]],
    counts: Counter,
    inquiry_count: int,
    total: int,
    pos_pct: float,
    neg_pct: float,
) -> str:
    pos_examples = sorted(
        [c for c, l in label_pairs if l == "positive"],
        key=lambda c: c.likes, reverse=True
    )[:5]
    neg_examples = sorted(
        [c for c, l in label_pairs if l == "negative"],
        key=lambda c: c.likes, reverse=True
    )[:5]
    inq_examples = sorted(
        [c for c, l in label_pairs if l == "inquiry"],
        key=lambda c: c.likes, reverse=True
    )[:5]

    pos_list = "\n".join(f"- {c.text}" for c in pos_examples) or "لا يوجد"
    neg_list = "\n".join(f"- {c.text}" for c in neg_examples) or "لا يوجد"
    inq_list = "\n".join(f"- {c.text}" for c in inq_examples) or "لا يوجد"

    return f"""أنت محلل مصداقية لمنصة "ثقة" الجزائرية.

المنصة: {scrape.platform}
رابط الصفحة: {scrape.profile_url}

تم تحليل {total} تعليق (بعضها تعليقات إيموجي فقط تم تصنيفها تلقائياً):
- إيجابي : {counts['positive']} تعليق ({pos_pct}%)
- سلبي   : {counts['negative']} تعليق ({neg_pct}%)
- محايد  : {counts['neutral']} تعليق
- استفسارات أسعار/توصيل: {inquiry_count} تعليق

تعليقات إيجابية:
{pos_list}

تعليقات سلبية:
{neg_list}

استفسارات (أسئلة عن الأسعار والتوصيل — ليست شكاوي):
{inq_list}


مهمتك:
1. اكتب ملخصاً بالدارجة الجزائرية (2-3 جمل) يوضح المشاعر الحقيقية للمشترين.
   - فرّق بين الاستفسارات (أسئلة عادية) والشكاوي الحقيقية.
   - التعليقات الإيموجي الإيجابية (❤️ 🔥 😍) تعني رضا حقيقي، خذها بعين الاعتبار.
   - إذا كانت الشكاوي قليلة، لا تبالغ في السلبية.
2. اختر أفضل 3 تعليقات إيجابية من القائمة الإيجابية أعلاه.
3. اختر 3 تعليقات سلبية من القائمة السلبية أعلاه — يجب أن تكون شكاوي حقيقية
   (مثل: ما وصلتش السلعة، منتوج رديء، نصب، تأخر، خدمة سيئة).
   لا تختار تعليقات تعبر عن دهشة أو فرحة أو أسئلة أو مدح حتى لو صنّفها النظام سلبياً.
   إذا ما كاينش 3 شكاوي حقيقية، رجع قائمة فارغة أو أقل من 3.

أعط JSON فقط بدون ```json أو أي نص إضافي:
{{
  "summary": "<ملخص بالدارجة>",
  "top_positive": ["<تعليق1>", "<تعليق2>", "<تعليق3>"],
  "top_negative": ["<تعليق1>", "<تعليق2>", "<تعليق3>"]
}}"""


def _parse_llm_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.warning("Could not parse LLM JSON response.")
    return {"summary": "ما قدرناش نلخصو التعليقات.", "top_positive": [], "top_negative": []}


def _call_llm_with_retry(prompt: str) -> dict:
    last_exc: Optional[Exception] = None
    for attempt in range(1, _LLM_MAX_RETRIES + 1):
        try:
            raw = call_llm(prompt)
            return _parse_llm_json(raw)
        except Exception as exc:
            last_exc = exc
            logger.warning("LLM call failed (attempt %d/%d): %s", attempt, _LLM_MAX_RETRIES, exc)
            if attempt < _LLM_MAX_RETRIES:
                time.sleep(_LLM_RETRY_DELAY)
    logger.error("LLM call failed after %d attempts: %s", _LLM_MAX_RETRIES, last_exc)
    return {"summary": "ما قدرناش نلخصو التعليقات.", "top_positive": [], "top_negative": []}


# ── Percentage calculation ────────────────────────────────────────────────────

def _compute_percentages(
    counts: Counter,
    n_inquiry: int,
    n_irrelevant: int,
    total: int,
) -> tuple[float, float, float, float]:
    if total == 0:
        return 0.0, 0.0, 0.0, 0.0

    n_non_sentiment = n_inquiry + n_irrelevant

    raw = {
        "positive":      counts.get("positive", 0),
        "negative":      counts.get("negative", 0),
        "neutral":       counts.get("neutral",  0),
        "non_sentiment": n_non_sentiment,
    }

    pcts  = {k: round(v / total * 100, 1) for k, v in raw.items()}
    drift = round(100.0 - sum(pcts.values()), 1)
    pcts["neutral"] = round(pcts["neutral"] + drift, 1)

    return pcts["positive"], pcts["negative"], pcts["neutral"], pcts["non_sentiment"]


# ── Public interface ──────────────────────────────────────────────────────────

def analyze_sentiment(scrape: ScrapeResult) -> SentimentResult:
    """
    Analyse scraped comments and return structured sentiment result.

    Key improvements:
    - Bare Darija price inquiries ("شحال", "بكم", "قداش") are pre-filtered
      via exact-match lookup BEFORE reaching the ML classifier.
    - _ALWAYS_INQUIRY_RE catches the same words with surrounding punctuation
      (e.g. "شحال؟", "بكم!").
    - Confidence threshold stays at 0.55 to reduce false negatives on short
      ambiguous phrases.
    """
    comments = [c for c in scrape.comments if c.text and c.text.strip()]
    total    = len(comments)

    _empty = SentimentResult(
        profile_url=scrape.profile_url,
        post_url=scrape.post_url,
        platform=scrape.platform,
        positive_pct=0.0, negative_pct=0.0, neutral_pct=0.0, irrelevant_pct=0.0,
        total_comments=total, total_analyzed=0,
        summary="ما كاينش تعليقات للتحليل.",
        top_positive=[], top_negative=[], labeled=[],
    )

    if not comments:
        return _empty

    # ── Step 1: pre-filter ────────────────────────────────────────────────────
    pre_labels: list[str | None] = [_classify_pre_filter(c.text) for c in comments]

    to_classify: list[tuple[int, Comment]] = []
    for i, (comment, pre) in enumerate(zip(comments, pre_labels)):
        if pre is None:
            to_classify.append((i, comment))

    logger.info(
        "Post %s — total=%d to_classify=%d pre-filtered=%d",
        scrape.post_url, total, len(to_classify),
        total - len(to_classify),
    )

    # ── Step 2: ML classification ─────────────────────────────────────────────
    ml_labels: dict[int, str] = {}
    if to_classify:
        texts  = [c.text for _, c in to_classify]
        labels = _classify_batch(texts)
        for (orig_idx, _), label in zip(to_classify, labels):
            ml_labels[orig_idx] = label

    # ── Step 3: merge labels ──────────────────────────────────────────────────
    label_pairs: list[tuple[Comment, str]] = []
    for i, (comment, pre) in enumerate(zip(comments, pre_labels)):
        final_label = pre if pre is not None else ml_labels.get(i, "neutral")
        label_pairs.append((comment, final_label))

    counts = Counter(
        l for _, l in label_pairs
        if l in ("positive", "negative", "neutral")
    )
    n_inquiry    = sum(1 for _, l in label_pairs if l == "inquiry")
    n_irrelevant = sum(1 for _, l in label_pairs if l == "irrelevant")
    n_classified = counts["positive"] + counts["negative"] + counts["neutral"]

    pos_pct, neg_pct, neu_pct, irr_pct = _compute_percentages(
        counts, n_inquiry, n_irrelevant, total
    )

    # ── Step 4: labeled list ──────────────────────────────────────────────────
    labeled: list[dict] = [
        {
            "text":      c.text,
            "author":    c.author,
            "timestamp": c.timestamp,
            "likes":     c.likes,
            "is_reply":  c.is_reply,
            "label":     label,
        }
        for c, label in label_pairs
    ]

    # ── Step 5: LLM summary ───────────────────────────────────────────────────
    prompt = _build_summary_prompt(
        scrape, label_pairs, counts, n_inquiry, total, pos_pct, neg_pct
    )
    llm = _call_llm_with_retry(prompt)

    return SentimentResult(
        profile_url=scrape.profile_url,
        post_url=scrape.post_url,
        platform=scrape.platform,
        positive_pct=pos_pct,
        negative_pct=neg_pct,
        neutral_pct=neu_pct,
        irrelevant_pct=irr_pct,
        total_comments=total,
        total_analyzed=n_classified,
        summary=llm.get("summary", ""),
        top_positive=llm.get("top_positive", [])[:3],
        top_negative=llm.get("top_negative", [])[:3],
        labeled=labeled,
    )