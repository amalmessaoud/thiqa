# ai/tests/test_llm_quality.py
# Run with: pytest ai/tests/test_llm_quality.py -v -s
# (needs GROQ_API_KEY set)

from ai.category.classifier import classify_seller_category
from ai.scoring.verdict import generate_seller_verdict
from ai.feedback.summarizer import summarize_feedbacks

CATEGORY_CASES = [
    ("بيع عطور وكريمات ومكياج",                   "مستحضرات_تجميل"),
    ("أثاث وديكور للمنزل، طاولات وكنب",           "أثاث_وديكور"),
    ("handmade pottery and embroidery artisanat",  "فن_وحرف"),
    ("formation digital marketing agence",         "خدمات"),
    ("jouets et vêtements pour bébés enfants",     "منتجات_أطفال"),
]

def test_category_llm_fallback():
    """These are ambiguous enough to reach the LLM — check it still gets them right."""
    wrong = []
    for text, expected in CATEGORY_CASES:
        got = classify_seller_category(text)
        if got != expected:
            wrong.append(f"  '{text}' → got '{got}', expected '{expected}'")
    assert not wrong, "LLM category mismatches:\n" + "\n".join(wrong)

def test_verdict_structure():
    """Verdict must always return the right keys and a valid recommendation."""
    result = generate_seller_verdict({
        "display_name": "بائع تجريبي",
        "account_age_days": 60,
        "post_count": 10,
        "reports": [{"scam_type": "ghost_seller", "description": "دفعت ما وصلتش البضاعة", "credibility_score": 0.8}],
        "reviews": [],
        "avg_stars": None,
        "review_count": 0,
    })
    assert "verdict" in result
    assert "recommendation" in result
    assert result["recommendation"] in ("تعامل", "احذر", "تجنب"), \
        f"Unexpected recommendation: {result['recommendation']}"

def test_summarizer_positive():
    feedbacks = [
        "البائع مزيان، وصل الطلب في وقتو",
        "خدمة ممتازة، نرجعلو مرة أخرى",
        "المنتج كيما قال، راضي",
    ]
    result = summarize_feedbacks(feedbacks)
    assert result["total_count"] == 3
    assert result["sentiment_hint"] == "mostly_positive"
    assert len(result["summary"]) > 10

def test_summarizer_empty():
    result = summarize_feedbacks([])
    assert result["total_count"] == 0
    assert "summary" in result