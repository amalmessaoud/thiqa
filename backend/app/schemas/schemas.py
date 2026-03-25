from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional
import uuid


# ── Auth ───────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: str
    token: str
    email: str


class MeResponse(BaseModel):
    id: str
    email: str
    created_at: str


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
    label: str
    scam_type: Optional[str]
    red_flags: list[str]
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
    analysis: Optional[TextAnalyzeResponse]


# ── Reports ────────────────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    id: str
    seller_id: str
    scam_type: str
    description: Optional[str]
    screenshot_url: str
    credibility_score: Optional[float]
    credibility_reason: Optional[str]
    reporter_email: str
    created_at: str


class ReportSubmitResponse(BaseModel):
    success: bool
    report_id: str
    credibility_score: Optional[float]
    credibility_label: Optional[str]
    message: str


class ReportsListResponse(BaseModel):
    reports: list[ReportResponse]