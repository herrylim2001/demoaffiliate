"""
Affiliate & Bonus System - Streamlit Cloud Entry Point
"""

import streamlit as st
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from webapp.pages import dashboard, affiliates, commission, bonus, reports
from webapp.state import initialize_state

# Page configuration
st.set_page_config(
    page_title="Affiliate & Bonus System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-top: 0;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
initialize_state()

# Sidebar navigation
st.sidebar.markdown("## 💰 Affiliate System")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "👥 Affiliates", "💵 Commission", "🎁 Bonus", "📊 Reports"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Stats")
st.sidebar.metric("Total Affiliates", len(st.session_state.affiliate_service._affiliates))
st.sidebar.metric("Total Users", len(st.session_state.affiliate_service._users))
st.sidebar.metric("Active Bonuses", len([b for b in st.session_state.bonus_service._bonuses.values() if b.status.value in ['active', 'claimable']]))

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='text-align: center; color: #888; font-size: 0.8rem;'>
    <p>Affiliate & Bonus System</p>
    <p>Prototype v1.0</p>
</div>
""", unsafe_allow_html=True)

# Render selected page
if page == "🏠 Dashboard":
    dashboard.render()
elif page == "👥 Affiliates":
    affiliates.render()
elif page == "💵 Commission":
    commission.render()
elif page == "🎁 Bonus":
    bonus.render()
elif page == "📊 Reports":
    reports.render()
