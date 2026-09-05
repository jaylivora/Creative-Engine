import streamlit as st
import plotly.express as px
from utils.db import fetch_df
from utils.idea_engine import update_idea_status

st.title("Prioritization Board")
st.caption("All your content ideas, ranked and plotted by impact vs. effort.")

ideas_df = fetch_df("SELECT * FROM content_ideas ORDER BY priority_score DESC")

if ideas_df.empty:
    st.info("No ideas yet — generate some on the Idea Generator page first.")
    st.stop()

status_filter = st.multiselect(
    "Show statuses",
    options=["suggested", "planned", "posted", "dismissed"],
    default=["suggested", "planned"],
)
filtered = ideas_df[ideas_df["status"].isin(status_filter)]

# --- impact vs effort scatter ---
st.subheader("Impact vs. Effort")
effort_map = {"light": 1, "medium": 2, "heavy": 3}
if not filtered.empty:
    plot_df = filtered.copy()
    plot_df["effort_numeric"] = plot_df["effort_level"].map(effort_map)
    fig = px.scatter(
        plot_df, x="effort_numeric", y="predicted_impact",
        size="priority_score", color="priority_score",
        hover_data=["title"], color_continuous_scale="Blues",
        labels={"effort_numeric": "Effort", "predicted_impact": "Predicted Impact"},
    )
    fig.update_xaxes(tickvals=[1, 2, 3], ticktext=["Light", "Medium", "Heavy"])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bottom-right (high impact, low effort) = your quick wins.")
else:
    st.info("No ideas match the selected filters.")

st.divider()

# --- ranked list with status controls ---
st.subheader("Ranked Idea List")
for _, idea in filtered.sort_values("priority_score", ascending=False).iterrows():
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.markdown(f"**#{idea['id']} — {idea['title']}**")
            st.caption(idea["rationale"])
            st.caption(
                f"Format: {idea['suggested_format']} · Topic: {idea['suggested_topic']} · "
                f"Effort: {idea['effort_level']} · Status: `{idea['status']}`"
            )
        with c2:
            st.metric("Priority", idea["priority_score"])
        with c3:
            new_status = st.selectbox(
                "Update status", ["suggested", "planned", "posted", "dismissed"],
                index=["suggested", "planned", "posted", "dismissed"].index(idea["status"]),
                key=f"status_{idea['id']}", label_visibility="collapsed"
            )
            if new_status != idea["status"]:
                update_idea_status(idea["id"], new_status)
                st.rerun()
