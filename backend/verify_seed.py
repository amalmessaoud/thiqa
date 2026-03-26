"""
Quick check: print what's in the DB after seeding.
Run from thiqa/backend/:
    python verify_seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.models.models import SellerProfile, Platform
from sqlalchemy import func

db = SessionLocal()

total = db.query(SellerProfile).count()
fb    = db.query(SellerProfile).filter(SellerProfile.platform == Platform.facebook).count()
ig    = db.query(SellerProfile).filter(SellerProfile.platform == Platform.instagram).count()
tt    = db.query(SellerProfile).filter(SellerProfile.platform == Platform.tiktok).count()

with_age   = db.query(SellerProfile).filter(SellerProfile.account_age_days != None).count()
with_posts = db.query(SellerProfile).filter(SellerProfile.post_count != None).count()

print(f"\n{'='*45}")
print(f"  Total sellers     : {total}")
print(f"  Facebook          : {fb}")
print(f"  Instagram         : {ig}")
print(f"  TikTok            : {tt}")
print(f"  With account age  : {with_age}")
print(f"  With post count   : {with_posts}")
print(f"{'='*45}")

print("\nSample (first 5):")
for s in db.query(SellerProfile).limit(5).all():
    print(f"  [{s.platform.value}] {s.display_name or 'unnamed'}")
    print(f"    {s.profile_url}")
    print(f"    age={s.account_age_days}d  posts={s.post_count}")

db.close()