"""
Seller risk classifier — rule-based scoring (no ML model required).
Uses account signals to deterministically assign risk categories.
"""

RISK_LABELS = {0: "legit", 1: "suspicious", 2: "high_risk"}


def classify_seller_risk(features: dict) -> dict:
    """
    Classify seller risk from account signals.

    Args:
        features: dict with any of:
            account_age_days, post_count, followers, report_count,
            avg_credibility_score, has_phone_contact, has_website,
            platform_facebook, platform_instagram, posts_per_month

    Returns:
        dict with risk_category (str), risk_probability (float), risk_class (int)
    """
    age      = float(features.get("account_age_days", 30))
    posts    = float(features.get("post_count", 5))
    followers = float(features.get("followers", 100))
    reports  = float(features.get("report_count", 0))
    cred     = float(features.get("avg_credibility_score", 0.5))
    has_phone = int(features.get("has_phone_contact", 0))
    has_web   = int(features.get("has_website", 0))

    risk_score = 0.0   # higher = riskier

    # Reports are the strongest signal
    if reports >= 3 and cred >= 0.7:
        risk_score += 60
    elif reports >= 2 and cred >= 0.6:
        risk_score += 40
    elif reports >= 1 and cred >= 0.5:
        risk_score += 20

    # Very new account
    if age < 30:
        risk_score += 25
    elif age < 90:
        risk_score += 10

    # Almost no content
    if posts < 3:
        risk_score += 15
    elif posts < 10:
        risk_score += 5

    # Tiny audience
    if followers < 50:
        risk_score += 10
    elif followers < 200:
        risk_score += 5

    # Trust signals reduce risk
    if has_phone:
        risk_score -= 8
    if has_web:
        risk_score -= 8

    risk_score = max(0.0, min(100.0, risk_score))

    if risk_score >= 60:
        risk_class = 2
    elif risk_score >= 25:
        risk_class = 1
    else:
        risk_class = 0

    # Convert score to a 0–1 probability-like confidence
    probability = round(risk_score / 100, 4) if risk_class > 0 else round(1 - risk_score / 100, 4)

    return {
        "risk_category":    RISK_LABELS[risk_class],
        "risk_probability": probability,
        "risk_class":       risk_class,
    }