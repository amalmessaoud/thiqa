from fastapi import APIRouter

router = APIRouter()

@router.post("/register/")
def register(body: dict):
    """STATUS: STUB"""
    return {
        "user_id": "stub-user-id-001",
        "token": "stub-jwt-token",
        "email": body.get("email")
    }

@router.post("/login/")
def login(body: dict):
    """STATUS: STUB"""
    return {
        "user_id": "stub-user-id-001",
        "token": "stub-jwt-token",
        "email": body.get("email")
    }

@router.post("/logout/")
def logout():
    """STATUS: STUB"""
    return {"success": True}

@router.get("/me/")
def me():
    """STATUS: STUB"""
    return {
        "id": "stub-user-id-001",
        "email": "user@example.com",
        "created_at": "2026-03-19T00:00:00Z"
    }