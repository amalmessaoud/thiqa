from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional, Any
import uuid

# ── Auth ───────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None 

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
    full_name: Optional[str] = None

class MeResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
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


# ── Feedback Summary ──────────────────────────────────────────────────────────

class FeedbackSummaryRequest(BaseModel):
    seller_id: str
    feedbacks: Optional[list[str]] = None

class FeedbackSummaryResponse(BaseModel):
    seller_id: str
    summary: str
    sentiment_hint: str        # "mostly_positive" | "mixed" | "mostly_negative"
    language_used: str         # "darija" | "arabic" | "french" | "mixed"
    total_count: int


# ── AI Image Detector ─────────────────────────────────────────────────────────

class ImageAuthenticityResponse(BaseModel):
    is_ai_generated: bool
    confidence: float
    verdict_arabic: str
    reasons: list[str]
    safe_to_trust: bool


# ── Flagged Post (inside image analysis) ─────────────────────────────────────

class FlaggedPostItem(BaseModel):
    post_url: str
    confidence: float
    verdict_arabic: str
    reasons: list[str]


# ── Image Analysis Summary (returned in search response) ─────────────────────

class ImageAnalysisSummary(BaseModel):
    total_images_checked: int = 0
    ai_generated_count: int = 0
    uncertain_count: int = 0
    ai_ratio: float = 0.0
    flagged_posts: list[FlaggedPostItem] = []


# ── Raw Engagement Stats ──────────────────────────────────────────────────────

class RawEngagementStats(BaseModel):
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    avg_likes_per_post: float = 0.0
    avg_comments_per_post: float = 0.0
    avg_shares_per_post: float = 0.0
    avg_reactions_per_post: float = 0.0


# ── Seller Detail (inside search response) ────────────────────────────────────

class SellerDetail(BaseModel):
    id: str
    profile_url: str
    platform: str
    display_name: Optional[str]
    profile_photo_url: Optional[str]
    account_age_days: Optional[int]
    post_count: Optional[int]
    category: Optional[str]
    followers: int = 0
    engagement_rate: float = 0.0
    contacts: list[dict] = []
    # Raw engagement stats
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    avg_reactions_per_post: float = 0.0

    class Config:
        from_attributes = True


# ── Trust Score Detail (inside search response) ───────────────────────────────

class TrustScoreDetail(BaseModel):
    score: int
    verdict_color: str
    verdict: str
    verdict_darija: str
    verdict_narrative: str
    recommendation: str
    model_used: str
    rule_based_score: int
    engagement_bonus: int
    sentiment_bonus: int
    ai_image_penalty: int = 0
    pre_bonus_score: int
    feature_values: dict = {}
    reports_contribution: str
    reviews_contribution: str


# ── Full Search Response ──────────────────────────────────────────────────────

class SearchResponse(BaseModel):
    found: bool
    seller: Optional[SellerDetail]
    trust_score: Optional[TrustScoreDetail]
    sentiment_summary: Optional[dict]
    image_analysis: ImageAnalysisSummary = ImageAnalysisSummary()
    reports: list[dict] = []
    reports_summary: Optional[str]
    reviews: list[dict] = []
    reviews_summary: Optional[str]
    avg_stars: Optional[float]

    class Config:
        from_attributes = True


# ── Sentiment Analysis ────────────────────────────────────────────────────────

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
    risk_category:    str
    risk_probability: float
    risk_class:       int


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
    success:           bool
    report_id:         str
    credibility_score: Optional[float]
    credibility_label: Optional[str]
    message:           str
    recommendations:   list[TrustedSellerItem]
    
class ReviewResponse(BaseModel):
    id: str
    seller_id: str
    stars: int
    comment: Optional[str]
    product_matched: bool = False
    responded_fast: bool = False
    item_received: bool = False
    would_buy_again: bool = False
    reviewer_email: str
    created_at: str