# backend/app/services/scraping.py
# ---------------------------------------------------------------------------
# Thiqa — Scraping service
# Platform : Facebook · Instagram · TikTok
# Stack    : FastAPI + SQLAlchemy + Apify
# ---------------------------------------------------------------------------

import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional
import asyncio, re

import httpx
from fastapi import HTTPException

log = logging.getLogger("thiqa")

# ── Constants ─────────────────────────────────────────────────────────────────

APIFY_BASE     = "https://api.apify.com/v2"
MAX_POSTS          = 25
MAX_COMMENTS       = 20   # per post on profile scrape
FETCH_COMMENTS     = 60   # fetch before filtering to top 20
POST_COMMENTS      = 30   # for single post scrape
FETCH_POST_COMMENTS = 90  # fetch before filtering to top 30


ACTORS = {
    "fb_page":     "apify~facebook-pages-scraper",
    "fb_posts":    "apify~facebook-posts-scraper",
    "fb_comments": "apify~facebook-comments-scraper",
    "ig":          "apify~instagram-scraper",
    "tt_profile":  "clockworks~tiktok-profile-scraper",
    "tt_posts":    "clockworks~free-tiktok-scraper",
    "tt_comments": "clockworks~tiktok-comments-scraper",
}


# ── Platform detection ────────────────────────────────────────────────────────

def detect_platform(url: str) -> Optional[str]:
    u = url.lower()
    if "facebook.com" in u:
        if any(s in u for s in ("/posts/", "/videos/", "/reels/", "story_fbid", "?p=", "permalink", "/share/r/", "/share/v/", "/share/p/")):
            return "fb_post"
        return "fb_page"
    if "instagram.com" in u:
        return "ig_post" if ("/p/" in u or "/reel/" in u) else "ig_profile"
    if "tiktok.com" in u:
        return "tt_post" if "/video/" in u else "tt_profile"
    return None


# ── Apify helpers ─────────────────────────────────────────────────────────────

async def _run(api_key: str, actor_id: str, inp: dict) -> str:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{APIFY_BASE}/acts/{actor_id}/runs?token={api_key}",
            json=inp, headers={"Content-Type": "application/json"},
        )
        if r.status_code not in (200, 201):
            raise HTTPException(400, f"Apify start failed [{actor_id}]: {r.text[:300]}")
        return r.json()["data"]["id"]

async def _poll(api_key: str, run_id: str, max_wait: int = 360) -> str:
    async with httpx.AsyncClient(timeout=15) as c:
        elapsed = 0
        while elapsed < max_wait:
            await asyncio.sleep(6); elapsed += 6
            d = (await c.get(f"{APIFY_BASE}/actor-runs/{run_id}?token={api_key}")).json()["data"]
            if d["status"] == "SUCCEEDED":
                return d["defaultDatasetId"]
            if d["status"] in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise HTTPException(400, f"Apify run {d['status']} [{run_id}]")
    raise HTTPException(408, "Scrape timed out")

async def _fetch(api_key: str, dataset_id: str) -> list:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{APIFY_BASE}/datasets/{dataset_id}/items?token={api_key}")
        data = r.json()
        return data if isinstance(data, list) else []

async def call_actor(api_key: str, actor_id: str, inp: dict) -> list:
    run_id     = await _run(api_key, actor_id, inp)
    dataset_id = await _poll(api_key, run_id)
    items      = await _fetch(api_key, dataset_id)
    log.debug("[%s] → %d items | first keys: %s",
              actor_id, len(items),
              list(items[0].keys())[:15] if items else "EMPTY")
    return items


# ── Comment mixer ─────────────────────────────────────────────────────────────

def mix_comments(comments: list, likes_key: str, date_key: str, limit: int = MAX_COMMENTS) -> list:
    if not comments:
        return []
    return sorted(comments, key=lambda c: c.get(likes_key, 0), reverse=True)[:limit]


# ── Scrapers ──────────────────────────────────────────────────────────────────

def _tt_username(url: str) -> str:
    m = re.search(r"tiktok\.com/@([^/?#&]+)", url)
    return m.group(1).strip() if m else url.rstrip("/").split("/")[-1].lstrip("@")

def _norm_url(u: str) -> str:
    return u.split("?")[0].rstrip("/").lower()


