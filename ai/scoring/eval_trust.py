"""
ai/scoring/eval_trust.py

Evaluate the trust model against hand-labeled sellers from your DB.
Run: python -m ai.scoring.eval_trust
"""

import sys
from pathlib import Path

_ROOT    = Path(__file__).resolve().parent.parent.parent
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_BACKEND))

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from app.db.database import SessionLocal
from app.models.models import SellerProfile, Report, Review, SellerContact
from ai.scoring.train_trust import _build_features, _assign_label

# ── Manual ground-truth overrides ─────────────────────────────────────────────
# Add seller profile_urls + their TRUE label here as you verify them manually.
# 0 = legit, 1 = suspicious, 2 = high_risk
GROUND_TRUTH: dict[str, int] = {
    # "https://facebook.com/seller_x": 2,
    # "https://instagram.com/seller_y": 0,
}

label_names = {0: "legit", 1: "suspicious", 2: "high_risk"}


def _build_signals(seller, reports, reviews, contacts) -> dict:
    """Build the signals dict used by calculate_trust_score."""
    return {
        "account_age_days":  seller.account_age_days,
        "post_count":        seller.post_count,
        "platform":          seller.platform.value,
        "has_phone_contact": int(any(c.contact_type.value == "phone"    for c in contacts)),
        "has_website":       int(any(c.contact_type.value == "website"  for c in contacts)),
        "reports": [
            {"scam_type": r.scam_type.value, "credibility_score": r.credibility_score}
            for r in reports
        ],
        "reviews": [{"stars": r.stars} for r in reviews],
    }


def evaluate():
    from ai.scoring.trust_score import calculate_trust_score

    db = SessionLocal()
    try:
        sellers = db.query(SellerProfile).all()
        y_auto, y_pred, names = [], [], []

        for seller in sellers:
            reports  = db.query(Report).filter(Report.seller_id  == seller.id).all()
            reviews  = db.query(Review).filter(Review.seller_id  == seller.id).all()
            contacts = db.query(SellerContact).filter(SellerContact.seller_id == seller.id).all()

            auto_label = _assign_label(reports, reviews)
            signals    = _build_signals(seller, reports, reviews, contacts)

            # ── FIX: call calculate_trust_score only once ──────────────────
            result = calculate_trust_score(signals)
            score  = result["score"]

            print(f"  {(seller.display_name or 'unnamed')[:30]:<32} score={score:>3}  model={result['model_used']}")

            pred_label = 0 if score >= 80 else (1 if score >= 30 else 2)

            y_auto.append(auto_label)
            y_pred.append(pred_label)
            names.append(seller.display_name or seller.profile_url)

        # Classification report
        print("\n-- Auto-label vs Model Predictions --")
        present_labels = sorted(set(y_auto) | set(y_pred))
        present_names  = [label_names[l] for l in present_labels]
        print(classification_report(
            y_auto, y_pred,
            labels=present_labels,
            target_names=present_names,
            zero_division=0,
        ))
        print("Confusion matrix (rows=true, cols=pred):")
        print(f"  classes: {present_names}")
        print(confusion_matrix(y_auto, y_pred, labels=present_labels))

        missing = [label_names[l] for l in [0, 1, 2] if l not in present_labels]
        if missing:
            print(f"\n  NOTE: Classes missing from real data: {', '.join(missing)}")
            print("  -> Add real scam sellers to GROUND_TRUTH to validate them.")

        # Manual ground truth
        if GROUND_TRUTH:
            url_to_seller    = {s.profile_url: s for s in sellers}
            y_true_m, y_pred_m = [], []

            for url, true_label in GROUND_TRUTH.items():
                seller = url_to_seller.get(url)
                if not seller:
                    print(f"  WARNING: {url} not found in DB")
                    continue
                reports  = db.query(Report).filter(Report.seller_id  == seller.id).all()
                reviews  = db.query(Review).filter(Review.seller_id  == seller.id).all()
                contacts = db.query(SellerContact).filter(SellerContact.seller_id == seller.id).all()
                signals  = _build_signals(seller, reports, reviews, contacts)
                result   = calculate_trust_score(signals)
                score    = result["score"]
                y_true_m.append(true_label)
                y_pred_m.append(0 if score >= 80 else (1 if score >= 30 else 2))

            print("\n-- Manual Ground Truth Evaluation --")
            present_m = sorted(set(y_true_m) | set(y_pred_m))
            names_m   = [label_names[l] for l in present_m]
            print(classification_report(
                y_true_m, y_pred_m,
                labels=present_m,
                target_names=names_m,
                zero_division=0,
            ))
        else:
            print("\n-- Manual Ground Truth --")
            print("  No entries in GROUND_TRUTH yet.")
            print("  Add known scam/legit seller URLs to get real accuracy numbers.")

        # Per-seller breakdown
        print("\n-- Per-seller scores (for manual review) --")
        print(f"{'Seller':<40} {'Pred class':<14} {'Auto-label'}")
        print("-" * 70)
        for name, pred, auto in sorted(zip(names, y_pred, y_auto), key=lambda x: -x[1]):
            print(f"{name[:38]:<40} {label_names[pred]:<14} {label_names[auto]}")

    finally:
        db.close()


if __name__ == "__main__":
    evaluate()