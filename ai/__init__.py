# ai/__init__.py
from ai.text_analyzer.llm_analyzer import analyze_text
from ai.ocr.screenshot_extractor import extract_text_from_screenshot, analyze_screenshots
from ai.image_analyzer.fake_detector import check_image_authenticity
from ai.scoring.trust_score import calculate_trust_score
from ai.credibility.report_credibility import assess_report_credibility
from ai.feedback.summarizer import summarize_feedbacks
from ai.sentiment.comment_sentiment import analyze_sentiment

# FIX 1: was importing from ai.scoring.seller_verdict — file is ai/scoring/verdict.py
from ai.scoring.seller_verdict import generate_seller_verdict

# ── Phase 2: Risk & Category ──────────────────────────────────────────────────
from ai.scoring.risk_classifier import classify_seller_risk
# FIX 2: was importing from ai.scoring.category_classifier — file is ai/category/classifier.py
from ai.scoring.category_classifier import classify_seller_category

__all__ = [
    "analyze_text",
    "extract_text_from_screenshot",
    "analyze_screenshots",
    "check_image_authenticity",
    "calculate_trust_score",
    "assess_report_credibility",
    "summarize_feedbacks",
    "analyze_sentiment",
    # FIX 3: generate_seller_verdict was imported but missing from __all__
    "generate_seller_verdict",
    "classify_seller_risk",
    "classify_seller_category",
]