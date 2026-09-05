"""
Generates realistic-looking historical post data so the analysis engine
has real patterns to discover. This stands in for the real OAuth + API
pulls (YouTube Data API, Instagram Graph API, TikTok, LinkedIn, Facebook)
until those are wired up.

Platforms + format segments (this is what the Post Analytics page splits
tabs by):
    instagram:  'photo'  (single image / carousel), 'reel'
    youtube:    'full_video' (long-form), 'short'
    tiktok:     'tiktok_video'  (TikTok is inherently short-form only)
    linkedin:   'linkedin_post' (text/image), 'linkedin_video'
    facebook:   'facebook_post', 'facebook_video'

Patterns baked in on purpose (so you can sanity-check the analysis
engine actually finds them, and so each platform has a DIFFERENT best
window — real creator audiences behave differently per platform):
    - Instagram: Tue/Thu 6-8pm outperforms other windows
    - YouTube:   Fri/Sat 7-9pm outperforms (weekend binge-watching)
    - TikTok:    daily 8-10pm outperforms
    - LinkedIn:  weekday (Tue-Thu) 8-10am outperforms (professional hours)
    - Facebook:  weekend 1-3pm outperforms
    - Shorter video (<=30s) retains watch % much better than long video
    - "tutorial" and "behind_the_scenes" topics outperform "vlog"

Financial modeling (illustrative, not real ad-rate data):
    - Each platform/format has a base CPM-ish rate representing ad
      revenue share and/or attributable sponsorship value per 1,000 views
    - ~8% of posts are randomly flagged as "sponsored" with a large
      revenue bonus, simulating brand deal posts
    - new_viewers = reach beyond the account's existing followers
    - new_followers = the subset of new_viewers who converted to a follow
"""

import random
from datetime import datetime, timedelta
from utils.db import get_connection

random.seed(42)

TOPICS = ["tutorial", "behind_the_scenes", "vlog", "product_review", "trend_response", "qna"]

PLATFORM_SEGMENTS = {
    "instagram": ["photo", "reel"],
    "youtube": ["full_video", "short"],
    "tiktok": ["tiktok_video"],
    "linkedin": ["linkedin_post", "linkedin_video"],
    "facebook": ["facebook_post", "facebook_video"],
}

# (good hours list, good weekdays list) -- weekday 0=Monday ... 6=Sunday
PLATFORM_GOOD_WINDOWS = {
    "instagram": ([18, 19], [1, 3]),         # Tue/Thu 6-8pm
    "youtube": ([19, 20], [4, 5]),           # Fri/Sat 7-9pm
    "tiktok": ([20, 21], [0, 1, 2, 3, 4, 5, 6]),  # any day, 8-10pm
    "linkedin": ([8, 9], [1, 2, 3]),         # Tue-Thu 8-10am
    "facebook": ([13, 14], [5, 6]),          # Sat/Sun 1-3pm
}

# base "CPM-ish" rate: estimated $ per 1,000 views, illustrative only
BASE_RATE_PER_1000_VIEWS = {
    "photo": 1.5,
    "reel": 2.5,
    "full_video": 6.0,      # YouTube mid-roll ads pay much better than shorts
    "short": 0.4,
    "tiktok_video": 0.5,
    "linkedin_post": 3.0,   # no native ad rev; modeled as attributable brand value
    "linkedin_video": 4.0,
    "facebook_post": 1.2,
    "facebook_video": 2.8,
}

FOLLOWER_COUNTS = {
    "instagram": 84200,
    "youtube": 61500,
    "tiktok": 45300,
    "linkedin": 12800,
    "facebook": 28900,
}

HANDLES = {
    "instagram": "@demo_creator",
    "youtube": "Demo Creator",
    "tiktok": "@demo_creator",
    "linkedin": "Demo Creator",
    "facebook": "Demo Creator Official",
}


