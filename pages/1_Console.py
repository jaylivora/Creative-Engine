import streamlit as st
from datetime import datetime
from utils.analysis import account_overview, top_recommendation_summary, best_time_to_post
from utils.db import fetch_df

st.title("Today's Console")
st.caption(f"{datetime.now().strftime('%A, %B %d')} — here's what your data says to do today.")

platform_filter = st.segmented_control(
    "Platform",
    options=["All", "instagram", "youtube", "tiktok", "linkedin", "facebook"],
    default="All", key="console_platform"
)
platform = None if platform_filter == "All" else platform_filter

# --- KPI row ---
overview = account_overview(platform)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Posts Tracked", overview["total_posts"])
c2.metric("Avg Engagement Rate", f"{overview['avg_engagement']}%")
c3.metric("Total Revenue (tracked)", f"${overview['total_revenue']:,.2f}")
c4.metric("New Followers Gained", f"{overview['total_new_followers']:,}")
c5.metric("30-Day Trend", f"{overview['trend_pct']}%",
          delta=f"{overview['trend_pct']}%" if overview['trend_pct'] != 0 else None)

st.divider()

# --- today's recommended action ---
st.subheader("🎯 Recommended for Today")

summary = top_recommendation_summary(platform)
today_weekday = datetime.now().strftime("%A")

if not summary:
    st.info("Not enough historical data yet — head to Post Analytics once more posts are tracked.")
else:
    best_window = summary.get("best_window")
    best_format = summary.get("best_format")
    best_topic = summary.get("best_topic")

    col1, col2 = st.columns([2, 1])
    with col1:
        if best_window:
            is_today = best_window["day"] == today_weekday
            highlight = "🔥 That's TODAY" if is_today else f"(next occurs: {best_window['day']})"
            st.markdown(f"""
**Post during your top-performing window: {best_window['day']} {best_window['window']}** {highlight}

- Historical engagement rate in this window: **{best_window['engagement']}%**
- Avg revenue in this window: **${best_window['revenue']:,.2f}** · Avg new followers: **{best_window['new_followers']}**
- Based on **{best_window['sample_size']}** past posts in this slot
            """)
        if best_format:
            watch_note = f", {best_format['watch_pct']}% avg watch retention" if best_format.get("watch_pct") else ""
            st.markdown(f"""
**Best format right now: {best_format['post_type'].replace('_', ' ').title()}, {best_format['length_bucket']}**

- Engagement rate: **{best_format['engagement']}%**{watch_note}
- Avg revenue per post: **${best_format['revenue']:,.2f}**
            """)
        if best_topic:
            st.markdown(f"""
**Best-performing topic: {best_topic['topic'].replace('_', ' ').title()}**

- Engagement rate: **{best_topic['engagement']}%** · Avg revenue: **${best_topic['revenue']:,.2f}**
            """)

    with col2:
        st.markdown("##### Why trust this?")
        st.caption(
            "Every number above is computed from this account's own post "
            "history — not generic best-practice advice. Check Post Analytics "
            "or the Weekly Calendar to see the underlying data."
        )

st.divider()

# --- this week's posting windows at a glance ---
st.subheader("📅 Your Best Windows This Week")
times_df = best_time_to_post(platform)
if times_df.empty:
    st.info("Not enough data to rank posting windows yet.")
else:
    top5 = times_df.head(5)[[
        "weekday_name", "window_label", "avg_engagement", "avg_revenue", "sample_size"
    ]]
    top5.columns = ["Day", "Time Window", "Avg Engagement %", "Avg Revenue ($)", "Sample Size"]
    st.dataframe(top5, use_container_width=True, hide_index=True)

st.caption("Want the full week mapped out across every platform? Check the **Weekly Calendar** page.")

st.divider()

# --- quick link to prioritized ideas ---
st.subheader("💡 Top Queued Content Idea")
ideas_df = fetch_df(
    "SELECT * FROM content_ideas WHERE status = 'suggested' ORDER BY priority_score DESC LIMIT 1"
)
if ideas_df.empty:
    st.info("No ideas generated yet — visit the Idea Generator page to create some.")
else:
    idea = ideas_df.iloc[0]
    st.markdown(f"**{idea['title']}**")
    st.caption(idea["rationale"])
    revenue_str = f" · Projected revenue: ${idea['predicted_revenue']:,.2f}" if idea['predicted_revenue'] else ""
    st.caption(f"Priority score: {idea['priority_score']} · Effort: {idea['effort_level']}{revenue_str}")
