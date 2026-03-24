import json
import re
from typing import Any
from ai.utils.llm_client import call_llm
from .preprocessor import preprocess_text
from .prompts import build_analysis_prompt


def analyze_text(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        return _fallback()

    cleaned = preprocess_text(text)
    prompt = build_analysis_prompt(cleaned)
    raw = call_llm(prompt)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                result = _fallback()
        else:
            result = _fallback()

    return _validate(result)


def _validate(result: dict) -> dict:
    """Ensure all required keys exist with correct types. Fill missing ones."""
    valid_scam_types = {"ghost_seller", "advance_payment", "fake_product", "wrong_item", "no_response"}
    valid_labels = {"scam", "legit", "unknown"}

    return {
        "label": result.get("label") if result.get("label") in valid_labels else "unknown",
        "scam_type": result.get("scam_type") if result.get("scam_type") in valid_scam_types else None,
        "red_flags": result.get("red_flags") if isinstance(result.get("red_flags"), list) else [],
        "verdict_darija": result.get("verdict_darija") or "ما قدرناش نحللوا هاد الرسالة، كن حذر",
        "safe_to_proceed": bool(result.get("safe_to_proceed", True))
    }


def _fallback() -> dict:
    return {
        "label": "unknown",
        "scam_type": None,
        "red_flags": [],
        "verdict_darija": "ما قدرناش نحللوا هاد الرسالة، كن حذر",
        "safe_to_proceed": True
    }