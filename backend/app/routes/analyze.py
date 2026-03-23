from fastapi import APIRouter

router = APIRouter()

@router.post("/text/")
def analyze_text(body: dict):
    """STATUS: STUB"""
    return {
        "scam_probability": 0.85,
        "is_scam": True,
        "confidence": "high",
        "scam_type": "advance_payment",
        "red_flags": [
            {"pattern": "advance_payment_request",
             "quote": "حول الفلوس قبل",
             "severity": "high"}
        ],
        "verdict_darija": "هاد الرسالة فيها علامات نصب واضحة",
        "safe_to_proceed": False
    }

@router.post("/image/")
def analyze_image():
    """STATUS: STUB"""
    return {"is_fake": True, "fake_probability": 0.94, "verdict": "AI-generated or stolen"}

@router.post("/screenshot/")
def analyze_screenshot():
    """STATUS: STUB"""
    return {
        "extracted_text": "حول 5000 دج على CCP قبل ما نبعث ليك",
        "analysis": {
            "scam_probability": 0.85,
            "is_scam": True,
            "scam_type": "advance_payment",
            "red_flags": [],
            "verdict_darija": "هاد الرسالة فيها علامات نصب واضحة"
        }
    }

@router.get("/profile/")
def analyze_profile(url: str):
    """STATUS: STUB"""
    return {"page_age_days": 21, "post_count": 8, "account_signal": "suspicious"}