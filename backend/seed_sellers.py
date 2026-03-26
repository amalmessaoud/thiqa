"""
Seed the database with scraped seller data.

Supports Facebook, Instagram, and TikTok pages.
Run from thiqa/backend/ with venv active:
    python seed_sellers.py

Usage:
    python seed_sellers.py                          # seeds thiqa_dataset.json
    python seed_sellers.py path/to/dataset.json     # seeds a specific file
    python seed_sellers.py file1.json file2.json    # seeds multiple files
"""
import sys
import os
import json
from datetime import datetime

# Make app importable
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.models.models import SellerProfile, Platform


# ── Helpers ────────────────────────────────────────────────────────────────────

def detect_platform(page_url: str, platform_hint: str = None) -> Platform:
    """Detect platform from URL or Apify platform hint."""
    if platform_hint:
        hint = platform_hint.lower()
        if "instagram" in hint or "ig_" in hint:
            return Platform.instagram
        if "tiktok" in hint or "tt_" in hint:
            return Platform.tiktok
        if "facebook" in hint or "fb_" in hint:
            return Platform.facebook

    url = (page_url or "").lower()
    if "instagram.com" in url:
        return Platform.instagram
    if "tiktok.com" in url:
        return Platform.tiktok
    return Platform.facebook


def parse_account_age(creation_date_str: str) -> int | None:
    """Convert 'March 10, 2016' or 'March 6, 2020' → days since then."""
    if not creation_date_str:
        return None
    formats = ["%B %d, %Y", "%B %Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            created = datetime.strptime(creation_date_str.strip(), fmt)
            return max(0, (datetime.now() - created).days)
        except ValueError:
            continue
    return None


def extract_page_data(record: dict) -> dict | None:
    """
    Handle both dataset formats:
    Format A (flat): { "page_url": ..., "title": ..., "posts": [...] }
    Format B (wrapped): { "platform": "fb_page", "url": ..., "data": { ... } }
    """
    # Format B — Apify wrapped format
    if "data" in record and isinstance(record["data"], dict):
        data = record["data"]
        platform_hint = record.get("platform", "")
        return {
            "page_url": data.get("page_url") or record.get("url"),
            "title": data.get("title") or data.get("page_name"),
            "creation_date": data.get("creation_date"),
            "post_count": (data.get("stats") or {}).get("post_count"),
            "posts": data.get("posts", []),
            "platform_hint": platform_hint,
            "bio": data.get("bio") or data.get("intro"),
        }

    # Format A — flat format
    if "page_url" in record:
        return {
            "page_url": record.get("page_url"),
            "title": record.get("title") or record.get("page_name"),
            "creation_date": record.get("creation_date"),
            "post_count": (record.get("stats") or {}).get("post_count"),
            "posts": record.get("posts", []),
            "platform_hint": "",
            "bio": record.get("bio") or record.get("intro"),
        }

    return None


def get_post_texts(posts: list) -> str:
    """Extract meaningful post texts, skip empty ones."""
    texts = []
    for post in posts[:10]:  # last 10 posts only
        text = post.get("text", "").strip()
        if text and len(text) > 15:  # skip very short/empty posts
            texts.append(text)
    return "\n---\n".join(texts)


# ── Main seed function ─────────────────────────────────────────────────────────

def seed_from_file(json_path: str, db) -> tuple[int, int]:
    """
    Seed from a JSON file. Returns (seeded_count, skipped_count).
    Handles both list format and single object format.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Normalize to list
    if isinstance(raw, dict):
        records = [raw]
    elif isinstance(raw, list):
        records = raw
    else:
        print(f"  [!] Unrecognized format in {json_path}")
        return 0, 0

    seeded = 0
    skipped = 0

    for record in records:
        page = extract_page_data(record)
        if not page:
            skipped += 1
            continue

        page_url = page["page_url"]
        if not page_url:
            skipped += 1
            continue

        # Normalize URL — strip trailing slash for consistency
        page_url = page_url.rstrip("/")

        # Skip if already exists
        existing = db.query(SellerProfile).filter(
            SellerProfile.profile_url == page_url
        ).first()
        if existing:
            skipped += 1
            continue

        platform = detect_platform(page_url, page.get("platform_hint", ""))
        account_age = parse_account_age(page.get("creation_date"))
        post_count = page.get("post_count")

        # Display name: prefer title, fall back to page_name from URL
        display_name = page.get("title") or page_url.split("/")[-1]
        if isinstance(display_name, list):
            # Some FB pages return bio as list
            display_name = display_name[0] if display_name else None

        seller = SellerProfile(
            profile_url=page_url,
            platform=platform,
            display_name=str(display_name)[:200] if display_name else None,
            account_age_days=account_age,
            post_count=post_count,
        )
        db.add(seller)
        seeded += 1

    db.commit()
    return seeded, skipped


def run(file_paths: list[str]):
    db = SessionLocal()
    total_seeded = 0
    total_skipped = 0

    try:
        for path in file_paths:
            if not os.path.exists(path):
                print(f"[!] File not found: {path}")
                continue

            print(f"\nSeeding from: {path}")
            seeded, skipped = seed_from_file(path, db)
            total_seeded += seeded
            total_skipped += skipped
            print(f"  ✓ Seeded: {seeded}  |  Skipped (exists or invalid): {skipped}")

    finally:
        db.close()

    print(f"\n{'='*40}")
    print(f"Total seeded : {total_seeded}")
    print(f"Total skipped: {total_skipped}")
    print(f"{'='*40}")


if __name__ == "__main__":
    # Default: look for thiqa_dataset.json next to this script
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        default = os.path.join(os.path.dirname(__file__), "thiqa_dataset.json")
        if not os.path.exists(default):
            print(f"[!] No file specified and thiqa_dataset.json not found at {default}")
            print("Usage: python seed_sellers.py [file1.json] [file2.json] ...")
            sys.exit(1)
        files = [default]

    run(files)