async def scrape_fb_page(api_key: str, url: str) -> dict:
    page_items, posts_items = await asyncio.gather(
        call_actor(api_key, ACTORS["fb_page"], {
            "startUrls": [{"url": url}],
            "maxPosts": 0,
            "scrapeAbout": True,
        }),
        call_actor(api_key, ACTORS["fb_posts"], {
            "startUrls": [{"url": url}],
            "maxPosts": MAX_POSTS,
            "maxPostComments": 0,
            "scrapeAbout": False,
        }),
    )

    page_info = page_items[0] if page_items else {}
    posts     = posts_items or []

    post_urls = [p["url"] for p in posts if p.get("url")][:MAX_POSTS]

    if post_urls:
        comment_items = await call_actor(api_key, ACTORS["fb_comments"], {
            "startUrls": [{"url": u} for u in post_urls],
            "maxComments": FETCH_COMMENTS,
            "includeNestedComments": False,
        })

        by_post = defaultdict(list)
        for c in comment_items:
            pu = _norm_url(c.get("facebookUrl") or c.get("postUrl") or c.get("url") or "")
            if pu:
                by_post[pu].append(c)

        for p in posts:
            pu = _norm_url(p.get("url") or "")
            p["latestComments"] = by_post.get(pu, [])

    page_info["posts"] = posts
    return page_info


async def scrape_fb_post(api_key: str, url: str) -> dict:
    post_items = await call_actor(api_key, ACTORS["fb_posts"], {
        "startUrls": [{"url": url}],
        "maxPosts": 1,
        "maxPostComments": 0,
        "scrapeAbout": False,
    })
    if not post_items:
        return {"posts": []}
    post     = post_items[0]
    post_url = post.get("url") or url
    comment_items = await call_actor(api_key, ACTORS["fb_comments"], {
        "startUrls": [{"url": post_url}],
        "maxComments": FETCH_POST_COMMENTS,
        "includeNestedComments": False,
    })
    post["latestComments"] = comment_items or []
    return {
        "posts":    [post],
        "pageUrl":  post.get("facebookUrl", ""),
        "pageName": post.get("pageName", ""),
        "title":    post.get("pageName", ""),
    }


async def scrape_ig_profile(api_key: str, url: str) -> dict:
    profile_items, posts_items = await asyncio.gather(
        call_actor(api_key, ACTORS["ig"], {
            "directUrls": [url],
            "resultsType": "details",
            "resultsLimit": 1,
        }),
        call_actor(api_key, ACTORS["ig"], {
            "directUrls": [url],
            "resultsType": "posts",
            "resultsLimit": MAX_POSTS,
            "addParentData": True,
            "maxComments": FETCH_COMMENTS,
        }),
    )
    profile = profile_items[0] if profile_items else {}
    profile["latestPosts"] = posts_items or []
    return profile


async def scrape_ig_post(api_key: str, url: str) -> dict:
    items = await call_actor(api_key, ACTORS["ig"], {
        "directUrls": [url],
        "resultsType": "posts",
        "resultsLimit": 1,
        "addParentData": True,
        "maxComments": FETCH_POST_COMMENTS,
    })
    return items[0] if items else {}



