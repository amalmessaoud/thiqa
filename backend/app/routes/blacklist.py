from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_blacklist(
    page: int = 1,
    scam_type: str = None,
    platform: str = None,
    search: str = None
):
    """STATUS: STUB"""
    return {
        "results": [
            {
                "profile_url": "facebook.com/BoutiqueTest",
                "platform": "facebook",
                "display_name": "Boutique Test",
                "scam_types": ["ghost_seller"],
                "report_count": 3,
                "latest_report": "2026-03-19T00:00:00Z"
            }
        ],
        "count": 1,
        "next": None,
        "previous": None
    }