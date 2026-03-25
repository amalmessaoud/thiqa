import sys
import os

# Make the ai/ package importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, search, analyze, reports, reviews, blacklist

app = FastAPI(title="Thiqa API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(search.router,    prefix="/api",           tags=["search"])
app.include_router(analyze.router,   prefix="/api/analyze",   tags=["analyze"])
app.include_router(reports.router,   prefix="/api/reports",   tags=["reports"])
app.include_router(reviews.router,   prefix="/api/reviews",   tags=["reviews"])
app.include_router(blacklist.router, prefix="/api/blacklist", tags=["blacklist"])
@app.get("/debug/step")
def debug_step():
    import time
    from app.config import DATABASE_URL
    from sqlalchemy import create_engine, text
    
    print("STEP 1 - starting")
    
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_timeout=5)
    print("STEP 2 - engine created")
    
    with engine.connect() as conn:
        print("STEP 3 - connected")
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        print("STEP 4 - query done:", result.scalar())
    
    print("STEP 5 - done")
    return {"status": "ok"}
@app.get("/debug/db")
def debug_db():
    from app.db.database import get_db
    db = next(get_db())
    from app.models.models import User
    count = db.query(User).count()
    return {"user_count": count}
@app.get("/")
def root():
    return {"status": "Thiqa API running"}