async def scrape_tt_profile(api_key: str, url: str) -> dict:
    username = _tt_username(url)

    profile_items, posts_items = await asyncio.gather(
        call_actor(api_key, ACTORS["tt_profile"], {
            "profiles": [username],
            "resultsPerPage": MAX_POSTS,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }),
        call_actor(api_key, ACTORS["tt_posts"], {
            "profiles": [username],
            "resultsPerPage": MAX_POSTS,
            "shouldDownloadVideos": False,
        }),
    )

    videos = posts_items or profile_items or []
    first  = videos[0] if videos else {}
    author = first.get("authorMeta") or first.get("author") or {}
    resolved_username = (
        author.get("name") or author.get("uniqueId")
        or first.get("uniqueId") or username
    )

    def video_url(v: dict) -> str:
        for f in ("webVideoUrl", "videoUrl", "url"):
            val = v.get(f, "")
            if val and "tiktok.com" in str(val):
                return val
        vid_id = v.get("id") or v.get("videoId")
        uname  = (v.get("authorMeta") or {}).get("name") or resolved_username
        return f"https://www.tiktok.com/@{uname}/video/{vid_id}" if vid_id else ""

    video_urls = [u for v in videos[:MAX_POSTS] if (u := video_url(v))]

    if video_urls:
        comment_items = await call_actor(api_key, ACTORS["tt_comments"], {
            "postURLs": video_urls,
            "commentsPerPost": FETCH_COMMENTS,
            "maxReplies": 0,
            "sortType": 1,
        })

        by_video = defaultdict(list)
        for c in comment_items:
            vu = _norm_url(
                c.get("videoWebUrl") or c.get("videoUrl")
                or c.get("postUrl") or c.get("url") or ""
            )
            if vu:
                by_video[vu].append(c)

        for v in videos:
            vu = _norm_url(video_url(v))
            v["comments"] = by_video.get(vu, [])

    return {
        "uniqueId":       resolved_username,
        "nickname":       author.get("nickName") or author.get("name") or resolved_username,
        "signature":      author.get("signature") or "",
        "followerCount":  author.get("fans") or author.get("followerCount", 0),
        "followingCount": author.get("following") or author.get("followingCount", 0),
        "videoCount":     author.get("video") or len(videos),
        "videos":         videos,
        # FIX: expose author avatar for profile_photo_url
        "profile_photo_url": (
            author.get("avatarLarger")
            or author.get("avatarMedium")
            or author.get("avatarThumb")
            or author.get("avatar")
            or ""
        ),
    }


async def scrape_tt_post(api_key: str, url: str) -> dict:
    post_items, comment_items = await asyncio.gather(
        call_actor(api_key, ACTORS["tt_posts"], {
            "postURLs": [url],
            "shouldDownloadVideos": False,
        }),
        call_actor(api_key, ACTORS["tt_comments"], {
            "postURLs": [url],
            "commentsPerPost": FETCH_POST_COMMENTS,
            "maxReplies": 0,
            "sortType": 1,
        }),
    )
    v = post_items[0] if post_items else {}
    v["comments"] = comment_items or []
    return v

# ── Normalisation ─────────────────────────────────────────────────────────────

