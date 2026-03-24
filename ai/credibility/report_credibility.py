import json
import re
from typing import Any

from ai.utils.llm_client import call_llm
from ai.ocr.screenshot_extractor import extract_text_from_screenshot
from ai.constants import ScamType
from ai.credibility.prompts import build_credibility_prompt

# If OCR fails, description alone gives a low-but-nonzero score
FALLBACK_SCORE_NO_SCREENSHOT = 0.3


def assess_report_credibility(
    scam_type: str,
    description: str | None,
    screenshot_path: str,
) -> dict[str, Any]:
    """
    Assess the credibility of a scam report.
    Backend calls this after saving the uploaded screenshot to a temp file.
    Backend is responsible for deleting the temp file after this returns.

    Args:
        scam_type: one of ScamType enum values
        description: reporter's free text description, can be None
        screenshot_path: temp file path to the proof screenshot

    Returns:
        {
            credibility_score: float (0.0–1.0),
            credibility_label: "high" | "medium" | "low",
            reason: str (Darija),
            screenshot_supports_claim: bool
        }

    STATUS: COMPLETE
    """
    # Normalize scam_type — fall back to OTHER if unrecognized
    if scam_type not in ScamType._value2member_map_:
        scam_type = ScamType.OTHER.value

    # Step 1 — OCR the screenshot
    ocr_result = extract_text_from_screenshot(screenshot_path)
    screenshot_text = ""
    ocr_succeeded = False

    if ocr_result["extraction_successful"] and ocr_result["extracted_text"].strip():
        screenshot_text = ocr_result["extracted_text"]
        ocr_succeeded = True

    # Step 2 — If OCR failed AND no description, return minimum credibility
    if not ocr_succeeded and not description:
        return {
            "credibility_score": FALLBACK_SCORE_NO_SCREENSHOT,
            "credibility_label": "low",
            "reason": "لقطة الشاشة ما بيّنتش نص ومفيش وصف — مصداقية منخفضة",
            "screenshot_supports_claim": False
        }

    # Step 3 — Build prompt and call LLM
    prompt = build_credibility_prompt(scam_type, description, screenshot_text)
    raw = call_llm(prompt)

    # Step 4 — Parse response
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                return _fallback(ocr_succeeded)
        else:
            return _fallback(ocr_succeeded)

    return _validate(result, ocr_succeeded)


def _validate(result: dict, ocr_succeeded: bool) -> dict:
    """Ensure all keys exist with correct types."""
    try:
        score = float(result.get("credibility_score", FALLBACK_SCORE_NO_SCREENSHOT))
        score = max(0.0, min(1.0, score))  # clamp to 0–1
    except (TypeError, ValueError):
        score = FALLBACK_SCORE_NO_SCREENSHOT

    if score >= 0.7:
        label = "high"
    elif score >= 0.4:
        label = "medium"
    else:
        label = "low"

    return {
        "credibility_score": round(score, 2),
        "credibility_label": label,
        "reason": result.get("reason") or "تعذر تقييم المصداقية",
        "screenshot_supports_claim": bool(result.get("screenshot_supports_claim", ocr_succeeded)),
    }


def _fallback(ocr_succeeded: bool) -> dict:
    score = FALLBACK_SCORE_NO_SCREENSHOT if not ocr_succeeded else 0.4
    return {
        "credibility_score": score,
        "credibility_label": "low" if score < 0.4 else "medium",
        "reason": "تعذر تحليل البلاغ، تم تعيين مصداقية منخفضة",
        "screenshot_supports_claim": ocr_succeeded,
    }