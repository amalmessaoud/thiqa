# ai/image_analyzer/fake_detector.py
# ---------------------------------------------------------------------------
# Detects whether a product/post image was AI-generated or is a real photo.
#
# Pipeline:
#   1. Sightengine API (primary) — purpose-built AI image detector,
#      100 free requests/day, no credit card required.
#      Get credentials at: https://sightengine.com/signup
#      Set env variables: SIGHTENGINE_USER, SIGHTENGINE_SECRET
#
#   2. Groq vision fallback — kicks in automatically if:
#      - Sightengine credentials are missing
#      - Daily limit is reached (402/429)
#      - Any other API error
#
# Fixes applied:
#   - safe_to_trust=False (not True) when both detectors fail
#   - Uncertainty zone: scores 0.35–0.65 flagged as uncertain
#   - Image size guard: rejects images smaller than 100×100px
#   - Arabic verdict reflects low confidence naturally
#   - PIL import used properly for size check
# ---------------------------------------------------------------------------

import json
import os
import re

import requests
from PIL import Image

from ai.utils.llm_client import call_llm, call_llm_vision


# ── Constants ─────────────────────────────────────────────────────────────────

SIGHTENGINE_USER     = os.getenv("SIGHTENGINE_USER", "")
SIGHTENGINE_SECRET   = os.getenv("SIGHTENGINE_SECRET", "")
SIGHTENGINE_ENDPOINT = "https://api.sightengine.com/1.0/check.json"

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tiff"}

# Uncertainty zone — scores in this range are flagged as ambiguous
_UNCERTAINTY_LOW  = 0.35
_UNCERTAINTY_HIGH = 0.65

# Minimum image dimensions for reliable analysis
_MIN_IMAGE_SIZE = 100   # pixels (width AND height)


# ── 1. Sightengine (primary) ──────────────────────────────────────────────────

def _call_sightengine(image_path: str) -> tuple[bool, float, bool]:
    """
    Calls Sightengine genai model.
    Returns (is_ai, confidence, is_uncertain).

    Raises:
        EnvironmentError   — credentials not set
        requests.HTTPError — API error (including 402 limit reached)
    """
    if not SIGHTENGINE_USER or not SIGHTENGINE_SECRET:
        raise EnvironmentError("SIGHTENGINE_USER or SIGHTENGINE_SECRET not set.")

    with open(image_path, "rb") as f:
        response = requests.post(
            SIGHTENGINE_ENDPOINT,
            files={"media": f},
            data={
                "models":     "genai",
                "api_user":   SIGHTENGINE_USER,
                "api_secret": SIGHTENGINE_SECRET,
            },
            timeout=30,
        )

    response.raise_for_status()
    data = response.json()

    # Sightengine returns: {"type": {"ai_generated": 0.93, ...}, ...}
    ai_score = float(data.get("type", {}).get("ai_generated", 0.0))

    # ── Uncertainty zone ──────────────────────────────────────────────────
    is_uncertain = _UNCERTAINTY_LOW <= ai_score <= _UNCERTAINTY_HIGH
    is_ai        = ai_score > _UNCERTAINTY_HIGH   # only confident positive
    conf         = ai_score if is_ai else (1.0 - ai_score)

    return is_ai, round(conf, 4), is_uncertain


# ── 2. Groq vision (fallback) ─────────────────────────────────────────────────

_VISION_PROMPT = """You are an expert forensic image analyst specializing in detecting AI-generated images.

Carefully examine this image for AI generation artifacts such as:
- Unnatural skin texture, hair, or eyes
- Distorted hands, fingers, or teeth
- Inconsistent lighting or shadows
- Overly smooth or plastic-looking surfaces
- Repetitive background patterns
- Watermarks from known AI tools (Midjourney, DALL-E, Firefly, etc.)
- Anatomical impossibilities
- Text or logos that are garbled or nonsensical

Return ONLY a JSON object, no markdown, no preamble:
{
  "is_ai": true or false,
  "ai_probability": <float 0.0 to 1.0>,
  "top_signals": ["<signal 1>", "<signal 2>"]
}"""


