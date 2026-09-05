import streamlit as st
from utils.idea_engine import generate_ideas, save_ideas
from utils.db import fetch_df

st.title("Content Idea Generator")
st.caption("New ideas, generated from what's actually worked on this account before — with projected outcomes attached.")

platform_filter = st.segmented_control(
    "Platform",
    options=["instagram", "youtube", "tiktok", "linkedin", "facebook"],
    default="instagram", key="ideas_platform"
)

col1, col2 = st.columns([1, 3])
with col1:
    num_ideas = st.slider("How many ideas?", 1, 10, 5)
    if st.button("✨ Generate New Ideas", type="primary"):
        new_ideas = generate_ideas(platform=platform_filter, n=num_ideas)
        if new_ideas:
            save_ideas(new_ideas)
            st.success(f"Generated {len(new_ideas)} new ideas — see below or check the Prioritization Board.")
        else:
            st.warning("Not enough historical data yet to generate grounded ideas.")

st.divider()

st.subheader("Recently Generated Ideas")
ideas_df = fetch_df(
    "SELECT * FROM content_ideas WHERE status = 'suggested' ORDER BY created_at DESC LIMIT 20"
)

if ideas_df.empty:
    st.info("No ideas yet — generate some above.")
else:
    for _, idea in ideas_df.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{idea['title']}**")
                st.caption(idea["rationale"])
                length_str = f", ~{idea['suggested_length_seconds']}s" if idea["suggested_length_seconds"] else ""
                st.caption(
                    f"Format: {idea['suggested_format']}{length_str} · "
                    f"Topic: {idea['suggested_topic']} · Platform: {idea['platform']}"
                )
                if idea["predicted_views"]:
                    st.caption(
                        f"📊 Projected: **{int(idea['predicted_views']):,} views** · "
                        f"**${idea['predicted_revenue']:,.2f}** · "
                        f"**+{int(idea['predicted_new_followers'])} followers**"
                    )
            with c2:
                st.metric("Priority Score", idea["priority_score"])
                st.caption(f"Impact: {idea['predicted_impact']} · Effort: {idea['effort_level']}")
