"""
ai/scoring/trust_score.py

Design goals:
- GB model and rule-based scorer produce scores on the SAME 0-100 scale.
- Scores are BLENDED intelligently based on data availability.
- Rule-based acts as a transparent anchor, not a silent override.
- _score_to_verdict output is stable: (verdict, verdict_color, verdict_darija).

Verdict bands (v4):
  80-100  → green-dark   "موثوق جداً"
  65-79   → green        "موثوق بشكل عام"
  50-64   → yellow       "فيه بعض الشكوك"
  40-49   → orange       "علامات مقلقة"
  0-39    → red          "تجنب"
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_HERE       = Path(__file__).parent
_MODELS_DIR = _HERE.parent / "models"
_MODEL_PATH = _MODELS_DIR / "trust_gb.pkl"

# ── Feature names (must match train_trust.py exactly) ─────────────────────────
FEATURE_NAMES = [
    "account_age_days",
    "post_count",
    "followers",
    "posts_per_month",
    "report_count",
    "avg_credibility_score",
    "weighted_report_score",
    "review_count",
    "avg_stars",
    "positive_review_ratio",
    "has_phone_contact",
    "has_website",
    "platform_facebook",
    "platform_instagram",
    "platform_tiktok",
    "engagement_rate",
    "comment_sentiment_score",
    "angry_ratio",
]

# ── Verdict thresholds ────────────────────────────────────────────────────────
# Format: (min_score_inclusive, verdict, color, darija)
# Five distinct bands for precision:
#   80-100  trusted seller, top band
#   65-79   generally trusted
#   50-64   some doubts
#   40-49   concerning signals
#   0-39    avoid
_SCORE_TO_VERDICT = [
    (80, "موثوق",  "green",        "هذا البائع موثوق جداً ويمكن التعامل معه بثقة"),
    (65, "تعامل",  "green",        "هذا البائع موثوق بشكل عام"),
    (50, "احذر",   "yellow",       "هذا البائع فيه بعض الشكوك — تحقق قبل الشراء"),
    (40, "احذر",   "orange",       "هذا البائع فيه علامات مقلقة — توخ الحذر الشديد"),
    ( 0, "تجنب",   "red",          "تجنب هذا البائع، فيه علامات نصب"),
]


# ── Engagement rate sanitizer ─────────────────────────────────────────────────

def _sanitize_engagement_rate(eng_rate: float, followers: float) -> float:
    """
    Clamp engagement rates that are physically implausible for the follower tier.

    Updated real-world ceilings (fashion/lifestyle niches, Instagram/TikTok 2024):
      >500k followers  ->  ~1-4%    (ceiling 8%)
      100k-500k        ->  ~3-8%    (ceiling 15%)
      10k-100k         ->  ~4-10%   (ceiling 20%)
      <10k             ->  ~5-15%   (ceiling 35%)

    Note: TikTok naturally has higher engagement than Instagram/Facebook.
    The ceilings above are deliberately generous to accommodate TikTok norms.
    """
    if followers >= 500_000:
        ceiling = 0.08
    elif followers >= 100_000:
        ceiling = 0.15
    elif followers >= 10_000:
        ceiling = 0.20
    else:
        ceiling = 0.35
    return min(eng_rate, ceiling)


# ── Feature extraction ────────────────────────────────────────────────────────

def _extract_features(signals: dict) -> np.ndarray:
    # FIX: None age → 0.0 (unknown = no credit)
    raw_age = signals.get("account_age_days")
    age     = float(raw_age) if raw_age is not None else 0.0

    posts     = float(signals.get("post_count") or 0)
    followers = float(signals.get("followers") or 0)
    months    = max(age / 30.0, 1.0)
    ppm       = min(posts / months, 60.0)

    reports     = signals.get("reports", [])
    r_count     = float(len(reports))
    cred_scores = [r.get("credibility_score") or 0.5 for r in reports]
    avg_cred    = float(np.mean(cred_scores)) if cred_scores else 0.0
    weighted    = r_count * avg_cred

    reviews   = signals.get("reviews", [])
    rv_count  = float(len(reviews))
    stars     = [r.get("stars", 3) for r in reviews]
    avg_stars = float(np.mean(stars)) if stars else 3.0
    pos_ratio = float(sum(1 for s in stars if s >= 4) / len(stars)) if stars else 0.5

    has_phone = int(bool(signals.get("has_phone_contact", 0)))
    has_web   = int(bool(signals.get("has_website", 0)))

    platform = str(signals.get("platform", "")).lower()
    p_fb = int("facebook"  in platform)
    p_ig = int("instagram" in platform)
    p_tt = int("tiktok"    in platform)

    from ai.scoring.trust_score import _sanitize_engagement_rate
    raw_eng  = min(float(signals.get("engagement_rate", 0)), 1.0)
    eng_rate = _sanitize_engagement_rate(raw_eng, followers)

    comment_sentiment = float(signals.get("comment_sentiment_score", 0.5))
    angry_ratio       = min(float(signals.get("angry_ratio", 0)), 1.0)

    return np.array([[
        age, posts, followers, ppm,
        r_count, avg_cred, weighted,
        rv_count, avg_stars, pos_ratio,
        has_phone, has_web,
        p_fb, p_ig, p_tt,
        eng_rate, comment_sentiment, angry_ratio,
    ]], dtype=np.float32)


# ── Model loading (lazy, module-level singleton) ───────────────────────────────

_model: Optional[object]         = None
_model_loaded: bool              = False
_model_classes: Optional[list]   = None
_model_n_features: Optional[int] = None


def _load_model():
    global _model, _model_loaded, _model_classes, _model_n_features
    if _model_loaded:
        return _model

    _model_loaded = True

    if not _MODEL_PATH.exists():
        logger.warning(
            "Trust GB model not found at %s -- using rule-based fallback. "
            "Run: python -m ai.scoring.train_trust --force",
            _MODEL_PATH,
        )
        return None

    try:
        with open(_MODEL_PATH, "rb") as f:
            loaded = pickle.load(f)

        clf = loaded.named_steps.get("clf") if hasattr(loaded, "named_steps") else loaded
        _model_classes    = list(clf.classes_) if hasattr(clf, "classes_") else [0, 1, 2]
        _model_n_features = int(getattr(clf, "n_features_in_", len(FEATURE_NAMES)))
        _model = loaded

        logger.info(
            "Loaded trust GB model from %s  (classes=%s, n_features=%d)",
            _MODEL_PATH, _model_classes, _model_n_features,
        )
        return _model

    except Exception as exc:
        logger.error("Failed to load trust GB model: %s", exc)
        return None


# ── Rule-based scorer ─────────────────────────────────────────────────────────

def _rule_based_score(signals: dict) -> float:
    """
    Deterministic 0-100 scorer. Used as the blending anchor and standalone
    fallback when the GB model is unavailable.
    """
    score = 55.0

    age       = float(signals.get("account_age_days") or 90)
    posts     = float(signals.get("post_count") or 0)
    followers = float(signals.get("followers") or 0)
    raw_eng   = float(signals.get("engagement_rate") or 0)
    eng       = _sanitize_engagement_rate(raw_eng, followers)
    angry     = float(signals.get("angry_ratio") or 0)
    sentiment = float(signals.get("comment_sentiment_score") or 0.5)
    reports   = signals.get("reports", [])
    reviews   = signals.get("reviews", [])

    # ── Account age ───────────────────────────────────────────────────────────
    if   age >= 365 * 3: score += 15
    elif age >= 365 * 2: score += 12
    elif age >= 365:     score += 7
    elif age >= 180:     score += 3
    elif age >= 90:      score += 1
    elif age <  30:      score -= 15

    # ── Post count ────────────────────────────────────────────────────────────
    if   posts >= 500: score += 8
    elif posts >= 200: score += 6
    elif posts >= 100: score += 5
    elif posts >= 30:  score += 3
    elif posts <  5:   score -= 8

    # ── Followers — tiered with a top-tier premium ────────────────────────────
    if   followers >= 500_000: score += 14
    elif followers >= 100_000: score += 10
    elif followers >= 50_000:  score += 8
    elif followers >= 10_000:  score += 6
    elif followers >= 1_000:   score += 3
    elif 0 < followers < 100:  score -= 5

    # ── Contact info — only penalise when combined with other risk signals ────
    has_phone   = bool(signals.get("has_phone_contact"))
    has_web     = bool(signals.get("has_website"))
    no_contact  = not has_phone and not has_web
    is_new      = age < 90
    no_reviews  = len(reviews) == 0
    has_reports = len(reports) > 0

    if no_contact:
        if followers >= 10_000 and (has_reports or (is_new and no_reviews)):
            score -= 10
        elif followers >= 1_000 and has_reports:
            score -= 5

    if has_phone: score += 4
    if has_web:   score += 6

    # ── Engagement rate (tier-adjusted, already sanitized above) ──────────────
    if followers >= 100_000:
        if   eng > 0.06:  score += 8
        elif eng > 0.03:  score += 5
        elif eng > 0.01:  score += 2
        elif eng > 0.005: score += 0
        elif eng > 0:     score -= 3
        else:             score -= 6
    elif followers >= 10_000:
        if   eng > 0.08: score += 8
        elif eng > 0.04: score += 5
        elif eng > 0.01: score += 2
        elif eng > 0:    score -= 2
        else:            score -= 5
    else:
        if   eng > 0.10: score += 10
        elif eng > 0.05: score += 6
        elif eng > 0.01: score += 2
        elif eng > 0:    score -= 2
        else:            score -= 3

    # ── Shares signal (TikTok / Facebook) — high shares = viral = credible ───
    avg_shares = float(signals.get("avg_shares_per_post") or 0)
    if avg_shares > 500:  score += 6
    elif avg_shares > 100: score += 3
    elif avg_shares > 20:  score += 1

    # ── Angry reactions ───────────────────────────────────────────────────────
    if   angry > 0.15: score -= 15
    elif angry > 0.05: score -= 5

    # ── Comment sentiment (range: -8 ... +8) ──────────────────────────────────
    score += (sentiment - 0.5) * 16

    # ── Reports — each report subtracts 15 × credibility_score ───────────────
    for r in reports:
        cred   = float(r.get("credibility_score") or 0.5)
        score -= 15 * cred

    # ── Reviews — shift by (avg_stars - 3) × 6 ───────────────────────────────
    if reviews:
        avg    = sum(r.get("stars", 3) for r in reviews) / len(reviews)
        score += (avg - 3) * 6

    score = min(score, 88.0)
    return max(0.0, score)


# ── GB probability -> 0-100 score ────────────────────────────────────────────

def _proba_to_score(proba: np.ndarray, classes: list) -> float:
    """
    Convert class probabilities to a 0-100 trust score.

    Mapping:
      class 0 (legit)      -> 100
      class 1 (suspicious) ->  45
      class 2 (high_risk)  ->   5
    """
    idx     = {cls: i for i, cls in enumerate(classes)}
    p_legit = float(proba[idx[0]]) if 0 in idx else 0.0
    p_sus   = float(proba[idx[1]]) if 1 in idx else 0.0
    p_hr    = float(proba[idx[2]]) if 2 in idx else 0.0

    score = p_legit * 100.0 + p_sus * 45.0 + p_hr * 5.0
    return max(0.0, min(100.0, score))


# ── Intelligent blending ───────────────────────────────────────────────────────

def _blend_scores_PATCHED(gb_score: float, rule_score: float, signals: dict) -> tuple[float, str]:
    """
    Blend GB and rule-based scores with (GB + rule) / 2 as the hard ceiling.

    gb_weight is ALWAYS ≤ 0.50 — meaning the blend can never give GB more
    than equal say.

    Blend tiers (data richness aware):
      rich  → GB 50% / rule 50%   (≥5 reviews AND known age)
      some  → GB 40% / rule 60%   (≥5 reviews OR known age)
      thin  → GB 33% / rule 67%   (1-4 reviews, or only age known)
      bare  → GB 25% / rule 75%   (no reviews, unknown age)

    Post-blend caps (follower-tier aware):
      no reviews:
        unknown age + <10k  followers → max 72
        unknown age + 10-50k          → max 75
        unknown age + 50k+            → max 78
        known age   + <10k  followers → max 76
        known age   + 10k+            → max 82
      ≥5 reviews → uncapped
    """
    review_count = len(signals.get("reviews", []))
    has_reviews  = review_count >= 5
    thin_reviews = 0 < review_count < 5
    has_age      = signals.get("account_age_days") is not None
    followers    = float(signals.get("followers", 0))

    # ── Blend weight (hard ceiling: GB ≤ 0.50) ────────────────────────────────
    if has_reviews and has_age:
        gb_weight   = 0.50
        tier_label  = "rich"
    elif has_reviews or has_age:
        gb_weight   = 0.40
        tier_label  = "some"
    elif thin_reviews or has_age:
        gb_weight   = 0.33
        tier_label  = "thin"
    else:
        gb_weight   = 0.25
        tier_label  = "bare"

    blended = gb_score * gb_weight + rule_score * (1.0 - gb_weight)

    # ── Post-blend cap (second defence layer) ─────────────────────────────────
    if not has_reviews:
        if not has_age:
            if followers < 10_000:
                cap = 72
            elif followers < 50_000:
                cap = 75
            else:
                cap = 78
        else:
            cap = 76 if followers < 10_000 else 82
        blended = min(blended, float(cap))

    logger.info(
        "Blend tier=%s  gb_weight=%.2f  gb=%.1f  rule=%.1f  blended=%.1f",
        tier_label, gb_weight, gb_score, rule_score, blended,
    )

    return max(0.0, min(100.0, blended)), f"gradient_boosting_blended_{tier_label}"

_blend_scores = _blend_scores_PATCHED


# ── Verdict helper ────────────────────────────────────────────────────────────

def _score_to_verdict(score_int: int) -> tuple[str, str, str]:
    for threshold, verdict, color, darija in _SCORE_TO_VERDICT:
        if score_int >= threshold:
            return verdict, color, darija
    return "تجنب", "red", "تجنب هذا البائع، فيه علامات نصب"


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_trust_score(signals: dict) -> dict:
    """
    Calculate trust score for a seller.

    Returns dict with keys:
        score, verdict, verdict_color, verdict_darija,
        model_used, rule_based_score, feature_values,
        reports_contribution, reviews_contribution
    """
    model      = _load_model()
    feats      = _extract_features(signals)
    rule_score = _rule_based_score(signals)

    model_used  = "rule_based"
    trust_score = rule_score

    if model is not None:
        expected = _model_n_features or len(FEATURE_NAMES)
        actual   = feats.shape[1]

        if expected != actual:
            logger.warning(
                "Feature mismatch: model expects %d features, got %d. "
                "Falling back to rule-based. Retrain: python -m ai.scoring.train_trust --force",
                expected, actual,
            )
            model_used  = "rule_based_fallback"
            trust_score = rule_score
        else:
            try:
                proba    = model.predict_proba(feats)[0]
                gb_score = _proba_to_score(proba, _model_classes or [0, 1, 2])

                logger.info(
                    "GB score=%d  rule_score=%d  divergence=%d",
                    int(gb_score), int(rule_score), int(abs(gb_score - rule_score)),
                )

                trust_score, model_used = _blend_scores(gb_score, rule_score, signals)

            except Exception as exc:
                logger.warning("GB prediction failed (%s) -- using rule-based", exc)
                model_used  = "rule_based_fallback"
                trust_score = rule_score

    score_int = int(round(trust_score))
    verdict, verdict_color, verdict_darija = _score_to_verdict(score_int)

    # ── Summarise report and review contributions for API transparency ─────────
    reports = signals.get("reports", [])
    reviews = signals.get("reviews", [])

    if reports:
        avg_cred = sum(r.get("credibility_score") or 0.5 for r in reports) / len(reports)
        total_deduction = sum(15 * (r.get("credibility_score") or 0.5) for r in reports)
        reports_contribution = (
            f"{len(reports)} بلاغ — متوسط المصداقية {round(avg_cred, 2)} "
            f"(خصم تقريبي: -{round(total_deduction)} نقطة)"
        )
    else:
        reports_contribution = "لا توجد بلاغات"

    if reviews:
        avg_stars = sum(r.get("stars", 3) for r in reviews) / len(reviews)
        star_delta = round((avg_stars - 3) * 6, 1)
        sign = "+" if star_delta >= 0 else ""
        reviews_contribution = (
            f"{len(reviews)} تقييم — متوسط {round(avg_stars, 1)}/5 نجوم "
            f"({sign}{star_delta} نقطة)"
        )
    else:
        reviews_contribution = "لا توجد تقييمات بعد"

    return {
        "score":                  score_int,
        "verdict":                verdict,
        "verdict_color":          verdict_color,
        "verdict_darija":         verdict_darija,
        "model_used":             model_used,
        "rule_based_score":       int(round(rule_score)),
        "feature_values":         dict(zip(FEATURE_NAMES, feats[0].tolist())),
        "reports_contribution":   reports_contribution,
        "reviews_contribution":   reviews_contribution,
    }