def normalize(platform: str, raw: dict) -> dict:
    is_single_post = platform in ("fb_post", "ig_post", "tt_post")
    comment_limit  = POST_COMMENTS if is_single_post else MAX_COMMENTS

    if platform in ("fb_page", "fb_post"):
        posts_raw = raw.get("posts") or []

        def norm_post(p):
            raw_comments = p.get("latestComments") or []
            rxn_like  = p.get("reactionLikeCount", 0)
            rxn_love  = p.get("reactionLoveCount", 0)
            rxn_haha  = p.get("reactionHahaCount", 0)
            rxn_wow   = p.get("reactionWowCount", 0)
            rxn_sad   = p.get("reactionSadCount", 0)
            rxn_angry = p.get("reactionAngryCount", 0)

            # FIX: extract image URL from Facebook post media fields
            media_list = p.get("media") or []
            first_media = media_list[0] if media_list else {}
            image_url = (
                first_media.get("image") or
                first_media.get("url") or
                p.get("full_picture") or
                p.get("picture") or
                p.get("attachments", [{}])[0].get("media", {}).get("image", {}).get("src") if p.get("attachments") else None or
                ""
            )

            return {
                "post_url":           p.get("url", ""),
                "page_name":          p.get("pageName") or raw.get("title") or raw.get("pageName", ""),
                "date":               p.get("time") or p.get("timestamp") or p.get("date"),
                "text":               p.get("text") or p.get("message", ""),
                "likes":              p.get("likes", 0),
                "comments_count":     p.get("comments") if isinstance(p.get("comments"), int) else 0,
                "shares":             p.get("shares", 0),
                "reaction_like":      rxn_like,
                "reaction_love":      rxn_love,
                "reaction_haha":      rxn_haha,
                "reaction_wow":       rxn_wow,
                "reaction_sad":       rxn_sad,
                "reaction_angry":     rxn_angry,
                "total_reactions":    rxn_like + rxn_love + rxn_haha + rxn_wow + rxn_sad + rxn_angry,
                "has_media":          bool(p.get("media") or p.get("isVideo")),
                "media_count":        len(media_list),
                "media_descriptions": [m.get("text", "") for m in media_list],
                # FIX: image URL fields so _analyze_post_images can find them
                "media_url":          image_url,
                "display_url":        image_url,
                "full_picture":       p.get("full_picture") or p.get("picture") or "",
                "comment_list":       mix_comments(raw_comments, "likesCount", "date", limit=comment_limit),
            }

        posts = [norm_post(p) for p in posts_raw]
        n = len(posts) or 1

        # FIX: extract Facebook page profile photo
        fb_profile_photo = (
            raw.get("profilePhoto") or
            raw.get("profilePicture") or
            raw.get("profileImageUrl") or
            raw.get("cover", {}).get("source") if isinstance(raw.get("cover"), dict) else None or
            ""
        )

        return {
            "page_url":          raw.get("pageUrl") or raw.get("facebookUrl", ""),
            "page_name":         raw.get("title") or raw.get("pageName", ""),
            "title":             raw.get("title") or raw.get("pageName", ""),
            "bio":               raw.get("info") or raw.get("about") or raw.get("description", ""),
            "intro":             raw.get("intro", ""),
            "categories":        raw.get("categories") or [],
            "followers":         raw.get("followers") or raw.get("fans", 0),
            "followings":        raw.get("followings", 0),
            "phone":             raw.get("phone"),
            "email":             raw.get("email"),
            "website":           (raw.get("websites") or [None])[0],
            "address":           raw.get("address"),
            "category":          (raw.get("categories") or [""])[0],
            "creation_date":     raw.get("creationDate"),
            "business_hours":    raw.get("hours"),
            "rating_percent":    raw.get("ratingValue"),
            "rating_count":      raw.get("reviewCount"),
            "rating":            raw.get("ratingValue"),
            "ad_status":         raw.get("pageIsAdsTransparent"),
            "messenger":         raw.get("messenger"),
            # FIX: profile photo
            "profile_photo_url": fb_profile_photo,
            "stats": {
                "post_count":             raw.get("postCount", len(posts)),
                "posts_with_media":       sum(1 for p in posts if p["has_media"]),
                "media_ratio":            round(sum(1 for p in posts if p["has_media"]) / n, 2),
                "total_likes":            sum(p["likes"] for p in posts),
                "total_comments":         sum(p["comments_count"] for p in posts),
                "total_shares":           sum(p["shares"] for p in posts),
                "total_reactions":        sum(p["total_reactions"] for p in posts),
                "total_angry_reactions":  sum(p["reaction_angry"] for p in posts),
                "total_sad_reactions":    sum(p["reaction_sad"] for p in posts),
                "avg_likes_per_post":     round(sum(p["likes"] for p in posts) / n, 2),
                "avg_comments_per_post":  round(sum(p["comments_count"] for p in posts) / n, 2),
                "avg_shares_per_post":    round(sum(p["shares"] for p in posts) / n, 2),
                "avg_reactions_per_post": round(sum(p["total_reactions"] for p in posts) / n, 2),
            },
            "posts": posts,
        }

    if platform in ("ig_profile", "ig_post"):
        posts_src = raw.get("latestPosts") or ([raw] if platform == "ig_post" else [])

        def norm_ig_post(p):
            # FIX: extract all possible image URL fields from Instagram post
            image_url = (
                p.get("displayUrl") or
                p.get("display_url") or
                p.get("thumbnailUrl") or
                p.get("thumbnail_url") or
                p.get("imageUrl") or
                p.get("image_url") or
                # carousel: first sidecar image
                (((p.get("sidecarImages") or p.get("images") or [{}])[0]) or {}).get("displayUrl") or
                ""
            )
            video_url = (
                p.get("videoUrl") or
                p.get("video_url") or
                ""
            )
            return {
                "post_url":           p.get("url", ""),
                "page_name":          raw.get("username", ""),
                "date":               p.get("timestamp") or p.get("takenAt"),
                "text":               p.get("caption", ""),
                "likes":              p.get("likesCount", 0),
                "comments_count":     p.get("commentsCount", 0),
                "shares":             0,
                "reaction_like":      p.get("likesCount", 0),
                "reaction_love":      0, "reaction_haha": 0,
                "reaction_wow":       0, "reaction_sad":  0, "reaction_angry": 0,
                "total_reactions":    p.get("likesCount", 0),
                "has_media":          True,
                "media_count":        len(p.get("sidecarImages") or p.get("images") or []) or 1,
                "media_descriptions": [p.get("alt", "")],
                # FIX: image URL fields for _analyze_post_images
                "display_url":        image_url,
                "media_url":          video_url or image_url,
                "thumbnail_url":      p.get("thumbnailUrl") or image_url,
                "comment_list": mix_comments(
                    p.get("latestComments") or p.get("comments") or [],
                    "likesCount", "timestamp", limit=comment_limit,
                ),
            }

        posts = [norm_ig_post(p) for p in posts_src]
        n = len(posts) or 1

        # FIX: robust followers extraction with multiple fallbacks
        ig_followers = (
            raw.get("followersCount") or
            raw.get("followers") or
            (raw.get("edge_followed_by") or {}).get("count") or
            (raw.get("userInfo", {}) or {}).get("followersCount") or
            0
        )

        # FIX: profile photo extraction with multiple fallbacks
        ig_profile_photo = (
            raw.get("profilePicUrlHD") or
            raw.get("profilePicUrl") or
            raw.get("profile_pic_url_hd") or
            raw.get("profile_pic_url") or
            raw.get("profilePictureUrl") or
            raw.get("avatarUrl") or
            ""
        )

        return {
            "page_url":          raw.get("url") or raw.get("inputUrl", ""),
            "page_name":         raw.get("username", ""),
            "title":             raw.get("fullName") or raw.get("username", ""),
            "bio":               raw.get("biography", ""),
            "intro":             raw.get("biography", ""),
            "categories":        [raw.get("businessCategoryName")] if raw.get("businessCategoryName") else [],
            # FIX: robust followers
            "followers":         ig_followers,
            "followings":        raw.get("followsCount", 0),
            "phone":             raw.get("businessPhoneNumber"),
            "email":             raw.get("businessEmail"),
            "website":           raw.get("externalUrl"),
            "address":           (raw.get("businessAddress") or {}).get("street"),
            "category":          raw.get("businessCategoryName"),
            "creation_date":     None,
            "business_hours":    None,
            "rating_percent":    None, "rating_count": None, "rating": None,
            "ad_status":         None, "messenger":    None,
            # FIX: profile photo
            "profile_photo_url": ig_profile_photo,
            "stats": {
                "post_count":             raw.get("postsCount", len(posts)),
                "posts_with_media":       len(posts),
                "media_ratio":            1.0,
                "total_likes":            sum(p["likes"] for p in posts),
                "total_comments":         sum(p["comments_count"] for p in posts),
                "total_shares":           0,
                "total_reactions":        sum(p["likes"] for p in posts),
                "total_angry_reactions":  0, "total_sad_reactions": 0,
                "avg_likes_per_post":     round(sum(p["likes"] for p in posts) / n, 2),
                "avg_comments_per_post":  round(sum(p["comments_count"] for p in posts) / n, 2),
                "avg_shares_per_post":    0,
                "avg_reactions_per_post": round(sum(p["likes"] for p in posts) / n, 2),
            },
            "posts": posts,
        }

    if platform in ("tt_profile", "tt_post"):
        username   = raw.get("uniqueId") or raw.get("username", "")
        videos_src = raw.get("videos") or ([raw] if platform == "tt_post" else [])

        def _stat(v, key):
            return v.get(key) or (v.get("stats") or {}).get(key, 0)

        def norm_tt_post(v):
            vid_id = v.get("id") or v.get("videoId") or ""
            author_meta = v.get("authorMeta") or v.get("author") or {}

            # FIX: extract TikTok cover/thumbnail image URL
            cover_url = (
                v.get("covers", [None])[0] if v.get("covers") else None or
                v.get("coverUrl") or
                v.get("cover") or
                v.get("originCoverUrl") or
                v.get("dynamicCover") or
                author_meta.get("avatarThumb") or
                ""
            )
            video_url = (
                v.get("webVideoUrl") or
                v.get("videoUrl") or
                ""
            )

            return {
                "post_url":           f"https://www.tiktok.com/@{username}/video/{vid_id}",
                "page_name":          username,
                "date":               datetime.fromtimestamp(v["createTime"]).isoformat() if v.get("createTime") else None,
                "text":               v.get("desc") or v.get("text", ""),
                "likes":              _stat(v, "diggCount"),
                "comments_count":     _stat(v, "commentCount"),
                "shares":             _stat(v, "shareCount"),
                "reaction_like":      _stat(v, "diggCount"),
                "reaction_love":      0, "reaction_haha": 0,
                "reaction_wow":       0, "reaction_sad":  0, "reaction_angry": 0,
                "total_reactions":    _stat(v, "diggCount"),
                "has_media":          True,
                "media_count":        1,
                "media_descriptions": [v.get("desc", "")],
                # FIX: image/video URL fields for _analyze_post_images
                "display_url":        cover_url,
                "media_url":          video_url or cover_url,
                "thumbnail_url":      cover_url,
                "comment_list": mix_comments(
                    v.get("comments") if isinstance(v.get("comments"), list) else [],
                    "diggCount", "createTimeISO", limit=comment_limit,
                ),
            }

        posts = [norm_tt_post(v) for v in videos_src]
        n = len(posts) or 1

        # FIX: TikTok profile photo from author metadata
        first_video = videos_src[0] if videos_src else {}
        first_author = first_video.get("authorMeta") or first_video.get("author") or {}
        tt_profile_photo = (
            raw.get("profile_photo_url") or          # pre-set in scrape_tt_profile
            first_author.get("avatarLarger") or
            first_author.get("avatarMedium") or
            first_author.get("avatarThumb") or
            first_author.get("avatar") or
            ""
        )

        # FIX: robust TikTok follower extraction
        tt_followers = (
            raw.get("followerCount") or
            raw.get("fans") or
            first_author.get("fans") or
            first_author.get("followerCount") or
            0
        )

        return {
            "page_url":          f"https://www.tiktok.com/@{username}",
            "page_name":         username,
            "title":             raw.get("nickname") or username,
            "bio":               raw.get("signature") or raw.get("bio", ""),
            "intro":             raw.get("signature", ""),
            "categories":        [],
            # FIX: robust followers
            "followers":         tt_followers,
            "followings":        raw.get("followingCount") or raw.get("following", 0),
            "phone":             None, "email": None, "website": None, "address": None,
            "category":          "TikTok Creator",
            "creation_date":     None, "business_hours": None,
            "rating_percent":    None, "rating_count":   None, "rating": None,
            "ad_status":         None, "messenger":      None,
            # FIX: profile photo
            "profile_photo_url": tt_profile_photo,
            "stats": {
                "post_count":             raw.get("videoCount", len(posts)),
                "posts_with_media":       len(posts),
                "media_ratio":            1.0,
                "total_likes":            sum(p["likes"] for p in posts),
                "total_comments":         sum(p["comments_count"] for p in posts),
                "total_shares":           sum(p["shares"] for p in posts),
                "total_reactions":        sum(p["likes"] for p in posts),
                "total_angry_reactions":  0, "total_sad_reactions": 0,
                "avg_likes_per_post":     round(sum(p["likes"] for p in posts) / n, 2),
                "avg_comments_per_post":  round(sum(p["comments_count"] for p in posts) / n, 2),
                "avg_shares_per_post":    round(sum(p["shares"] for p in posts) / n, 2),
                "avg_reactions_per_post": round(sum(p["likes"] for p in posts) / n, 2),
            },
            "posts": posts,
        }

    return raw

# ── Apify usage ───────────────────────────────────────────────────────────────

async def get_apify_usage(api_key: str) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{APIFY_BASE}/users/me?token={api_key}")
        if r.status_code != 200:
            return None
        d     = r.json().get("data", {})
        plan  = d.get("plan", {})
        usage = d.get("monthlyUsage", {})
        limit = plan.get("monthlyUsageCreditsUsd", 5)
        used  = round(usage.get("totalCostUsd", 0), 4)
        return {
            "username":          d.get("username"),
            "email":             d.get("email"),
            "plan_name":         plan.get("name", "Free"),
            "monthly_limit_usd": limit,
            "used_usd":          used,
            "remaining_usd":     round(limit - used, 4),
            "usage_pct":         round(used / max(limit, 0.01) * 100, 1),
        }