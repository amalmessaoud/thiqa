# ai/feedback/summarizer.py
# ---------------------------------------------------------------------------
# Summarises all buyer feedbacks for one seller into a short Darija paragraph.
# Uses call_llm (Groq LLaMA) — same pattern as ai/text_analyzer/llm_analyzer.py
#
# Input  : list[str]  — raw buyer feedback strings (AR / Darija / FR / mixed)
# Output : dict with keys:
#            summary         – 2-4 sentence paragraph in the dominant language
#            sentiment_hint  – "mostly_positive" | "mixed" | "mostly_negative"
#            language_used   – "darija" | "arabic" | "french" | "mixed"
#            total_count     – int
# ---------------------------------------------------------------------------

import json
import re
from ai.utils.llm_client import call_llm

# FIX: system instruction moved to the system role instead of buried in the
#      user message — gives the model clearer separation of context vs task
_SYSTEM = (
    'أنت مساعد تحليل المصداقية لمنصة "ثقة" (Thiqa)، منصة جزائرية للتحقق من البائعين. '
    "مهمتك تلخيص تقييمات المشترين بدقة وموضوعية."
)


def _build_prompt(feedbacks: list[str]) -> str:
    numbered = "\n".join(f"{i+1}. {fb.strip()}" for i, fb in enumerate(feedbacks))
    return f"""اقرأ كل تقييمات المشترين التالية عن بائع واحد وأعط ملخصاً موحداً.

التقييمات:
{numbered}

أعط الجواب فقط كـ JSON بهذه المفاتيح بالضبط، بدون أي نص إضافي:
{{
  "summary": "<ملخص من 2-4 جمل بالدارجة الجزائرية يوضح تجربة المشترين — اذكر النقاط الإيجابية والسلبية بنسبة واقعية>",
  "sentiment_hint": "<واحدة فقط من: mostly_positive | mixed | mostly_negative>",
  "language_used": "<واحدة فقط من: darija | arabic | french | mixed>"
}}

قواعد:
- الملخص يعكس جميع التقييمات بنسبها الحقيقية.
- تجاهل التقييمات الفارغة أو غير المفهومة (مثل "aaa", "test").
- لا تخترع معلومات غير موجودة في التقييمات.
- JSON فقط بدون ```json أو أي شيء آخر."""


def summarize_feedbacks(feedbacks: list[str]) -> dict:
    """
    Parameters
    ----------
    feedbacks : list[str]
        Raw buyer feedback strings for one seller (AR / Darija / FR / mixed).

    Returns
    -------
    dict — summary, sentiment_hint, language_used, total_count
    """
    feedbacks = [f for f in feedbacks if f and f.strip()]

    if not feedbacks:
        return {
            "summary": "ما كاينش تقييمات بعد على هذا البائع.",
            "sentiment_hint": "mixed",
            "language_used": "darija",
            "total_count": 0,
        }

    raw    = call_llm(_build_prompt(feedbacks), system=_SYSTEM)
    result = _parse(raw, total_count=len(feedbacks))
    result["total_count"] = len(feedbacks)
    return result


def _parse(raw: str, total_count: int = 0) -> dict:
    """Mirrors the JSON-extraction pattern used in llm_analyzer.py."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return _fallback(total_count)


def _fallback(total_count: int = 0) -> dict:
    return {
        "summary": "ما قدرناش نلخصو التقييمات، كن حذر.",
        "sentiment_hint": "mixed",
        "language_used": "darija",
        "total_count": total_count,   # FIX: was hardcoded 0
    }