import streamlit as st
from utils.calendar_engine import build_weekly_schedule, weekly_totals, WEEKDAY_NAMES

st.title("Suggested Weekly Calendar")
st.caption(
    "What your week could look like as a full-time creator — built from "
    "your own historical performance, per platform."
)

all_platforms = ["instagram", "youtube", "tiktok", "linkedin", "facebook"]
selected_platforms = st.multiselect(
    "Include platforms", options=all_platforms, default=all_platforms
)

if not selected_platforms:
    st.info("Select at least one platform to build a schedule.")
    st.stop()

schedule = build_weekly_schedule(platforms=selected_platforms)
totals = weekly_totals(schedule)

st.divider()

# --- weekly totals header ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Suggested Posts This Week", totals["total_tasks"])
c2.metric("Projected Views", f"{totals['total_views']:,}")
c3.metric("Projected Revenue", f"${totals['total_revenue']:,.2f}")
c4.metric("Projected New Followers", f"{totals['total_new_followers']:,}")

st.caption(
    "These totals assume you follow every suggested slot below. Projections come "
    "from utils/analysis.py's predict_outcome(), based on this account's own history."
)

st.divider()

PLATFORM_ICONS = {
    "instagram": "📷", "youtube": "▶️", "tiktok": "🎵", "linkedin": "💼", "facebook": "👍"
}

# --- weekly grid, tabbed by day ---
day_tabs = st.tabs(WEEKDAY_NAMES)

for day, tab in zip(WEEKDAY_NAMES, day_tabs):
    with tab:
        tasks = schedule[day]
        if not tasks:
            st.info("No suggested posts for this day — try including more platforms above.")
            continue

        for task in tasks:
            icon = PLATFORM_ICONS.get(task["platform"], "📌")
            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    length_str = ""
                    if task["length_bucket"] and "n/a" not in task["length_bucket"]:
                        length_str = f", {task['length_bucket']}"
                    st.markdown(
                        f"### {icon} {task['platform'].title()} — {task['window_label']}"
                    )
                    st.markdown(
                        f"**{task['post_type'].replace('_', ' ').title()}{length_str}** "
                        f"on **{task['topic'].replace('_', ' ').title()}**"
                    )
                    st.caption(
                        f"Historical engagement in this slot: {task['historical_engagement']}% · "
                        f"Confidence: {task['confidence']}"
                    )
                with col2:
                    if task["predicted_views"] is not None:
                        st.metric("Predicted Views", f"{task['predicted_views']:,}")
                        st.caption(
                            f"💰 ${task['predicted_revenue']:,.2f} · "
                            f"👥 +{task['predicted_new_followers']} followers"
                        )
                    else:
                        st.caption("Not enough data yet to predict outcome.")

st.divider()
st.caption(
    "This calendar suggests each platform's top 1-2 historically best windows. "
    "As you accumulate more real post history, these slots will sharpen and may "
    "shift — check back after connecting real accounts via OAuth."
)
