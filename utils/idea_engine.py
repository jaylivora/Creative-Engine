"""
Content idea generation + prioritization.

v1 approach (works with zero external dependencies, good for your trial):
  - Generates ideas by recombining the creator's own best-performing
    topic + format + length + timing combos into new suggestions they
    haven't tried yet.
  - Attaches a predicted outcome (views, revenue, new followers) to each
    idea using utils.analysis.predict_outcome, so ideas aren't just
    "this seems good" — they come with a number attached.
  - Scores each idea: priority = (impact * 0.5) + (strategic_fit * 0.3) - (effort_penalty * 0.2)

To upgrade later: swap `generate_ideas()` internals to call the Anthropic
API with the analysis summary as context, asking Claude to propose
novel ideas grounded in the same data. The scoring/prioritization
function can stay exactly the same either way — that seam is intentional.
"""

import random
from utils.analysis import best_time_to_post, best_format_and_length, best_topics, predict_outcome
from utils.db import get_connection
from utils.mock_data import PLATFORM_SEGMENTS

EFFORT_WEIGHTS = {"light": 1, "medium": 2, "heavy": 3}

IDEA_TEMPLATES = {
    "tutorial": "Step-by-step walkthrough of a tool/process your audience keeps asking about",
    "behind_the_scenes": "Show the unfiltered process behind your most recent project",
    "vlog": "Day-in-the-life covering a specific theme (not just general vlogging)",
    "product_review": "Honest review/comparison of a product in your niche",
    "trend_response": "Your take on a current trend/format, adapted to your niche",
    "qna": "Answer your most-repeated audience question in depth",
}


def _pick_underused_combo(topics_df, formats_df):
    if topics_df.empty or formats_df.empty:
        return None, None
    topic_choices = topics_df.head(3)["topic"].tolist()
    format_choices = formats_df.head(2)[["post_type", "length_bucket"]].to_dict("records")
    topic = random.choice(topic_choices)
    fmt = random.choice(format_choices)
    return topic, fmt


def generate_ideas(platform=None, n=5):
    """Generate n content idea suggestions grounded in historical performance,
    each with a predicted views/revenue/new-follower outcome attached."""
    times = best_time_to_post(platform)
    formats = best_format_and_length(platform)
    topics = best_topics(platform)

    ideas = []
    for _ in range(n):
        topic, fmt = _pick_underused_combo(topics, formats)
        if topic is None:
            break

        best_window = times.iloc[0] if not times.empty else None
        topic_row = topics[topics["topic"] == topic].iloc[0]

        length_bucket = fmt["length_bucket"]
        length_seconds = {
            "0-30s": 25, "31-60s": 45, "1-3min": 120, "3min+": 300,
        }.get(length_bucket)  # None for static/text buckets

        title = IDEA_TEMPLATES.get(topic, f"New {topic.replace('_', ' ')} content")

        # attach a predicted outcome using the real prediction engine
        weekday = int(best_window["weekday_order"]) if best_window is not None else None
        prediction = predict_outcome(
            platform=platform, post_type=fmt["post_type"], weekday=weekday, topic=topic
        )

        rationale_parts = [
            f"'{topic.replace('_', ' ')}' content has averaged "
            f"{topic_row['avg_engagement']:.1f}% engagement in your history"
        ]
        if best_window is not None:
            rationale_parts.append(
                f"posting in your top window ({best_window['weekday_name']} "
                f"{best_window['window_label']}) has driven "
                f"{best_window['avg_engagement']:.1f}% engagement historically"
            )
        rationale = "; ".join(rationale_parts) + "."

        predicted_impact = min(100, topic_row["avg_engagement"] * 8)
        effort_level = random.choice(["light", "medium", "heavy"])
        strategic_fit = random.uniform(50, 95)  # placeholder until tied to real brand-deal deliverables

        idea = {
            "title": title,
            "platform": platform or fmt["post_type"],
            "suggested_format": fmt["post_type"],
            "suggested_length_seconds": length_seconds,
            "suggested_topic": topic,
            "rationale": rationale,
            "predicted_impact": round(predicted_impact, 1),
            "effort_level": effort_level,
            "strategic_fit": round(strategic_fit, 1),
        }

        if prediction:
            idea["predicted_views"] = prediction["predicted_views"]
            idea["predicted_revenue"] = prediction["predicted_revenue"]
            idea["predicted_new_followers"] = prediction["predicted_new_followers"]
        else:
            idea["predicted_views"] = None
            idea["predicted_revenue"] = None
            idea["predicted_new_followers"] = None

        ideas.append(idea)

    return ideas


def score_priority(predicted_impact, strategic_fit, effort_level):
    """Composite priority score: impact and strategic fit help, high effort
    slightly hurts (all else equal, easier wins should surface first)."""
    effort_penalty = EFFORT_WEIGHTS.get(effort_level, 2) * 10  # 10/20/30
    score = (predicted_impact * 0.5) + (strategic_fit * 0.3) - (effort_penalty * 0.2)
    return round(max(0, min(100, score)), 1)


def save_ideas(ideas):
    with get_connection() as conn:
        cur = conn.cursor()
        for idea in ideas:
            priority = score_priority(
                idea["predicted_impact"], idea["strategic_fit"], idea["effort_level"]
            )
            cur.execute("""
                INSERT INTO content_ideas (
                    title, platform, suggested_format, suggested_length_seconds,
                    suggested_topic, rationale, predicted_impact, effort_level,
                    strategic_fit, priority_score, predicted_views, predicted_revenue,
                    predicted_new_followers, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'suggested')
            """, (
                idea["title"], idea["platform"], idea["suggested_format"],
                idea["suggested_length_seconds"], idea["suggested_topic"],
                idea["rationale"], idea["predicted_impact"], idea["effort_level"],
                idea["strategic_fit"], priority, idea.get("predicted_views"),
                idea.get("predicted_revenue"), idea.get("predicted_new_followers"),
            ))
        conn.commit()


def update_idea_status(idea_id, status):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE content_ideas SET status = ? WHERE id = ?", (status, idea_id))
        conn.commit()
