from fastapi import APIRouter

router = APIRouter()

@router.post("/")
def submit_review(body: dict):
    """STATUS: STUB"""
    return {
        "success": True,
        "review_id": "stub-review-id-001"
    }

@router.get("/")
def get_reviews(seller_id: str):
    """STATUS: STUB"""
    return {
        "reviews": [
            {
                "id": "stub-review-id-001",
                "seller_id": seller_id,
                "stars": 4,
                "product_matched": True,
                "responded_fast": True,
                "item_received": True,
                "would_buy_again": True,
                "comment": "تعامل مليح",
                "reviewer_email": "user@example.com",
                "created_at": "2026-03-19T00:00:00Z"
            }
        ],
        "avg_stars": 4.0
    }