"""
ai/scoring/train_trust.py

Training data comes from trust_training_data.csv (hand-designed profiles)
combined with any real sellers already in the DB.

Real DB samples are weighted 5x so they dominate as soon as you accumulate
reports and reviews. Until then the CSV provides the prior.

Usage:
    python -m ai.scoring.train_trust --force       # train + save
    python -m ai.scoring.train_trust --dry-run     # train only, no save
"""
from __future__ import annotations

import sys
import csv
import pickle
import logging
import argparse
from pathlib import Path

import numpy as np

_ROOT    = Path(__file__).resolve().parent.parent.parent
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_BACKEND))

from app.db.database import SessionLocal
from app.models.models import SellerProfile, Report, Review, Platform

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_HERE       = Path(__file__).parent
_MODELS_DIR = _HERE.parent / "models"
_MODEL_PATH = _MODELS_DIR / "trust_gb.pkl"

# CSV lives next to this script: ai/scoring/trust_training_data.csv
_CSV_PATH = _HERE / "trust_training_data.csv"

# Real DB samples are worth this many CSV rows each
_REAL_SAMPLE_WEIGHT = 5


# ── Engagement rate sanitizer (duplicated from trust_score to avoid circular import) ──

def _sanitize_engagement_rate(eng_rate: float, followers: float) -> float:
    """
    Clamp engagement rates that are physically implausible for the follower tier.

    Real-world norms:
      >100k followers  ->  ~1-3%   (ceiling 9% = 3x normal max)
      10k-100k         ->  ~2-5%   (ceiling 15%)
      <10k             ->  ~3-10%  (ceiling 30%)
    """
    if followers >= 100_000:
        ceiling = 0.09
    elif followers >= 10_000:
        ceiling = 0.15
    else:
        ceiling = 0.30
    return min(eng_rate, ceiling)


# ── Label assignment (for DB rows) ────────────────────────────────────────────

def _assign_label(reports: list, reviews: list, seller=None) -> int:
    """0 = legit | 1 = suspicious | 2 = high_risk"""
    if not reports:
        if reviews:
            avg = sum(r.stars for r in reviews) / len(reviews)
            if avg < 2.5:
                return 2
            return 0 if avg >= 3.5 else 1
        if seller:
            age   = seller.account_age_days or 90
            posts = seller.post_count or 0
            if age < 30 and posts < 3:
                return 1
        return 0

    cred_scores = [r.credibility_score or 0.5 for r in reports]
    max_cred    = max(cred_scores)
    avg_cred    = sum(cred_scores) / len(cred_scores)

    if max_cred >= 0.7 or (len(reports) >= 2 and avg_cred >= 0.6):
        return 2
    if max_cred >= 0.5 or len(reports) >= 1:
        return 1
    return 0


# ── Feature builder (mirrors trust_score._extract_features) ───────────────────

def _build_features(seller, reports, reviews, contacts) -> list[float]:
    age       = float(seller.account_age_days or 90)
    posts     = float(seller.post_count or 0)
    followers = float(getattr(seller, "followers", None) or 0)
    months    = max(age / 30.0, 1.0)
    ppm       = min(posts / months, 60.0)

    r_count  = float(len(reports))
    cred_s   = [r.credibility_score or 0.5 for r in reports]
    avg_cred = float(np.mean(cred_s)) if cred_s else 0.0
    weighted = r_count * avg_cred

    rv_count  = float(len(reviews))
    stars     = [r.stars for r in reviews]
    avg_stars = float(np.mean(stars)) if stars else 3.0
    pos_ratio = float(sum(1 for s in stars if s >= 4) / len(stars)) if stars else 0.5

    has_phone = int(any(c.contact_type.value == "phone"              for c in contacts))
    has_web   = int(any(c.contact_type.value in ("website", "other") for c in contacts))

    plat  = seller.platform.value if seller.platform else ""
    p_fb  = int(plat == Platform.facebook.value)
    p_ig  = int(plat == Platform.instagram.value)
    p_tt  = int(plat == "tiktok")

    raw_eng  = float(getattr(seller, "engagement_rate", None) or 0)
    eng_rate = _sanitize_engagement_rate(raw_eng, followers)

    sentiment = 0.5
    angry     = 0.0

    return [
        age, posts, followers, ppm,
        r_count, avg_cred, weighted,
        rv_count, avg_stars, pos_ratio,
        has_phone, has_web,
        p_fb, p_ig, p_tt,
        eng_rate, sentiment, angry,
    ]


# ── Load CSV training data ────────────────────────────────────────────────────

def _load_csv(path: Path) -> tuple[list, list]:
    """
    Load hand-designed training profiles from CSV.
    First column must be 'label' (0/1/2).
    Remaining columns must match FEATURE_NAMES order exactly.
    """
    if not path.exists():
        logger.warning("Training CSV not found at %s -- skipping CSV data.", path)
        return [], []

    X, y = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                label = int(row["label"])
                feats = [
                    float(row["account_age_days"]),
                    float(row["post_count"]),
                    float(row["followers"]),
                    float(row["posts_per_month"]),
                    float(row["report_count"]),
                    float(row["avg_credibility_score"]),
                    float(row["weighted_report_score"]),
                    float(row["review_count"]),
                    float(row["avg_stars"]),
                    float(row["positive_review_ratio"]),
                    float(row["has_phone_contact"]),
                    float(row["has_website"]),
                    float(row["platform_facebook"]),
                    float(row["platform_instagram"]),
                    float(row["platform_tiktok"]),
                    float(row["engagement_rate"]),
                    float(row["comment_sentiment_score"]),
                    float(row["angry_ratio"]),
                ]
                X.append(feats)
                y.append(label)
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed CSV row: %s", exc)

    counts = {i: y.count(i) for i in [0, 1, 2]}
    logger.info("CSV samples: %d  (labels: %s)", len(y), counts)
    return X, y