def _call_groq_vision(image_path: str) -> tuple[bool, float, bool, list[str]]:
    """
    Calls Groq vision as fallback.
    Returns (is_ai, confidence, is_uncertain, top_signals).
    """
    raw = call_llm_vision(_VISION_PROMPT, image_path)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match  = re.search(r'\{.*\}', raw, re.DOTALL)
        parsed = json.loads(match.group()) if match else {}

    prob     = float(parsed.get("ai_probability", 0.5))
    signals  = parsed.get("top_signals", [])

    # ── Uncertainty zone ──────────────────────────────────────────────────
    is_uncertain = _UNCERTAINTY_LOW <= prob <= _UNCERTAINTY_HIGH
    is_ai        = prob > _UNCERTAINTY_HIGH
    conf         = prob if is_ai else (1.0 - prob)

    return is_ai, round(conf, 4), is_uncertain, signals


# ── 3. Image validation ───────────────────────────────────────────────────────

def _validate_image(image_path: str) -> str | None:
    """
    Returns an error reason string if the image is invalid, else None.
    Checks:
      - File exists
      - Extension is supported
      - Dimensions are at least _MIN_IMAGE_SIZE × _MIN_IMAGE_SIZE
    """
    if not os.path.isfile(image_path):
        return f"Image not found: {image_path}"

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return f"Unsupported format: {ext}"

    try:
        with Image.open(image_path) as img:
            w, h = img.size
            if w < _MIN_IMAGE_SIZE or h < _MIN_IMAGE_SIZE:
                return (
                    f"Image too small ({w}×{h}px) for reliable analysis — "
                    f"minimum is {_MIN_IMAGE_SIZE}×{_MIN_IMAGE_SIZE}px."
                )
    except Exception as e:
        return f"Could not open image: {e}"

    return None


# ── 4. Build reasons ──────────────────────────────────────────────────────────

def _build_reasons_sightengine(
    is_ai: bool, confidence: float, is_uncertain: bool
) -> list[str]:
    if is_uncertain:
        label = "ambiguous (score in uncertain range)"
    else:
        label = "AI-generated" if is_ai else "real"
    reasons = [f"Sightengine: image classified as {label} ({confidence:.0%} confidence)"]
    if is_uncertain:
        reasons.append("Result is uncertain — manual review recommended.")
    return reasons


def _build_reasons_groq(
    is_ai: bool, confidence: float, is_uncertain: bool, signals: list[str]
) -> list[str]:
    if is_uncertain:
        label = "ambiguous (score in uncertain range)"
    else:
        label = "AI-generated" if is_ai else "real"
    reasons = [f"Groq vision: image classified as {label} ({confidence:.0%} confidence)"]
    if is_uncertain:
        reasons.append("Result is uncertain — manual review recommended.")
    for s in signals[:2]:
        if s:
            reasons.append(f"Visual signal: {s}")
    return reasons


# ── 5. Arabic verdict ─────────────────────────────────────────────────────────

def _build_arabic_verdict_prompt(
    is_ai: bool,
    confidence: float,
    is_uncertain: bool,
    reasons: list[str],
    source: str,
    image_path: str,
) -> str:
    filename = os.path.basename(image_path)

    if is_uncertain:
        verdict_label = "UNCERTAIN — could be AI or real"
    else:
        verdict_label = "AI-GENERATED" if is_ai else "REAL PHOTO"

    reasons_text   = "\n".join(f"- {r}" for r in reasons)
    uncertainty_note = (
        "\nNote: confidence is LOW — the Arabic sentence MUST reflect uncertainty "
        "and advise caution without making a definitive claim."
        if is_uncertain or confidence < _UNCERTAINTY_HIGH
        else ""
    )

    return f"""You are a forensic image analyst for Thiqa, an Algerian seller-verification platform.
A product image was analyzed by {source}.

File: {filename}
Final Verdict: {verdict_label}
Confidence: {confidence:.0%}
Evidence:
{reasons_text}
{uncertainty_note}

Write ONE sentence in Modern Standard Arabic that:
- Clearly tells an Algerian buyer whether the image is real or AI-generated
- Mentions the confidence level naturally
- Reflects uncertainty if confidence is below 65%
- Is simple, direct, and trustworthy in tone

Return ONLY a JSON object, no markdown, no preamble:
{{
  "verdict_arabic": "<one Arabic sentence>"
}}"""


