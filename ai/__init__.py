# Public AI interface — backend imports ONLY from here
# All functions return stubs until replaced with real implementations

from ai.text_analyzer import analyze_text
from ai.ocr.screenshot_extractor import extract_text_from_screenshot
from ai.image_analyzer.fake_detector import check_image_authenticity
from ai.sentiment.comment_sentiment import analyze_comments_sentiment
from ai.scoring.trust_score import calculate_trust_score

__all__ = [
    "analyze_text",
    "extract_text_from_screenshot",
    "check_image_authenticity",
    "analyze_comments_sentiment",
    "calculate_trust_score",
]