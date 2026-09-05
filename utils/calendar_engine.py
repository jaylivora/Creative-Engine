"""
Builds a suggested weekly posting schedule — the "what should my week
look like as a full-time creator" view.

For each connected platform, this pulls that platform's own best-performing
day/time windows (from utils.analysis.best_time_to_post) and pairs each
window with that platform's best-performing format + topic combo, then
attaches a predicted outcome (views, revenue, new followers) so every
calendar slot shows the reasoning behind it, not just a time.
"""

from utils.analysis import best_time_to_post, best_format_and_length, best_topics, predict_outcome
from utils.mock_data import PLATFORM_SEGMENTS

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def build_weekly_schedule(platforms=None, windows_per_platform=2):
    """Returns a dict keyed by weekday name -> list of suggested task dicts,
    each with platform, time window, format, topic, and predicted outcome.
    """
    if platforms is None:
        platforms = list(PLATFORM_SEGMENTS.keys())

    schedule = {day: [] for day in WEEKDAY_NAMES}

    for platform in platforms:
        times_df = best_time_to_post(platform)
        formats_df = best_format_and_length(platform)
        topics_df = best_topics(platform)

        if times_df.empty or formats_df.empty or topics_df.empty:
            continue

        top_windows = times_df.head(windows_per_platform)
        best_format_row = formats_df.iloc[0]
        best_topic_row = topics_df.iloc[0]

        for _, window in top_windows.iterrows():
            weekday_name = window["weekday_name"]
            weekday_num = int(window["weekday_order"])

            prediction = predict_outcome(
                platform=platform,
                post_type=best_format_row["post_type"],
                weekday=weekday_num,
                topic=best_topic_row["topic"],
            )

            task = {
                "platform": platform,
                "window_label": window["window_label"],
                "post_type": best_format_row["post_type"],
                "length_bucket": best_format_row["length_bucket"],
                "topic": best_topic_row["topic"],
                "historical_engagement": round(window["avg_engagement"], 2),
                "predicted_views": prediction["predicted_views"] if prediction else None,
                "predicted_revenue": prediction["predicted_revenue"] if prediction else None,
                "predicted_new_followers": prediction["predicted_new_followers"] if prediction else None,
                "confidence": prediction["confidence"] if prediction else "low (limited data)",
            }
            schedule[weekday_name].append(task)

    # sort each day's tasks by window label so the day reads chronologically
    for day in schedule:
        schedule[day] = sorted(schedule[day], key=lambda t: t["window_label"])

    return schedule


def weekly_totals(schedule):
    """Sum up predicted outcomes across the whole suggested week — this is
    the 'here's what a full week of following this schedule could yield'
    number for the top of the Calendar page."""
    total_views = 0
    total_revenue = 0.0
    total_new_followers = 0
    total_tasks = 0

    for day_tasks in schedule.values():
        for task in day_tasks:
            total_tasks += 1
            total_views += task["predicted_views"] or 0
            total_revenue += task["predicted_revenue"] or 0
            total_new_followers += task["predicted_new_followers"] or 0

    return {
        "total_tasks": total_tasks,
        "total_views": total_views,
        "total_revenue": round(total_revenue, 2),
        "total_new_followers": total_new_followers,
    }
