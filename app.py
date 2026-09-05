import streamlit as st
from utils.db import init_db
from utils.mock_data import seed_mock_data, reset_mock_data, FOLLOWER_COUNTS, HANDLES

st.set_page_config(
    page_title="Creator Engine",
    page_icon="📊",
    layout="wide",
)

# --- one-time setup ---
init_db()
seed_mock_data()

PLATFORM_ICONS = {
    "instagram": "📷", "youtube": "▶️", "tiktok": "🎵", "linkedin": "💼", "facebook": "👍"
}

# --- sidebar: global controls ---
with st.sidebar:
    st.title("📊 Creator Engine")
    st.caption("Analytics & strategy console")

    st.divider()
    st.subheader("Connected Accounts")
    for platform, handle in HANDLES.items():
        icon = PLATFORM_ICONS.get(platform, "🔗")
        followers = FOLLOWER_COUNTS.get(platform, 0)
        st.markdown(f"🟢 {icon} **{platform.title()}** — {handle} *({followers:,} followers, mock data)*")
    st.caption(
        "This trial runs on generated sample data shaped like real "
        "engagement, revenue, and audience-growth patterns. Swap in real "
        "OAuth + API pulls later — see README for where that plugs in."
    )

    st.divider()
    if st.button("🔄 Reset & regenerate sample data"):
        reset_mock_data()
        st.success("Sample data regenerated.")
        st.rerun()

# --- page navigation ---
console_page = st.Page("pages/1_Console.py", title="Today's Console", icon="🏠", default=True)
calendar_page = st.Page("pages/2_Calendar.py", title="Weekly Calendar", icon="📅")
analytics_page = st.Page("pages/2_Post_Analytics.py", title="Post Analytics", icon="📈")
ideas_page = st.Page("pages/3_Idea_Generator.py", title="Idea Generator", icon="💡")
priority_page = st.Page("pages/4_Prioritization_Board.py", title="Prioritization Board", icon="📋")

pg = st.navigation([console_page, calendar_page, analytics_page, ideas_page, priority_page])
pg.run()
