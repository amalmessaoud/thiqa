from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional, Any
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

# ── Scraping ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    url: str

class AnalyzeResponse(BaseModel):
    id: str
    platform: str
    url: str
    data: Any
    created_at: str

    class Config:
        from_attributes = True

class HistoryItem(BaseModel):
    id: str
    url: str
    platform: str
    page_name: Optional[str]
    title: Optional[str]
    followers: Optional[int]
    created_at: str

    class Config:
        from_attributes = True



# ── Feedback Summary (Part 1) ─────────────────────────────────────────────────
 
class FeedbackSummaryRequest(BaseModel):
    seller_id: str
    # Optional: pass feedbacks directly (for tests). If None, route loads from DB.
    feedbacks: Optional[list[str]] = None
 
 
class FeedbackSummaryResponse(BaseModel):
    seller_id: str
    summary: str
    sentiment_hint: str        # "mostly_positive" | "mixed" | "mostly_negative"
    language_used: str         # "darija" | "arabic" | "french" | "mixed"
    total_count: int
 
 
# ── AI Image Detector (Part 2) ────────────────────────────────────────────────
 
class ImageAuthenticityResponse(BaseModel):
    is_ai_generated: bool
    confidence: float          # 0.0 – 1.0
    verdict_arabic: str
    reasons: list[str]
    safe_to_trust: bool
 
 
# ── Sentiment Analysis (Part 3) ───────────────────────────────────────────────

class CommentInput(BaseModel):
    text: str

class SentimentRequest(BaseModel):
    profile_url: str
    post_url: str
    comments: list[CommentInput]

    @field_validator("comments")
    @classmethod
    def must_not_be_empty(cls, v):
        if not v:
            raise ValueError("comments list must not be empty")
        return v

class SentimentResponse(BaseModel):
    profile_url: str
    post_url: str
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    irrelevant_pct: float
    total_analyzed: int
    summary: str
    top_positive: list[str]
    top_negative: list[str]
    
    
# ── Risk Classifier ───────────────────────────────────────────────────────────

class SellerRiskRequest(BaseModel):
    account_age_days:      Optional[float] = None
    post_count:            Optional[float] = None
    followers:             Optional[float] = None
    report_count:          Optional[float] = None
    avg_credibility_score: Optional[float] = None
    has_phone_contact:     Optional[int]   = None
    has_website:           Optional[int]   = None
    platform_facebook:     Optional[int]   = None
    platform_instagram:    Optional[int]   = None
    posts_per_month:       Optional[float] = None

class SellerRiskResponse(BaseModel):
    risk_category:    str    # "legit" | "suspicious" | "high_risk"
    risk_probability: float
    risk_class:       int    # 0 | 1 | 2


# ── Category Classifier ───────────────────────────────────────────────────────

class SellerCategoryRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must not be empty")
        return v.strip()

class SellerCategoryResponse(BaseModel):
    category: str
    
    
# ── Trusted Seller Recommender ────────────────────────────────────────────────

class TrustedSellerItem(BaseModel):
    id:           str
    display_name: Optional[str]
    profile_url:  str
    platform:     str
    category:     Optional[str]

    class Config:
        from_attributes = True

class ReportSubmitWithRecommendationsResponse(BaseModel):
    success:          bool
    report_id:        str
    credibility_score: Optional[float]
    credibility_label: Optional[str]
    message:          str
    recommendations:  list[TrustedSellerItem]