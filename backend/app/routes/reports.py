from fastapi import APIRouter

router = APIRouter()

@router.post("/")
def submit_report(body: dict):
    """STATUS: STUB"""
    return {
        "success": True,
        "report_id": "stub-report-id-001",
        "credibility_score": 0.85,
        "message": "تم تسجيل بلاغك بنجاح"
    }

@router.get("/")
def get_reports(seller_id: str):
    """STATUS: STUB"""
    return {
        "reports": [
            {
                "id": "stub-report-id-001",
                "seller_id": seller_id,
                "scam_type": "ghost_seller",
                "description": "أخذ الفلوس وما بعثش",
                "screenshot_url": "https://example.com/screenshot.jpg",
                "credibility_score": 0.85,
                "credibility_reason": "الصورة تبين محادثة واضحة وإثبات تحويل",
                "reporter_email": "user@example.com",
                "created_at": "2026-03-19T00:00:00Z"
            }
        ]
    }