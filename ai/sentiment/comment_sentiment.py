# ai/sentiment/comment_sentiment.py
# ---------------------------------------------------------------------------
# Analyses scraped post comments for sentiment.
# Designed for Algerian content: Arabic, Darija, French, code-switching.
#
# Pipeline:
#   1. Input: ScrapeResult — profile_url, post_url, raw comments (list[Comment])
#   2. Classification:
#      - If fine-tuned weights exist at ai/models/arabert_sentiment/, AraBERT
#        (aubmindlab/bert-base-arabertv02) is loaded with those weights.
#      - Fallback: CAMeL-Lab/bert-base-arabic-camelbert-da-sentiment
#        (dialect-aware Arabic sentiment, handles Darija well)
#   3. Aggregates counts → percentages.
#   4. Groq LLaMA (call_llm) — writes the final Darija summary paragraph
#      and picks the top representative comments.
#
# Input  : ScrapeResult  (see dataclass below)
# Output : SentimentResult (see dataclass below)
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


# ── Logging ──────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


# ── Input / Output schema ────────────────────────────────────────────────────

@dataclass
class Comment:
    """A single scraped comment."""
    text: str
    author: Optional[str] = None          # username / display name
    timestamp: Optional[str] = None       # ISO-8601 or raw platform string
    likes: int = 0                        # reaction count (if available)
    is_reply: bool = False                # True if it's a reply to another comment


@dataclass
class ScrapeResult:
    """
    Output of the scraping step — one post's full context.

    Example
    -------
    result = ScrapeResult(
        profile_url="https://www.facebook.com/seller.page",
        post_url="https://www.facebook.com/seller.page/posts/123456",
        comments=[
            Comment(text="بضاعة ممتازة وسريع في التوصيل", author="user1", likes=12),
            Comment(text="نصاب ما وصلتليش الطلبية", author="user2"),
        ],
        platform="facebook",
        post_text="عرض خاص على الملابس الشتوية 🧥",
    )
    """
    profile_url: str
    post_url: str
    comments: list[Comment]
    platform: str = "unknown"           # facebook | instagram | tiktok | …
    post_text: Optional[str] = None     # caption / post body (optional context)
    post_id: Optional[str] = None       # platform post ID if scraped


@dataclass
class SentimentResult:
    """Full output of analyze_sentiment()."""
    profile_url: str
    post_url: str
    platform: str

    # Percentages (sum to 100)
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    irrelevant_pct: float

    total_comments: int      # raw count incl. irrelevant
    total_analyzed: int      # relevant comments that went through classifier

    # LLM outputs
    summary: str
    top_positive: list[str]
    top_negative: list[str]

    # Per-comment breakdown (for downstream use / debugging)
    labeled: list[dict] = field(default_factory=list)
    # [{"text": ..., "author": ..., "label": "positive"|"negative"|"neutral"|"irrelevant"}]


# ── Constants ─────────────────────────────────────────────────────────────────

_FINETUNED_WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "../../models/arabert_sentiment"
)

_ARABERT_MODEL  = "aubmindlab/bert-base-arabertv02"
_FALLBACK_MODEL = "CAMeL-Lab/bert-base-arabic-camelbert-da-sentiment"

# Minimum characters for a comment to be considered meaningful
_MIN_MEANINGFUL_CHARS = 5

# Comments longer than this will be truncated by the model — log a warning
_MAX_COMMENT_CHARS = 400

# Minimum confidence score to trust a label — below this → "neutral"
_CONFIDENCE_THRESHOLD = 0.60

# Batch size — CAMeL is a base model, safe to use larger batches
_BATCH_SIZE = 32

# LLM retry settings
_LLM_MAX_RETRIES = 3
_LLM_RETRY_DELAY = 2.0   # seconds between retries


# ── Label maps ────────────────────────────────────────────────────────────────

_LABEL_MAP_FINETUNED: dict[str, str] = {
    "LABEL_0": "negative",
    "LABEL_1": "neutral",
    "LABEL_2": "positive",
    "negative": "negative",
    "neutral":  "neutral",
    "positive": "positive",
    "NEGATIVE": "negative",
    "NEUTRAL":  "neutral",
    "POSITIVE": "positive",
}

