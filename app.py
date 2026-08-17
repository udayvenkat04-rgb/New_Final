import sys
import os

# Ensure backend and frontend directories are on sys.path for seamless imports
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
from database import check_connection
from repositories import CaseRepository, SightingRepository
from utils.helpers import inject_custom_css

# 1. Page Configuration
st.set_page_config(
    page_title="Missing Person Identification System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verify MongoDB availability
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning("Please ensure that MongoDB is running on your system and your `DATABASE_URL` is configured correctly in `.env`.")
    st.stop()

# 2. Inject global custom CSS styling
inject_custom_css()

# 3. Handle Session State Initialization & Role Routing
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None

# Automatic Role-Based Entry Router
if not st.session_state.authenticated:
    st.switch_page("pages/login.py")
else:
    user_role = st.session_state.user.get("role") if st.session_state.user else None
    if user_role == "admin":
        st.switch_page("pages/admin_dashboard.py")
    elif user_role == "officer":
        st.switch_page("pages/officer_dashboard.py")

import base64
from backend.utils.icons import get_svg_icon

logo_path = os.path.join(ROOT_DIR, "assets", "mpis_brand_logo.png")
logo_b64 = ""
if os.path.exists(logo_path):
    try:
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
    except Exception:
        pass

header_logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 56px; height: 56px; border-radius: 12px; box-shadow: 0 6px 20px rgba(79,70,229,0.3); border: 2px solid #818cf8;" />' if logo_b64 else get_svg_icon('brand_logo', size=42)

# Main Page Layout
st.markdown(f"""
<div style="text-align: center; margin-bottom: 8px;">
    <div style="display: inline-flex; align-items: center; justify-content: center; gap: 14px;">
        {header_logo_html}
        <h1 style="color: #3730a3; margin: 0; font-size: 34px; font-weight: 800; letter-spacing: -0.5px;">Missing Person Identification System</h1>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 16px; margin-top: 4px;'>Secure Centralized Portal for Law Enforcement & Public Search</p>", unsafe_allow_html=True)
st.markdown("---", unsafe_allow_html=True)

# Fetch current dashboard metrics via repositories
case_repo = CaseRepository()
sighting_repo = SightingRepository()

total_cases = len(case_repo.get_all())
active_missing = len(case_repo.get_all({"status": "Missing"}))
total_found = len(case_repo.get_all({"status": "Found"}))
pending_sightings = len(sighting_repo.get_all({"status": "Pending"}))

# Hero Section
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    ### Welcome to the Portal
    The **Missing Person Identification System** leverage advanced image processing, face recognition and spatial maps to expedite case registrations, log reported sightings, and assist officers in verifying matches.
    
    #### 🔑 Access Portals:
    1. **Public Portal**: Accessible via the sidebar without log in. Allows the general public to search registered missing cases, view stats, and report sightings.
    2. **Officer/Admin Dashboard**: Secure modules requiring authorization to add cases, verify sightings, perform face matching checks, and manage users.
    """)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Session Information Box
    if st.session_state.authenticated:
        user_info = st.session_state.user
        st.info(f"👤 **Logged in as:** `{user_info['username']}` | **Role:** `{user_info['role'].upper()}`")
        
        # Navigation shortcuts
        st.write("📂 **Quick Navigation:**")
        cols = st.columns(4)
        with cols[0]:
            if st.button("📁 View Case Directory", key="goto_cases"):
                st.switch_page("pages/cases.py")
        with cols[1]:
            if user_info and user_info.get("role") == "admin":
                if st.button("🔬 Face Match Engine", key="goto_matching"):
                    st.switch_page("pages/admin_face_matching.py")
        with cols[2]:
            if user_info and user_info.get("role") == "admin":
                if st.button("📹 Video Sightings", key="goto_video"):
                    st.switch_page("pages/video_sightings.py")
        with cols[3]:
            if st.button("📍 Sighting Map", key="goto_map"):
                st.switch_page("pages/map.py")
    else:
        st.warning("⚠️ **You are currently logged out.** Access to secure officer pages is restricted.")
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            if st.button("🚨 File Public Report", key="goto_public_portal"):
                st.switch_page("pages/public_portal.py")
        with pcol2:
            if st.button("🔐 Proceed to Login Page", key="goto_login"):
                st.switch_page("pages/login.py")

with col2:
    st.markdown("<h3 style='margin-bottom: 15px;'>📊 System Statistics</h3>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #ef4444;">
        <span style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">Active Missing Bulletins</span>
        <h2 style="margin: 0; color: #ef4444; font-size: 32px; font-weight: 700;">{active_missing}</h2>
    </div>
    <div class="metric-card" style="border-left-color: #10b981;">
        <span style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">Found & Reunited</span>
        <h2 style="margin: 0; color: #10b981; font-size: 32px; font-weight: 700;">{total_found}</h2>
    </div>
    <div class="metric-card" style="border-left-color: #f59e0b;">
        <span style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">Pending Sightings</span>
        <h2 style="margin: 0; color: #f59e0b; font-size: 32px; font-weight: 700;">{pending_sightings}</h2>
    </div>
    <div class="metric-card" style="border-left-color: #3b82f6;">
        <span style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">Total Cases Logged</span>
        <h2 style="margin: 0; color: #3b82f6; font-size: 32px; font-weight: 700;">{total_cases}</h2>
    </div>
    """, unsafe_allow_html=True)

# Footer Alert Panel
if st.session_state.authenticated and "simulated_alerts" in st.session_state and st.session_state.simulated_alerts:
    st.markdown("---", unsafe_allow_html=True)
    st.subheader("🔔 Active Real-Time Alerts")
    for alert in st.session_state.simulated_alerts[-3:]:
        st.toast(f"Match Alert: {alert['case_name']} spotted!", icon="⚠️")
        with st.expander(f"Alert: {alert['subject']} (Confidence: {alert['confidence'] * 100:.1f}%)"):
            st.code(alert['body'])
