from fastapi import APIRouter

router = APIRouter()

@router.get("/search/")
def search(q: str):
    """STATUS: STUB"""
    return {
        "found": True,
        "seller": {
            "id": "stub-seller-id-001",
            "profile_url": q,
            "platform": "facebook",
            "display_name": "Boutique Test",
            "profile_photo_url": None,
            "account_age_days": 21,
            "post_count": 8,
            "contacts": [
                {"type": "phone", "value": "0770123456"}
            ]
        },
        "trust_score": {
            "score": 28,
            "verdict_color": "red",
            "verdict_darija": "تجنب هذا البائع",
            "verdict_narrative": "هذا البائع عندو تقارير متعددة على النصب",
            "recommendation": "تجنب"
        },
        "reports": [],
        "reviews": [],
        "avg_stars": None
    }