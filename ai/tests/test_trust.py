# Run with: pytest ai/tests/test_trust.py -v

from ai.scoring.trust_score import calculate_trust_score
from ai.scoring.risk_classifier import classify_seller_risk
from ai.category.classifier import classify_seller_category

# ── Known-answer tests: you know what the output SHOULD be ────────────────────

def test_obvious_scammer():
    """New account + multiple high-cred reports → should be red / low score"""
    result = calculate_trust_score({
        "account_age_days": 10,
        "post_count": 2,
        "platform": "facebook",
        "reports": [
            {"scam_type": "ghost_seller", "credibility_score": 0.9},
            {"scam_type": "advance_payment", "credibility_score": 0.85},
        ],
        "reviews": [],
    })
    assert result["score"] < 30,          f"Expected low score, got {result['score']}"
    assert result["verdict_color"] == "red", f"Expected red, got {result['verdict_color']}"
    assert result["verdict"] == "تجنب"

def test_trusted_seller():
    """Old account + many good reviews + no reports → should be green"""
    result = calculate_trust_score({
        "account_age_days": 900,
        "post_count": 200,
        "platform": "instagram",
        "has_phone_contact": 1,
        "has_website": 1,
        "reports": [],
        "reviews": [{"stars": 5}] * 20 + [{"stars": 4}] * 5,
    })
    assert result["score"] >= 80,           f"Expected high score, got {result['score']}"
    assert result["verdict_color"] == "green"
    assert result["verdict"] == "تعامل"

def test_suspicious_middle():
    """1 low-cred report + decent reviews → should be yellow/orange"""
    result = calculate_trust_score({
        "account_age_days": 180,
        "post_count": 30,
        "platform": "facebook",
        "reports": [{"scam_type": "wrong_item", "credibility_score": 0.4}],
        "reviews": [{"stars": 3}, {"stars": 4}, {"stars": 3}],
    })
    assert 30 <= result["score"] < 80, f"Expected middle score, got {result['score']}"

def test_empty_signals():
    """No data at all → should not crash, should return a valid result"""
    result = calculate_trust_score({})
    assert "score" in result
    assert "verdict" in result
    assert 0 <= result["score"] <= 100

def test_category_clothing():
    assert classify_seller_category("قندورة وفساتين جزائرية تقليدية") == "ملابس"

def test_category_food():
    assert classify_seller_category("حلويات وكسكس وطبخ بيتي") == "منتجات_غذائية"

def test_category_electronics():
    assert classify_seller_category("iphone samsung laptop gsm") == "إلكترونيات"

def test_risk_high():
    result = classify_seller_risk({
        "account_age_days": 5,
        "post_count": 1,
        "followers": 20,
        "report_count": 3,
        "avg_credibility_score": 0.85,
    })
    assert result["risk_class"] == 2
    assert result["risk_category"] == "high_risk"

def test_risk_legit():
    result = classify_seller_risk({
        "account_age_days": 730,
        "post_count": 150,
        "followers": 5000,
        "report_count": 0,
        "has_phone_contact": 1,
    })
    assert result["risk_class"] == 0
    assert result["risk_category"] == "legit"