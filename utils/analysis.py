"""
Analysis engine: turns raw historical post data into actionable patterns —
including financial and audience-growth outcomes, not just engagement %.

Everything here is computed FROM THE CREATOR'S OWN HISTORY — no generic
"best practices" advice. That's the whole point of the tool.
"""

import pandas as pd
import numpy as np
from utils.db import fetch_df

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _engagement_rate(row):
    """Simple composite engagement rate, normalized by views so we're not
    just rewarding raw reach. Weighted toward saves/shares since those are
    stronger 'this content mattered' signals than likes."""
    if row["views"] == 0:
        return 0.0
    weighted = (row["likes"] * 1.0 + row["comments"] * 2.0 +
                row["shares"] * 3.0 + row["saves"] * 3.0)
    return (weighted / row["views"]) * 100


def load_posts(platform=None, post_type=None):
    query = "SELECT * FROM posts"
    clauses = []
    params = []
    if platform:
        clauses.append("platform = ?")
        params.append(platform)
    if post_type:
        clauses.append("post_type = ?")
        params.append(post_type)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    df = fetch_df(query, tuple(params))
    if df.empty:
        return df
    df["posted_at"] = pd.to_datetime(df["posted_at"])
    df["weekday"] = df["posted_at"].dt.dayofweek  # 0=Mon
    df["weekday_name"] = df["weekday"].apply(lambda x: WEEKDAY_NAMES[x])
    df["hour"] = df["posted_at"].dt.hour
    df["engagement_rate"] = df.apply(_engagement_rate, axis=1)

    for col in ["estimated_revenue", "new_viewers", "new_followers"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    return df


def best_time_to_post(platform=None, post_type=None, min_samples=3):
    """Group by weekday + hour-bucket, return engagement/financial/audience
    ranked windows. Only surfaces windows with enough data points to mean
    something — this guards against 'you posted once at 3am and it did
    fine' noise."""
    df = load_posts(platform, post_type)
    if df.empty:
        return pd.DataFrame()

    df["hour_bucket"] = (df["hour"] // 3) * 3
    df["window_label"] = df["hour_bucket"].apply(lambda h: f"{h:02d}:00–{(h+3)%24:02d}:00")

    grouped = df.groupby(["weekday_name", "window_label", "weekday"]).agg(
        avg_engagement=("engagement_rate", "mean"),
        avg_views=("views", "mean"),
        avg_revenue=("estimated_revenue", "mean"),
        avg_new_viewers=("new_viewers", "mean"),
        avg_new_followers=("new_followers", "mean"),
        sample_size=("id", "count"),
    ).reset_index()

    grouped = grouped[grouped["sample_size"] >= min_samples]
    grouped = grouped.sort_values("avg_engagement", ascending=False)
    grouped["weekday_order"] = grouped["weekday"]
    return grouped.drop(columns=["weekday"])


def best_format_and_length(platform=None, post_type=None):
    """Correlate post_type + duration bucket against engagement, watch
    retention, revenue, and audience growth."""
    df = load_posts(platform, post_type)
    if df.empty:
        return pd.DataFrame()

    def length_bucket(row):
        if pd.isna(row["duration_seconds"]):
            return "n/a (static/text)"
        d = row["duration_seconds"]
        if d <= 30:
            return "0-30s"
        elif d <= 60:
            return "31-60s"
        elif d <= 180:
            return "1-3min"
        else:
            return "3min+"

    df["length_bucket"] = df.apply(length_bucket, axis=1)

    grouped = df.groupby(["post_type", "length_bucket"]).agg(
        avg_engagement=("engagement_rate", "mean"),
        avg_watch_pct=("avg_watch_pct", "mean"),
        avg_views=("views", "mean"),
        avg_revenue=("estimated_revenue", "mean"),
        avg_new_viewers=("new_viewers", "mean"),
        avg_new_followers=("new_followers", "mean"),
        sample_size=("id", "count"),
    ).reset_index()

    grouped = grouped[grouped["sample_size"] >= 3]
    return grouped.sort_values("avg_engagement", ascending=False)


def best_topics(platform=None, post_type=None):
    df = load_posts(platform, post_type)
    if df.empty:
        return pd.DataFrame()

    grouped = df.groupby("topic").agg(
        avg_engagement=("engagement_rate", "mean"),
        avg_views=("views", "mean"),
        avg_revenue=("estimated_revenue", "mean"),
        avg_new_viewers=("new_viewers", "mean"),
        avg_new_followers=("new_followers", "mean"),
        sample_size=("id", "count"),
    ).reset_index()
    grouped = grouped[grouped["sample_size"] >= 3]
    return grouped.sort_values("avg_engagement", ascending=False)


def account_overview(platform=None, post_type=None):
    """Top-line KPI numbers for dashboard header cards, including
    financial and audience-growth totals."""
    df = load_posts(platform, post_type)
    if df.empty:
        return {
            "total_posts": 0, "avg_engagement": 0, "avg_views": 0,
            "trend_pct": 0, "total_revenue": 0, "total_new_followers": 0,
            "total_new_viewers": 0,
        }

    total_posts = len(df)
    avg_engagement = df["engagement_rate"].mean()
    avg_views = df["views"].mean()
    total_revenue = df["estimated_revenue"].sum()
    total_new_followers = df["new_followers"].sum()
    total_new_viewers = df["new_viewers"].sum()

    cutoff_recent = df["posted_at"].max() - pd.Timedelta(days=30)
    cutoff_prior = cutoff_recent - pd.Timedelta(days=30)
    recent = df[df["posted_at"] >= cutoff_recent]["engagement_rate"].mean()
    prior = df[(df["posted_at"] < cutoff_recent) & (df["posted_at"] >= cutoff_prior)]["engagement_rate"].mean()

    trend_pct = 0
    if prior and not np.isnan(prior) and prior > 0:
        trend_pct = ((recent - prior) / prior) * 100

    return {
        "total_posts": total_posts,
        "avg_engagement": round(avg_engagement, 2),
        "avg_views": int(avg_views),
        "trend_pct": round(trend_pct, 1) if not np.isnan(trend_pct) else 0,
        "total_revenue": round(total_revenue, 2),
        "total_new_followers": int(total_new_followers),
        "total_new_viewers": int(total_new_viewers),
    }


def top_recommendation_summary(platform=None, post_type=None):
    """Produces the plain-language 'why' behind the top suggestion —
    used on the Console page so recommendations aren't a black box."""
    times = best_time_to_post(platform, post_type)
    formats = best_format_and_length(platform, post_type)
    topics = best_topics(platform, post_type)

    summary = {}
    if not times.empty:
        top = times.iloc[0]
        summary["best_window"] = {
            "day": top["weekday_name"],
            "window": top["window_label"],
            "engagement": round(top["avg_engagement"], 2),
            "revenue": round(top["avg_revenue"], 2),
            "new_viewers": round(top["avg_new_viewers"]),
            "new_followers": round(top["avg_new_followers"]),
            "sample_size": int(top["sample_size"]),
        }
    if not formats.empty:
        top = formats.iloc[0]
        summary["best_format"] = {
            "post_type": top["post_type"],
            "length_bucket": top["length_bucket"],
            "engagement": round(top["avg_engagement"], 2),
            "watch_pct": round(top["avg_watch_pct"], 1) if not pd.isna(top["avg_watch_pct"]) else None,
            "revenue": round(top["avg_revenue"], 2),
        }
    if not topics.empty:
        top = topics.iloc[0]
        summary["best_topic"] = {
            "topic": top["topic"],
            "engagement": round(top["avg_engagement"], 2),
            "revenue": round(top["avg_revenue"], 2),
        }
    return summary


def predict_outcome(platform, post_type, weekday=None, hour=None, topic=None):
    """Given a proposed platform/format(/day/hour/topic), predict expected
    views, revenue, new viewers, and new followers based on historical
    posts matching similar conditions. Falls back to broader averages
    when there isn't enough narrow-match data, so it never just errors out.

    Returns a dict with the prediction plus a `confidence` label so the UI
    can be honest about how much history backs the number up.
    """
    df = load_posts(platform, post_type)
    if df.empty:
        return None

    subset = df.copy()
    if weekday is not None:
        subset = subset[subset["weekday"] == weekday]
    if hour is not None:
        subset = subset[(subset["hour"] >= hour - 1) & (subset["hour"] <= hour + 1)]
    if topic is not None:
        subset = subset[subset["topic"] == topic]

    confidence = "high"
    if len(subset) < 5:
        # not enough narrow matches — fall back to platform+format only
        subset = df.copy()
        confidence = "low (based on overall platform/format average, not this exact combo)"
    elif len(subset) < 10:
        confidence = "medium"

    if subset.empty:
        return None

    return {
        "predicted_views": round(subset["views"].mean()),
        "predicted_engagement": round(subset["engagement_rate"].mean(), 2),
        "predicted_revenue": round(subset["estimated_revenue"].mean(), 2),
        "predicted_new_viewers": round(subset["new_viewers"].mean()),
        "predicted_new_followers": round(subset["new_followers"].mean()),
        "sample_size": len(subset),
        "confidence": confidence,
    }
