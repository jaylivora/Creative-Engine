import streamlit as st
import plotly.express as px
from utils.analysis import load_posts, best_time_to_post, best_format_and_length, best_topics
from utils.mock_data import PLATFORM_SEGMENTS

st.title("Post Analytics")
st.caption("Your historical performance, broken down by time, format, topic — and what it's worth.")

SEGMENT_LABELS = {
    "photo": "📷 Photos", "reel": "🎬 Reels",
    "full_video": "🎥 Full-Length Videos", "short": "⚡ Shorts",
    "tiktok_video": "🎵 TikTok Videos",
    "linkedin_post": "📝 Posts", "linkedin_video": "🎬 Video",
    "facebook_post": "📝 Posts", "facebook_video": "🎬 Video",
}

platform_filter = st.segmented_control(
    "Platform",
    options=["All", "instagram", "youtube", "tiktok", "linkedin", "facebook"],
    default="All", key="analytics_platform"
)
platform = None if platform_filter == "All" else platform_filter

# --- segment selector (only shows when a platform with multiple formats is picked) ---
post_type = None
if platform and len(PLATFORM_SEGMENTS.get(platform, [])) > 1:
    segment_options = ["All"] + PLATFORM_SEGMENTS[platform]
    segment_choice = st.radio(
        "Format segment", options=segment_options,
        format_func=lambda s: "All Formats" if s == "All" else SEGMENT_LABELS.get(s, s),
        horizontal=True, key="analytics_segment"
    )
    post_type = None if segment_choice == "All" else segment_choice

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Best Time to Post", "Format & Length", "Topics", "Financials & Audience", "Raw Post History"]
)

with tab1:
    st.subheader("Engagement by Day & Time Window")
    times_df = best_time_to_post(platform, post_type)
    if times_df.empty:
        st.info("Not enough data yet.")
    else:
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pivot = times_df.pivot_table(
            index="weekday_name", columns="window_label", values="avg_engagement"
        ).reindex(weekday_order)
        fig = px.imshow(
            pivot,
            labels=dict(x="Time Window", y="Day", color="Avg Engagement %"),
            color_continuous_scale="Blues", aspect="auto",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Darker = higher historical engagement rate. Blank cells = not enough sample data.")

        display = times_df[[
            "weekday_name", "window_label", "avg_engagement", "avg_views",
            "avg_revenue", "avg_new_followers", "sample_size"
        ]].rename(columns={
            "weekday_name": "Day", "window_label": "Window",
            "avg_engagement": "Avg Engagement %", "avg_views": "Avg Views",
            "avg_revenue": "Avg Revenue ($)", "avg_new_followers": "Avg New Followers",
            "sample_size": "N"
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Engagement by Format & Length")
    formats_df = best_format_and_length(platform, post_type)
    if formats_df.empty:
        st.info("Not enough data yet.")
    else:
        formats_df["label"] = formats_df["post_type"] + " (" + formats_df["length_bucket"] + ")"
        fig = px.bar(
            formats_df.sort_values("avg_engagement"),
            x="avg_engagement", y="label", orientation="h",
            labels={"avg_engagement": "Avg Engagement %", "label": "Format / Length"},
            color="avg_engagement", color_continuous_scale="Blues",
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        if formats_df["avg_watch_pct"].notna().any():
            st.subheader("Watch Retention by Length (video only)")
            video_df = formats_df.dropna(subset=["avg_watch_pct"])
            fig2 = px.bar(
                video_df.sort_values("avg_watch_pct"),
                x="avg_watch_pct", y="label", orientation="h",
                labels={"avg_watch_pct": "Avg Watch %", "label": "Format / Length"},
                color="avg_watch_pct", color_continuous_scale="Greens",
            )
            fig2.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("Engagement by Content Topic")
    topics_df = best_topics(platform, post_type)
    if topics_df.empty:
        st.info("Not enough data yet.")
    else:
        fig = px.bar(
            topics_df.sort_values("avg_engagement"),
            x="avg_engagement", y="topic", orientation="h",
            labels={"avg_engagement": "Avg Engagement %", "topic": "Topic"},
            color="avg_engagement", color_continuous_scale="Purples",
        )
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("What Your Content Is Actually Worth")
    st.caption(
        "Estimated revenue = ad revenue share + attributable sponsorship value. "
        "New viewers/followers = reach and growth beyond your existing audience."
    )
    formats_df = best_format_and_length(platform, post_type)
    if formats_df.empty:
        st.info("Not enough data yet.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                formats_df.sort_values("avg_revenue"),
                x="avg_revenue", y="post_type", orientation="h",
                labels={"avg_revenue": "Avg Revenue per Post ($)", "post_type": "Format"},
                color="avg_revenue", color_continuous_scale="Greens",
            )
            fig.update_layout(height=350, showlegend=False, title="Revenue by Format")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.bar(
                formats_df.sort_values("avg_new_followers"),
                x="avg_new_followers", y="post_type", orientation="h",
                labels={"avg_new_followers": "Avg New Followers per Post", "post_type": "Format"},
                color="avg_new_followers", color_continuous_scale="Oranges",
            )
            fig2.update_layout(height=350, showlegend=False, title="Audience Growth by Format")
            st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(
            formats_df[["post_type", "length_bucket", "avg_revenue", "avg_new_viewers", "avg_new_followers", "sample_size"]]
            .rename(columns={
                "post_type": "Format", "length_bucket": "Length",
                "avg_revenue": "Avg Revenue ($)", "avg_new_viewers": "Avg New Viewers",
                "avg_new_followers": "Avg New Followers", "sample_size": "N"
            }),
            use_container_width=True, hide_index=True
        )

with tab5:
    st.subheader("All Tracked Posts")
    posts_df = load_posts(platform, post_type)
    if posts_df.empty:
        st.info("No posts tracked yet.")
    else:
        display_cols = [
            "posted_at", "platform", "post_type", "topic", "duration_seconds",
            "views", "likes", "comments", "shares", "saves", "avg_watch_pct",
            "engagement_rate", "estimated_revenue", "new_viewers", "new_followers"
        ]
        st.dataframe(
            posts_df[display_cols].sort_values("posted_at", ascending=False),
            use_container_width=True, hide_index=True
        )
