from pydantic import BaseModel, field_validator
from typing import Optional


# ── Analyze: Text ──────────────────────────────────────────────────────────────

class TextAnalyzeRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must not be empty")
        return v.strip()


class TextAnalyzeResponse(BaseModel):
    label: str                        # "scam" | "legit" | "unknown"
    scam_type: Optional[str]          # ScamType value or null
    red_flags: list[str]              # list of Darija strings
    verdict_darija: str
    safe_to_proceed: bool


# ── Analyze: Screenshot ────────────────────────────────────────────────────────

class ScreenshotAnalyzeResponse(BaseModel):
    extracted_text: str
    confidence: float
    word_count: int
    extraction_successful: bool
    images_processed: int
    images_failed: int
    analysis: Optional[TextAnalyzeResponse]  # None if OCR extracted nothing