# CAMeL model outputs: positive / negative / neutral (case-insensitive)
_CAMEL_LABEL_MAP: dict[str, str] = {
    "positive": "positive",
    "negative": "negative",
    "neutral":  "neutral",
    "POSITIVE": "positive",
    "NEGATIVE": "negative",
    "NEUTRAL":  "neutral",
    "POS": "positive",
    "NEG": "negative",
    "NEU": "neutral",
}


# ── Model loading (lazy, thread-safe, loaded once) ────────────────────────────

_classifier   = None
_preprocessor = None
_lock         = threading.Lock()


def _get_classifier():
    global _classifier, _preprocessor

    # Fast path — already loaded
    if _classifier is not None:
        return _classifier

    with _lock:
        # Double-checked locking — another thread may have loaded it while
        # we were waiting for the lock
        if _classifier is not None:
            return _classifier

        device = 0 if torch.cuda.is_available() else -1

        if os.path.isdir(_FINETUNED_WEIGHTS_PATH):
            # ── Fine-tuned AraBERT weights ────────────────────────────────────
            logger.info("Loading fine-tuned weights from %s", _FINETUNED_WEIGHTS_PATH)

            try:
                from arabert.preprocess import ArabertPreprocessor
                _preprocessor = ArabertPreprocessor(model_name=_ARABERT_MODEL)
                logger.info("AraBERT preprocessor initialised.")
            except ImportError:
                logger.warning("arabert package not installed — skipping preprocessing.")
                _preprocessor = None

            tokenizer = AutoTokenizer.from_pretrained(_FINETUNED_WEIGHTS_PATH)
            model     = AutoModelForSequenceClassification.from_pretrained(
                _FINETUNED_WEIGHTS_PATH
            )
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
            # ── CAMeL dialect sentiment fallback ──────────────────────────────
            logger.info(
                "Fine-tuned weights not found. Loading CAMeL dialect sentiment: %s",
                _FALLBACK_MODEL,
            )
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


# ── Comment pre-processing ────────────────────────────────────────────────────

def _is_irrelevant(text: str) -> bool:
    """
    True for:
      - very short texts (< _MIN_MEANINGFUL_CHARS non-whitespace chars)
      - strings that contain NO Arabic or Latin letters at all
        (pure emoji / punctuation / digit strings)

    Deliberately lenient: a comment with even one real word is kept.
    """
    stripped = text.strip()

    if len(stripped) < _MIN_MEANINGFUL_CHARS:
        return True

    has_arabic = bool(re.search(r'[\u0600-\u06FF]', stripped))
    has_latin  = bool(re.search(r'[a-zA-Z]', stripped))
    if has_arabic or has_latin:
        return False

    return True


def _preprocess_for_arabert(text: str) -> str:
    """
    Apply AraBERT normalisation ONLY when fine-tuned weights are loaded.
    Falls back to raw text on error.
    """
    if _preprocessor is None:
        return text
    try:
        return _preprocessor.preprocess(text)
    except Exception as exc:
        logger.debug("AraBERT preprocessor error on %r: %s", text[:40], exc)
        return text


def _guard_length(text: str) -> str:
    """Warn and return text as-is if it will be truncated by the model."""
    if len(text) > _MAX_COMMENT_CHARS:
        logger.debug(
            "Long comment (%d chars) will be truncated by model: %r…",
            len(text), text[:40],
        )
    return text


# ── Inference ─────────────────────────────────────────────────────────────────

def _classify_batch(texts: list[str]) -> list[str]:
    """
    Returns a list of labels ("positive" | "negative" | "neutral")
    parallel to `texts`.

    - Fine-tuned path : applies AraBERT preprocessing → text-classification.
    - Fallback path   : feeds raw text to CAMeL → text-classification.
    - Low-confidence predictions (score < _CONFIDENCE_THRESHOLD) → "neutral".
    """
    if not texts:
        return []

    clf = _get_classifier()

    # Warn on long comments before they hit the model
    texts = [_guard_length(t) for t in texts]

    try:
        if _is_finetuned():
            preprocessed = [_preprocess_for_arabert(t) for t in texts]
            results = clf(preprocessed, batch_size=_BATCH_SIZE, truncation=True)
            return [
                _LABEL_MAP_FINETUNED.get(r["label"], "neutral")
                if r["score"] >= _CONFIDENCE_THRESHOLD
                else "neutral"
                for r in results
            ]
        else:
            # CAMeL handles Arabic/Darija natively — no preprocessing needed
            results = clf(texts, batch_size=_BATCH_SIZE, truncation=True)
            return [
                _CAMEL_LABEL_MAP.get(r["label"], "neutral")
                if r["score"] >= _CONFIDENCE_THRESHOLD
                else "neutral"
                for r in results
            ]

    except Exception as exc:
        logger.error("Classification batch failed: %s. Defaulting to neutral.", exc)
        return ["neutral"] * len(texts)