def _seed_accounts(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM accounts")
    if cur.fetchone()["c"] > 0:
        return  # already seeded

    for platform, handle in HANDLES.items():
        cur.execute(
            "INSERT INTO accounts (platform, handle, connected, follower_count) VALUES (?, ?, ?, ?)",
            (platform, handle, 1, FOLLOWER_COUNTS[platform]),
        )


def _length_seconds_for(post_type):
    if post_type == "photo" or post_type in ("linkedin_post", "facebook_post"):
        return None
    if post_type == "reel":
        return random.choice([12, 18, 22, 28, 35, 45, 60, 75, 90])
    if post_type == "short":
        return random.choice([10, 15, 20, 28, 35, 45, 58])
    if post_type == "tiktok_video":
        return random.choice([10, 15, 20, 25, 32, 40, 55])
    if post_type == "full_video":
        return random.choice([300, 480, 600, 900, 1200, 1500])
    if post_type in ("linkedin_video", "facebook_video"):
        return random.choice([30, 60, 90, 150, 240])
    return None


def _generate_post(account_id, platform, days_ago):
    post_type = random.choice(PLATFORM_SEGMENTS[platform])
    topic = random.choice(TOPICS)

    posted_dt = datetime.now() - timedelta(days=days_ago)
    good_hours, good_weekdays = PLATFORM_GOOD_WINDOWS[platform]

    if random.random() < 0.35:
        # nudge into this platform's good window
        posted_dt = posted_dt.replace(hour=random.choice(good_hours), minute=random.randint(0, 59))
        target_weekday = random.choice(good_weekdays)
        weekday_shift = target_weekday - posted_dt.weekday()
        posted_dt = posted_dt + timedelta(days=weekday_shift)
        is_good_window = True
    else:
        posted_dt = posted_dt.replace(hour=random.randint(0, 23), minute=random.randint(0, 59))
        is_good_window = False

    duration = _length_seconds_for(post_type)
    is_video = duration is not None

    avg_watch_pct = None
    if is_video:
        base_retention = 85 if duration <= 30 else (55 if duration <= 60 else 35)
        avg_watch_pct = max(5, min(100, base_retention + random.gauss(0, 8)))

    caption_length = random.randint(20, 280)
    hashtag_count = random.randint(0, 15)

    base_views = random.randint(2000, 15000)
    multiplier = 1.0
    if is_good_window:
        multiplier *= 1.4
    if topic in ("tutorial", "behind_the_scenes"):
        multiplier *= 1.25
    if is_video and duration and duration <= 30:
        multiplier *= 1.3

    views = int(base_views * multiplier * random.uniform(0.8, 1.2))
    likes = int(views * random.uniform(0.04, 0.12))
    comments = int(views * random.uniform(0.002, 0.01))
    shares = int(views * random.uniform(0.001, 0.02))
    saves = int(views * random.uniform(0.002, 0.015))

    # --- financial modeling ---
    base_rate = BASE_RATE_PER_1000_VIEWS.get(post_type, 1.0)
    estimated_revenue = (views / 1000) * base_rate * random.uniform(0.7, 1.3)

    is_sponsored = random.random() < 0.08
    if is_sponsored:
        estimated_revenue += random.uniform(150, 1200)  # flat brand-deal bonus

    # --- audience growth modeling ---
    new_viewer_fraction = random.uniform(0.3, 0.7)
    new_viewers = int(views * new_viewer_fraction)
    conversion_rate = random.uniform(0.005, 0.02)
    if is_video and duration and duration <= 30:
        conversion_rate *= 1.5  # short punchy video converts viewers to followers better
    new_followers = int(new_viewers * conversion_rate)

    title = f"{topic.replace('_', ' ').title()} — {post_type.replace('_', ' ').title()}"
    if is_sponsored:
        title += " (Sponsored)"

    return {
        "account_id": account_id,
        "platform": platform,
        "post_type": post_type,
        "title": title,
        "topic": topic,
        "posted_at": posted_dt.isoformat(),
        "duration_seconds": duration,
        "caption_length": caption_length,
        "hashtag_count": hashtag_count,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "avg_watch_pct": avg_watch_pct,
        "estimated_revenue": round(estimated_revenue, 2),
        "new_viewers": new_viewers,
        "new_followers": new_followers,
    }


def seed_mock_data(num_posts_per_platform=70):
    """Populate the database with sample accounts + historical posts across
    all 5 platforms. Safe to call repeatedly — it only seeds if posts table
    is empty."""
    with get_connection() as conn:
        _seed_accounts(conn)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM posts")
        if cur.fetchone()["c"] > 0:
            return  # already have data

        cur.execute("SELECT id, platform FROM accounts")
        accounts = cur.fetchall()

        for acct in accounts:
            for i in range(num_posts_per_platform):
                days_ago = random.randint(1, 180)
                post = _generate_post(acct["id"], acct["platform"], days_ago)
                cur.execute("""
                    INSERT INTO posts (
                        account_id, platform, post_type, title, topic, posted_at,
                        duration_seconds, caption_length, hashtag_count,
                        views, likes, comments, shares, saves, avg_watch_pct,
                        estimated_revenue, new_viewers, new_followers
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post["account_id"], post["platform"], post["post_type"], post["title"],
                    post["topic"], post["posted_at"], post["duration_seconds"],
                    post["caption_length"], post["hashtag_count"], post["views"],
                    post["likes"], post["comments"], post["shares"], post["saves"],
                    post["avg_watch_pct"], post["estimated_revenue"], post["new_viewers"],
                    post["new_followers"],
                ))
        conn.commit()


def reset_mock_data():
    """Wipe and reseed — useful during development."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM posts")
        cur.execute("DELETE FROM accounts")
        cur.execute("DELETE FROM content_ideas")
        conn.commit()
    seed_mock_data()
