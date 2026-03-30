"""
Step 1: Auto-label all scraped sellers with Arabic product categories.
Uses LLM (Groq) to classify each seller based on post texts + page metadata.

Run from thiqa/backend/ with venv active:
    python label_dataset.py

Output: backend/labeled_dataset.json
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.utils.llm_client import call_llm

# ── Our 10 target categories ───────────────────────────────────────────────────
CATEGORIES = [
    "ملابس",              # clothing, fashion, traditional dress
    "إلكترونيات",         # phones, tech, computers
    "منتجات_أطفال",       # baby and kids products
    "منتجات_غذائية",      # food, groceries, nutrition
    "مستحضرات_تجميل",     # cosmetics, beauty, skincare
    "أثاث_وديكور",        # furniture, home decor
    "متجر_إلكتروني",      # general online store / marketplace
    "فن_وحرف",            # art, crafts, handmade
    "خدمات",              # services, freelance, consulting
    "أخرى",               # anything else
]

CATEGORIES_STR = " | ".join(CATEGORIES)


def build_label_prompt(page_title: str, bio: str, fb_category: str, post_texts: list[str]) -> str:
    posts_sample = "\n".join(f"- {t[:300]}" for t in post_texts[:6])
    return f"""صنف هذا البائع الجزائري. أعد كلمة واحدة فقط من القائمة التالية، بدون أي نص آخر إطلاقاً:

{CATEGORIES_STR}

معلومات البائع:
الاسم: {page_title}
الوصف: {(bio or '')[:200]}
المنشورات: {chr(10).join(f'- {t[:200]}' for t in post_texts[:5])}

الفئة:"""

def load_json(path: str) -> list:
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    return d if isinstance(d, list) else [d]


def extract_page_info(record: dict) -> dict:
    """Handle both flat format and Apify wrapped format."""
    if "data" in record and isinstance(record["data"], dict):
        data = record["data"]
        return {
            "page_url":    data.get("page_url") or record.get("url", ""),
            "title":       data.get("title") or data.get("page_name", ""),
            "bio":         data.get("bio") or data.get("intro", ""),
            "fb_category": data.get("category", ""),
            "posts":       data.get("posts", []),
        }
    return {
        "page_url":    record.get("page_url", ""),
        "title":       record.get("title") or record.get("page_name", ""),
        "bio":         record.get("bio") or record.get("intro", ""),
        "fb_category": record.get("category", ""),
        "posts":       record.get("posts", []),
    }


def get_post_texts(posts: list) -> list[str]:
    texts = []
    for p in posts:
        t = (p.get("text") or "").strip()
        if t and len(t) > 15:
            texts.append(t)
    return texts


def label_seller(info: dict) -> str:
    texts = get_post_texts(info["posts"])

    # If no post texts at all, use simple heuristic from fb_category
    if not texts:
        fb_cat = (info["fb_category"] or "").lower()
        if "cloth" in fb_cat or "fashion" in fb_cat:
            return "ملابس"
        if "food" in fb_cat or "grocery" in fb_cat:
            return "منتجات_غذائية"
        if "mobile" in fb_cat or "tech" in fb_cat or "it" in fb_cat:
            return "إلكترونيات"
        if "baby" in fb_cat or "kids" in fb_cat:
            return "منتجات_أطفال"
        if "art" in fb_cat or "craft" in fb_cat:
            return "فن_وحرف"
        return "أخرى"

    prompt = build_label_prompt(
        info["title"],
        info["bio"],
        info["fb_category"],
        texts,
    )

    try:
        result = call_llm(prompt).strip()
        # Validate — must be one of our categories
        if result in CATEGORIES:
            return result
        # Sometimes LLM adds extra text — try to find the category in the response
        for cat in CATEGORIES:
            if cat in result:
                return cat
        return "أخرى"
    except Exception as e:
        print(f"    [!] LLM error: {e}")
        return "أخرى"


def main():
    output_path = os.path.join(os.path.dirname(__file__), "labeled_dataset.json")
    files = {
        "fb":  os.path.join(os.path.dirname(__file__), "thiqa_dataset.json"),
        "ig":  os.path.join(os.path.dirname(__file__), "ig_db.json"),
        "tt":  os.path.join(os.path.dirname(__file__), "tt_db.json"),
    }

    all_records = []

    for source, path in files.items():
        if not os.path.exists(path):
            print(f"[!] File not found: {path}, skipping")
            continue
        records = load_json(path)
        print(f"\nLoaded {len(records)} records from {source}")
        for i, record in enumerate(records):
            info = extract_page_info(record)
            if not info["page_url"]:
                continue
            all_records.append((source, info))

    print(f"\nTotal sellers to label: {len(all_records)}")
    print("Starting LLM labeling (this will take ~3-5 min for 50 sellers)...\n")

    labeled = []
    category_counts = {c: 0 for c in CATEGORIES}

    for i, (source, info) in enumerate(all_records):
        texts = get_post_texts(info["posts"])
        print(f"[{i+1}/{len(all_records)}] {info['title'][:50]} ({len(texts)} posts)...")

        category = label_seller(info)
        category_counts[category] += 1
        print(f"    → {category}")

        # Build training examples — one per seller using all post texts combined
        combined_text = " [SEP] ".join(texts[:8]) if texts else info["bio"] or info["title"]

        labeled.append({
            "page_url":    info["page_url"],
            "title":       info["title"],
            "source":      source,
            "category":    category,
            "text":        combined_text[:1500],   # combined posts as single training example
            "post_count":  len(texts),
        })

        # Also add individual posts as separate training examples (more data)
        for post_text in texts[:5]:
            labeled.append({
                "page_url":  info["page_url"],
                "title":     info["title"],
                "source":    source,
                "category":  category,
                "text":      post_text[:512],
                "post_count": 1,
            })

        # Rate limit — avoid hitting Groq too fast
        time.sleep(0.3)

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"Labeled {len(labeled)} training examples")
    print(f"From {len(all_records)} sellers")
    print("\nCategory distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"  {cat:<25} {count:>3}  {bar}")
    print(f"\nSaved to: {output_path}")
    print("="*50)


if __name__ == "__main__":
    main()