# ── LLM summary ───────────────────────────────────────────────────────────────

def _build_summary_prompt(
    scrape: ScrapeResult,
    label_pairs: list[tuple[Comment, str]],
    counts: Counter,
    total: int,
    pos_pct: float,   # ✅ use the already-rounded safe percentages
    neg_pct: float,
) -> str:
    pos_examples = [c.text for c, l in label_pairs if l == "positive"][:5]
    neg_examples = [c.text for c, l in label_pairs if l == "negative"][:5]

    pos_list = "\n".join(f"- {t}" for t in pos_examples) or "لا يوجد"
    neg_list = "\n".join(f"- {t}" for t in neg_examples) or "لا يوجد"

    platform_line = (
        f"المنصة: {scrape.platform}\n"
        f"رابط الصفحة: {scrape.profile_url}\n"
        f"رابط المنشور: {scrape.post_url}\n"
    )
    post_context = (
        f"نص المنشور: {scrape.post_text}\n" if scrape.post_text else ""
    )

    return f"""أنت محلل مصداقية لمنصة "ثقة" الجزائرية.

{platform_line}{post_context}
تم تحليل {total} تعليق على منشور بائع بالأرقام التالية:
- إيجابي : {counts['positive']} تعليق ({pos_pct}%)
- سلبي   : {counts['negative']} تعليق ({neg_pct}%)
- محايد  : {counts['neutral']} تعليق

أمثلة التعليقات الإيجابية:
{pos_list}

أمثلة التعليقات السلبية:
{neg_list}

مهمتك:
1. اكتب ملخصاً بالدارجة الجزائرية (2-3 جمل) يوضح المشاعر العامة للمشترين.
2. اختر أفضل 3 تعليقات إيجابية و3 سلبية ممثلة من القائمة أعلاه فقط.

أعط JSON فقط بدون ```json أو أي نص إضافي:
{{
  "summary": "<ملخص بالدارجة>",
  "top_positive": ["<تعليق1>", "<تعليق2>", "<تعليق3>"],
  "top_negative": ["<تعليق1>", "<تعليق2>", "<تعليق3>"]
}}"""


def _parse_llm_json(raw: str) -> dict:
    """Robust JSON extraction from LLM output."""
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
    return {
        "summary": "ما قدرناش نلخصو التعليقات.",
        "top_positive": [],
        "top_negative": [],
    }