# ── Main training routine ─────────────────────────────────────────────────────

def train(force_save: bool = False, dry_run: bool = False):
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_validate, StratifiedKFold

    # ── 1. Real DB data ───────────────────────────────────────────────────────
    logger.info("Loading seller data from DB ...")
    db = SessionLocal()
    X_real, y_real = [], []

    try:
        from app.models.models import SellerContact
        sellers = db.query(SellerProfile).all()
        logger.info("Found %d sellers in DB", len(sellers))

        for seller in sellers:
            reports  = db.query(Report).filter(Report.seller_id  == seller.id).all()
            reviews  = db.query(Review).filter(Review.seller_id  == seller.id).all()
            contacts = db.query(SellerContact).filter(SellerContact.seller_id == seller.id).all()
            X_real.append(_build_features(seller, reports, reviews, contacts))
            y_real.append(_assign_label(reports, reviews, seller=seller))

    finally:
        db.close()

    real_label_counts = {i: y_real.count(i) for i in [0, 1, 2]}
    logger.info("Real DB samples: %d  (labels: %s)", len(y_real), real_label_counts)

    if len(set(y_real)) < 2:
        logger.warning(
            "All real samples are class %s. "
            "Scores will improve once reports/reviews appear in the DB.",
            list(set(y_real)),
        )

    # ── 2. CSV hand-designed data ─────────────────────────────────────────────
    X_csv, y_csv = _load_csv(_CSV_PATH)

    if not X_csv:
        logger.error(
            "No CSV data found and real DB has no class diversity. "
            "Place trust_training_data.csv in ai/scoring/ and retry."
        )
        return None

    # ── 3. Combine: real rows weighted 5x, CSV rows weighted 1x ──────────────
    X_all = np.array(X_real + X_csv, dtype=np.float32)
    y_all = np.array(y_real + y_csv, dtype=np.int32)
    w_all = np.array(
        [_REAL_SAMPLE_WEIGHT] * len(y_real) + [1] * len(y_csv),
        dtype=np.float32,
    )

    total_label_counts = {i: int((y_all == i).sum()) for i in [0, 1, 2]}
    logger.info("Total training samples: %d  (labels: %s)", len(y_all), total_label_counts)

    # ── 4. Model ──────────────────────────────────────────────────────────────
    # Deliberately conservative hyperparams: shallow trees, high min_samples_leaf,
    # feature subsampling -- all reduce overfitting on a small dataset.
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.08,
            subsample=0.80,
            min_samples_leaf=8,
            max_features=0.75,
            random_state=42,
        )),
    ])

    # ── 5. Cross-validation ───────────────────────────────────────────────────
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    try:
        cv_results = cross_validate(
            pipeline, X_all, y_all, cv=cv,
            scoring="f1_weighted",
            fit_params={"clf__sample_weight": w_all},
        )
        scores = cv_results["test_score"]
    except TypeError:
        logger.warning(
            "sklearn version does not support fit_params in cross_validate "
            "-- CV metric computed without sample weights (final fit still uses them)."
        )
        cv_results = cross_validate(pipeline, X_all, y_all, cv=cv, scoring="f1_weighted")
        scores = cv_results["test_score"]

    logger.info("CV F1-weighted: %.3f +/- %.3f", scores.mean(), scores.std())

    if scores.mean() > 0.97:
        logger.warning(
            "CV F1 = %.3f -- still suspiciously high. "
            "Add more boundary/ambiguous rows to trust_training_data.csv.",
            scores.mean(),
        )
    elif scores.mean() < 0.70:
        logger.warning(
            "CV F1 = %.3f -- model is struggling. "
            "Check for label noise or very imbalanced classes in the CSV.",
            scores.mean(),
        )
    else:
        logger.info("CV F1 looks healthy.")

    # ── 6. Final fit ──────────────────────────────────────────────────────────
    pipeline.fit(X_all, y_all, clf__sample_weight=w_all)

    feature_names = [
        "account_age_days", "post_count", "followers", "posts_per_month",
        "report_count", "avg_credibility_score", "weighted_report_score",
        "review_count", "avg_stars", "positive_review_ratio",
        "has_phone_contact", "has_website",
        "platform_facebook", "platform_instagram", "platform_tiktok",
        "engagement_rate", "comment_sentiment_score", "angry_ratio",
    ]
    importances = pipeline.named_steps["clf"].feature_importances_
    logger.info("Top feature importances:")
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1])[:10]:
        logger.info("  %-32s %.4f", name, imp)

    if dry_run:
        logger.info("Dry run -- model NOT saved.")
        return pipeline

    # ── 7. Save ───────────────────────────────────────────────────────────────
    real_classes = set(y_real)
    should_save  = force_save or len(real_classes) >= 2 or not _MODEL_PATH.exists()

    if not should_save:
        logger.warning(
            "Skipping save -- real data has only class %s and a prior model exists. "
            "Use --force to override.",
            real_classes,
        )
        return pipeline

    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)
    logger.info("Model saved to %s  (force=%s)", _MODEL_PATH, force_save)
    return pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",   action="store_true",
                        help="Save model even without real class diversity")
    parser.add_argument("--dry-run", action="store_true",
                        help="Train but do not save the model")
    args = parser.parse_args()
    train(force_save=args.force, dry_run=args.dry_run)