def _get_arabic_verdict(
    is_ai: bool,
    confidence: float,
    is_uncertain: bool,
    reasons: list[str],
    source: str,
    image_path: str,
) -> str:
    prompt = _build_arabic_verdict_prompt(
        is_ai, confidence, is_uncertain, reasons, source, image_path
    )
    raw = call_llm(prompt)
    try:
        return json.loads(raw).get("verdict_arabic", _default_arabic_verdict(is_ai, is_uncertain))
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group()).get(
                    "verdict_arabic", _default_arabic_verdict(is_ai, is_uncertain)
                )
            except json.JSONDecodeError:
                pass
    return _default_arabic_verdict(is_ai, is_uncertain)


def _default_arabic_verdict(is_ai: bool, is_uncertain: bool = False) -> str:
    if is_uncertain:
        return "لم يتمكن النظام من تحديد ما إذا كانت هذه الصورة حقيقية أم مُولَّدة بالذكاء الاصطناعي، يُرجى توخي الحذر."
    if is_ai:
        return "تم اكتشاف أن هذه الصورة مُولَّدة بالذكاء الاصطناعي، يُرجى توخي الحذر."
    return "تبدو هذه الصورة حقيقية ولم يتم اكتشاف أي مؤشرات على توليدها بالذكاء الاصطناعي."


# ── Public interface ──────────────────────────────────────────────────────────

def check_image_authenticity(image_path: str) -> dict:
    """
    Checks whether an image is AI-generated.
    Uses Sightengine as primary, Groq vision as fallback.

    Returns
    -------
    dict with keys:
        is_ai_generated  – bool
        confidence       – float 0.0–1.0
        is_uncertain     – bool   (True when score is in the 0.35–0.65 zone)
        verdict_arabic   – str
        reasons          – list[str]
        safe_to_trust    – bool   (False when uncertain or AI detected)
        generator        – dict   (always empty — reserved for future use)
    """
    # ── Validate image ─────────────────────────────────────────────────────
    error = _validate_image(image_path)
    if error:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(error)
        return _fallback(reason=error)

    # ── Try Sightengine first ──────────────────────────────────────────────
    try:
        is_ai, confidence, is_uncertain = _call_sightengine(image_path)
        reasons = _build_reasons_sightengine(is_ai, confidence, is_uncertain)
        source  = "Sightengine (professional AI image detector)"

    # ── Fall back to Groq vision ───────────────────────────────────────────
    except (EnvironmentError, requests.HTTPError, Exception) as e:
        try:
            is_ai, confidence, is_uncertain, signals = _call_groq_vision(image_path)
            reasons = _build_reasons_groq(is_ai, confidence, is_uncertain, signals)
            source  = "Groq vision model (fallback)"
        except Exception as e2:
            return _fallback(
                reason=f"Both detectors failed — Sightengine: {e} | Groq: {e2}"
            )

    verdict_arabic = _get_arabic_verdict(
        is_ai, confidence, is_uncertain, reasons, source, image_path
    )

    return {
        "is_ai_generated": is_ai,
        "confidence":      confidence,
        "is_uncertain":    is_uncertain,
        "verdict_arabic":  verdict_arabic,
        "reasons":         reasons,
        # ✅ safe_to_trust is False when AI detected OR result is uncertain
        "safe_to_trust":   not is_ai and not is_uncertain,
        "generator":       {},
    }


def _fallback(reason: str = "") -> dict:
    return {
        "is_ai_generated": False,
        "confidence":      0.0,
        "is_uncertain":    True,
        # ✅ Fixed: unknown ≠ safe — was True before, now correctly False
        "safe_to_trust":   False,
        "verdict_arabic":  "لم نتمكن من تحليل الصورة، يُرجى توخي الحذر.",
        "reasons":         [reason] if reason else [],
        "generator":       {},
    }