def _call_llm_with_retry(prompt: str) -> dict:
    """
    Calls call_llm() with up to _LLM_MAX_RETRIES attempts.
    Returns parsed JSON dict or a safe fallback on total failure.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(1, _LLM_MAX_RETRIES + 1):
        try:
            raw = call_llm(prompt)
            return _parse_llm_json(raw)
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "LLM call failed (attempt %d/%d): %s",
                attempt, _LLM_MAX_RETRIES, exc,
            )
            if attempt < _LLM_MAX_RETRIES:
                time.sleep(_LLM_RETRY_DELAY)

    logger.error("LLM call failed after %d attempts: %s", _LLM_MAX_RETRIES, last_exc)
    return {
        "summary": "ما قدرناش نلخصو التعليقات.",
        "top_positive": [],
        "top_negative": [],
    }


# ── Percentage helpers ────────────────────────────────────────────────────────

def _safe_percentages(
    counts: Counter, n_irrelevant: int, total: int
) -> tuple[float, float, float, float]:
    """
    Returns (positive_pct, negative_pct, neutral_pct, irrelevant_pct)
    guaranteed to sum to exactly 100.0.
    Distributes any rounding remainder into neutral_pct.
    """
    if total == 0:
        return 0.0, 0.0, 0.0, 0.0

    raw = {
        "positive":   counts.get("positive", 0),
        "negative":   counts.get("negative", 0),
        "neutral":    counts.get("neutral",  0),
        "irrelevant": n_irrelevant,
    }

    pcts = {k: round(v / total * 100, 1) for k, v in raw.items()}
    diff = round(100.0 - sum(pcts.values()), 1)
    pcts["neutral"] = round(pcts["neutral"] + diff, 1)

    return pcts["positive"], pcts["negative"], pcts["neutral"], pcts["irrelevant"]


# ── Public interface ──────────────────────────────────────────────────────────

def analyze_sentiment(scrape: ScrapeResult) -> SentimentResult:
    """
    Parameters
    ----------
    scrape : ScrapeResult
        Full scraping output: profile URL, post URL, and list of Comment objects.
        Accepts Arabic, Darija, French, or any mix.

    Returns
    -------
    SentimentResult
        Structured result with percentages, summary, top comments,
        per-comment labels, and the original profile / post URLs.

    Example
    -------
    from ai.sentiment.comment_sentiment import analyze_sentiment, ScrapeResult, Comment

    result = analyze_sentiment(ScrapeResult(
        profile_url="https://www.facebook.com/seller",
        post_url="https://www.facebook.com/seller/posts/99",
        platform="facebook",
        post_text="سولد 🔥 ملابس شتوية",
        comments=[
            Comment(text="توصلت بضاعة نيشان"),
            Comment(text="نصابين ما وصلتليش"),
            Comment(text="👍👍👍"),
        ],
    ))
    print(result.summary)
    """
    # ── Normalise input ───────────────────────────────────────────────────────
    comments = [c for c in scrape.comments if c.text and c.text.strip()]
    total = len(comments)

    # ✅ total_comments now reflects actual count, not hardcoded 0
    _empty = SentimentResult(
        profile_url=scrape.profile_url,
        post_url=scrape.post_url,
        platform=scrape.platform,
        positive_pct=0.0,
        negative_pct=0.0,
        neutral_pct=0.0,
        irrelevant_pct=0.0,
        total_comments=total,
        total_analyzed=0,
        summary="ما كاينش تعليقات للتحليل.",
        top_positive=[],
        top_negative=[],
        labeled=[],
    )

    if not comments:
        return _empty

    # ── Step 1: Split relevant vs irrelevant ──────────────────────────────────
    relevant   = [c for c in comments if not _is_irrelevant(c.text)]
    irrelevant = [c for c in comments if _is_irrelevant(c.text)]

    logger.info(
        "Post %s — total=%d relevant=%d irrelevant=%d",
        scrape.post_url, total, len(relevant), len(irrelevant),
    )

    # ── Step 2: Classification ────────────────────────────────────────────────
    label_pairs: list[tuple[Comment, str]] = []

    if relevant:
        texts  = [c.text for c in relevant]
        labels = _classify_batch(texts)
        label_pairs = list(zip(relevant, labels))

    counts = Counter(l for _, l in label_pairs)

    # ── Step 3: Compute percentages ───────────────────────────────────────────
    pos_pct, neg_pct, neu_pct, irr_pct = _safe_percentages(
        counts, len(irrelevant), total
    )

    # ── Step 4: Build labeled breakdown ──────────────────────────────────────
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
    ] + [
        {
            "text":      c.text,
            "author":    c.author,
            "timestamp": c.timestamp,
            "likes":     c.likes,
            "is_reply":  c.is_reply,
            "label":     "irrelevant",
        }
        for c in irrelevant
    ]

    # ── Step 5: Groq LLaMA summary (with retry) ───────────────────────────────
    # ✅ Pass already-computed safe percentages so prompt matches returned result
    prompt = _build_summary_prompt(
        scrape, label_pairs, counts, total, pos_pct, neg_pct
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
        total_analyzed=len(relevant),
        summary=llm.get("summary", ""),
        top_positive=llm.get("top_positive", [])[:3],
        top_negative=llm.get("top_negative", [])[:3],
        labeled=labeled,
    )