import sys
import os
import base64

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
from backend.utils.icons import get_svg_icon

# 1. Page Configuration
st.set_page_config(
    page_title="National Missing Person Identification Portal",
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

# 2. Inject global custom CSS styling & top header navbar
inject_custom_css()

# 3. Handle Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "carousel_index" not in st.session_state:
    st.session_state.carousel_index = 0

# Base64 Brand Logo
logo_path = os.path.join(ROOT_DIR, "assets", "mpis_brand_logo.png")
logo_b64 = ""
if os.path.exists(logo_path):
    try:
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
    except Exception:
        pass

header_logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 48px; height: 48px; border-radius: 10px; box-shadow: 0 4px 12px rgba(37,99,235,0.25);" />' if logo_b64 else get_svg_icon('brand_logo', size=40)

# Fetch current metrics
case_repo = CaseRepository()
sighting_repo = SightingRepository()

total_cases = len(case_repo.get_all())
active_missing = len(case_repo.get_all({"status": "Missing"}))
total_found = len(case_repo.get_all({"status": "Found"}))
pending_sightings = len(sighting_repo.get_all({"status": "Pending"}))

# Hero Banner Carousel Section
carousel_slides = [
    {
        "title": "Dissemination of Information & Facial Intelligence",
        "subtitle": "Centralized AI-Driven Missing Person Identification & Spatial Sighting Tracking Portal",
        "badge1": ("🔍", "FACE MATCHING", "AI Feature Extraction"),
        "badge2": ("📍", "GIS SIGHTINGS", "Interactive Spatial Map"),
        "badge3": ("⚡", "REAL-TIME ALERTS", "Automated Case Matching"),
        "badge4": ("🛡️", "REUNIFICATION", f"{total_found} Reunited Cases")
    },
    {
        "title": "Citizen Sighting Portal & Law Enforcement Network",
        "subtitle": "Empowering Citizens and Officers to Rapidly Submit Sightings & Verify Bulletins",
        "badge1": ("🌐", "PUBLIC REPORTING", "Direct Sighting Submission"),
        "badge2": ("📹", "SURVEILLANCE", "Video Feed Extraction"),
        "badge3": ("⚖️", "MATCH REVIEW", "Officer Verification"),
        "badge4": ("🔔", "NOTIFICATION", "Instant Email Dispatch")
    }
]

curr_slide = carousel_slides[st.session_state.carousel_index % len(carousel_slides)]

# Hero Banner Carousel Section (100% Full Width Matching All Containers)
st.markdown("<span style='font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;'>NATIONAL PORTAL HIGHLIGHT</span>", unsafe_allow_html=True)

# Hidden button to trigger auto-transition of carousel slides
st.markdown("""
<style>
    .st-key-hidden_rerun {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

if st.button("hidden_rerun", key="hidden_rerun"):
    st.session_state.carousel_index = (st.session_state.carousel_index + 1) % len(carousel_slides)
    st.rerun()

# Auto-advance carousel timer script (5 seconds)
import streamlit.components.v1 as components
components.html(
    """
    <script>
        setTimeout(function() {
            const parentDoc = window.parent.document;
            const button = parentDoc.querySelector('.st-key-hidden_rerun button');
            if (button) {
                button.click();
            }
        }, 5000);
    </script>
    """,
    height=0,
    width=0
)


st.markdown(f"""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e1b4b 100%); border-radius: 20px; padding: 36px 40px; color: white; position: relative; overflow: hidden; box-shadow: 0 14px 40px rgba(15, 23, 42, 0.25); border: 1px solid #334155; width: 100%;">
<div style="text-align: center; max-width: 850px; margin: 0 auto 28px auto;">
<span style="background: rgba(59, 130, 246, 0.2); color: #93c5fd; padding: 6px 16px; border-radius: 9999px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; border: 1px solid rgba(147, 197, 253, 0.3);">Featured System Module</span>
<h1 style="color: #ffffff; font-size: 30px; font-weight: 800; margin-top: 12px; margin-bottom: 8px; font-family: 'Outfit', sans-serif;">{curr_slide['title']}</h1>
<p style="color: #cbd5e1; font-size: 15.5px; margin: 0; font-weight: 400;">{curr_slide['subtitle']}</p>
</div>

<div style="display: flex; justify-content: center; align-items: center; gap: 36px; flex-wrap: wrap; margin-top: 20px;">
<div style="text-align: center; width: 150px;">
<div style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; font-size: 32px; box-shadow: 0 8px 20px rgba(2, 132, 199, 0.4); border: 3px solid rgba(255,255,255,0.25);">
{curr_slide['badge1'][0]}
</div>
<div style="font-size: 13px; font-weight: 800; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px;">{curr_slide['badge1'][1]}</div>
<div style="font-size: 11.5px; color: #93c5fd;">{curr_slide['badge1'][2]}</div>
</div>

<div style="text-align: center; width: 150px;">
<div style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #be123c 0%, #9f1239 100%); margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; font-size: 32px; box-shadow: 0 8px 20px rgba(190, 18, 60, 0.4); border: 3px solid rgba(255,255,255,0.25);">
{curr_slide['badge2'][0]}
</div>
<div style="font-size: 13px; font-weight: 800; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px;">{curr_slide['badge2'][1]}</div>
<div style="font-size: 11.5px; color: #fda4af;">{curr_slide['badge2'][2]}</div>
</div>

<div style="text-align: center; width: 150px;">
<div style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #d97706 0%, #b45309 100%); margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; font-size: 32px; box-shadow: 0 8px 20px rgba(217, 119, 6, 0.4); border: 3px solid rgba(255,255,255,0.25);">
{curr_slide['badge3'][0]}
</div>
<div style="font-size: 13px; font-weight: 800; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px;">{curr_slide['badge3'][1]}</div>
<div style="font-size: 11.5px; color: #fde68a;">{curr_slide['badge3'][2]}</div>
</div>

<div style="text-align: center; width: 150px;">
<div style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #15803d 0%, #166534 100%); margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; font-size: 32px; box-shadow: 0 8px 20px rgba(21, 128, 61, 0.4); border: 3px solid rgba(255,255,255,0.25);">
{curr_slide['badge4'][0]}
</div>
<div style="font-size: 13px; font-weight: 800; color: #ffffff; text-transform: uppercase; letter-spacing: 0.5px;">{curr_slide['badge4'][1]}</div>
<div style="font-size: 11.5px; color: #86efac;">{curr_slide['badge4'][2]}</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# System Statistics Cards
st.markdown(f"""
<div style="display: flex; justify-content: center; align-items: center; gap: 20px; flex-wrap: wrap; margin-top: 20px; margin-bottom: 10px;">
    <div class="metric-card" style="border-left: 4px solid #ef4444; background: #ffffff; padding: 18px 22px; border-radius: 14px; box-shadow: 0 4px 16px rgba(15,23,42,0.05); flex: 1; max-width: 270px; min-width: 200px;">
        <span style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Active Missing Bulletins</span>
        <h2 style="margin: 4px 0 0 0; color: #ef4444; font-size: 34px; font-weight: 800;">{active_missing}</h2>
    </div>
    <div class="metric-card" style="border-left: 4px solid #10b981; background: #ffffff; padding: 18px 22px; border-radius: 14px; box-shadow: 0 4px 16px rgba(15,23,42,0.05); flex: 1; max-width: 270px; min-width: 200px;">
        <span style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Found & Reunited</span>
        <h2 style="margin: 4px 0 0 0; color: #10b981; font-size: 34px; font-weight: 800;">{total_found}</h2>
    </div>
    <div class="metric-card" style="border-left: 4px solid #f59e0b; background: #ffffff; padding: 18px 22px; border-radius: 14px; box-shadow: 0 4px 16px rgba(15,23,42,0.05); flex: 1; max-width: 270px; min-width: 200px;">
        <span style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Pending Sightings</span>
        <h2 style="margin: 4px 0 0 0; color: #f59e0b; font-size: 34px; font-weight: 800;">{pending_sightings}</h2>
    </div>
    <div class="metric-card" style="border-left: 4px solid #3b82f6; background: #ffffff; padding: 18px 22px; border-radius: 14px; box-shadow: 0 4px 16px rgba(15,23,42,0.05); flex: 1; max-width: 270px; min-width: 200px;">
        <span style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Total Cases Logged</span>
        <h2 style="margin: 4px 0 0 0; color: #3b82f6; font-size: 34px; font-weight: 800;">{total_cases}</h2>
    </div>
</div>
""", unsafe_allow_html=True)

# Comprehensive Project Explanation Section
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background: #ffffff; border-radius: 20px; padding: 36px 40px; border: 1px solid #e2e8f0; box-shadow: 0 8px 30px rgba(15, 23, 42, 0.05); margin-top: 10px;">
<div style="display: flex; align-items: center; gap: 14px; margin-bottom: 24px; border-bottom: 2px solid #f1f5f9; padding-bottom: 16px;">
<span style="font-size: 32px;">🏛️</span>
<div>
<h2 style="margin: 0; color: #1e3a8a; font-size: 24px; font-weight: 800; text-transform: uppercase; letter-spacing: -0.3px;">About National Missing Person Identification Portal (MPIS)</h2>
<p style="margin: 0; color: #64748b; font-size: 13px; font-weight: 600;">State-of-the-Art Public Safety Infrastructure & AI Facial Intelligence Platform</p>
</div>
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin-bottom: 28px;">
<div style="background: #f8fafc; padding: 24px; border-radius: 16px; border-left: 5px solid #2563eb;">
<h3 style="color: #1e3a8a; margin-top: 0; font-size: 18px; font-weight: 700;">🎯 Project Mission & Objective</h3>
<p style="color: #334155; font-size: 14.5px; line-height: 1.65; margin-bottom: 0;">
The <strong>Missing Person Identification System (MPIS)</strong> is a centralized national web application designed to bridge the gap between citizens, law enforcement agencies, and investigative officers. By leveraging computer vision, facial landmark detection, and spatial mapping, MPIS speeds up missing person identification and accelerates reunification.
</p>
</div>

<div style="background: #f8fafc; padding: 24px; border-radius: 16px; border-left: 5px solid #10b981;">
<h3 style="color: #065f46; margin-top: 0; font-size: 18px; font-weight: 700;">🤝 Citizen & Law Enforcement Synergy</h3>
<p style="color: #334155; font-size: 14.5px; line-height: 1.65; margin-bottom: 0;">
Public users can anonymously view active missing bulletins, report spotted individuals with GIS coordinates and photo evidence, and assist police teams in real-time. Officers verify incoming sightings, execute automated face-matching checks, and update official case statuses seamlessly.
</p>
</div>
</div>

<h3 style="color: #1e3a8a; font-size: 20px; font-weight: 800; margin-top: 32px; margin-bottom: 18px;">🛠️ Core System Architecture & Features</h3>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 30px;">
<div style="padding: 20px; background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 14px; box-shadow: 0 4px 14px rgba(15,23,42,0.03);">
<div style="font-size: 24px; margin-bottom: 8px;">🔬</div>
<strong style="color: #0f172a; font-size: 15px; display: block; margin-bottom: 4px;">1. AI Face Matching Engine</strong>
<span style="color: #475569; font-size: 12.5px; line-height: 1.5; display: block;">MediaPipe 468-point facial landmark mesh extraction and deep feature vector cosine similarity scoring for reliable face comparison.</span>
</div>

<div style="padding: 20px; background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 14px; box-shadow: 0 4px 14px rgba(15,23,42,0.03);">
<div style="font-size: 24px; margin-bottom: 8px;">📍</div>
<strong style="color: #0f172a; font-size: 15px; display: block; margin-bottom: 4px;">2. Interactive GIS Sighting Map</strong>
<span style="color: #475569; font-size: 12.5px; line-height: 1.5; display: block;">Interactive spatial mapping with radius search, location markers, missing case pins, and real-time spatial sighting heatmaps.</span>
</div>

<div style="padding: 20px; background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 14px; box-shadow: 0 4px 14px rgba(15,23,42,0.03);">
<div style="font-size: 24px; margin-bottom: 8px;">🌐</div>
<strong style="color: #0f172a; font-size: 15px; display: block; margin-bottom: 4px;">3. Public Sighting Portal</strong>
<span style="color: #475569; font-size: 12.5px; line-height: 1.5; display: block;">Public submission pipeline allowing citizens to submit sighting photos, location data, and observer notes directly for police review.</span>
</div>

<div style="padding: 20px; background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 14px; box-shadow: 0 4px 14px rgba(15,23,42,0.03);">
<div style="font-size: 24px; margin-bottom: 8px;">📹</div>
<strong style="color: #0f172a; font-size: 15px; display: block; margin-bottom: 4px;">4. Surveillance Video Feed Extraction</strong>
<span style="color: #475569; font-size: 12.5px; line-height: 1.5; display: block;">CCTV video frame sampling, face detection, and batch matching against registered missing case files.</span>
</div>
</div>

<h3 style="color: #1e3a8a; font-size: 20px; font-weight: 800; margin-top: 28px; margin-bottom: 18px;">🔄 End-to-End Operational Workflow</h3>

<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; background: #f8fafc; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0;">
<div style="text-align: center;">
<div style="width: 40px; height: 40px; border-radius: 50%; background: #2563eb; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; margin: 0 auto 10px auto;">1</div>
<strong style="color: #1e3a8a; font-size: 14px; display: block;">Case Registration</strong>
<span style="color: #64748b; font-size: 12px; display: block; margin-top: 4px;">Officers upload reference photos & case details into database.</span>
</div>
<div style="text-align: center;">
<div style="width: 40px; height: 40px; border-radius: 50%; background: #d97706; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; margin: 0 auto 10px auto;">2</div>
<strong style="color: #b45309; font-size: 14px; display: block;">Sighting Submission</strong>
<span style="color: #64748b; font-size: 12px; display: block; margin-top: 4px;">Citizens or CCTV feeds capture sightings with location tags.</span>
</div>
<div style="text-align: center;">
<div style="width: 40px; height: 40px; border-radius: 50%; background: #0284c7; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; margin: 0 auto 10px auto;">3</div>
<strong style="color: #0369a1; font-size: 14px; display: block;">AI Facial Matching</strong>
<span style="color: #64748b; font-size: 12px; display: block; margin-top: 4px;">Engine calculates similarity scores & generates officer alert.</span>
</div>
<div style="text-align: center;">
<div style="width: 40px; height: 40px; border-radius: 50%; background: #16a34a; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; margin: 0 auto 10px auto;">4</div>
<strong style="color: #15803d; font-size: 14px; display: block;">Verification & Recovery</strong>
<span style="color: #64748b; font-size: 12px; display: block; margin-top: 4px;">Officers verify match, ground response team dispatches, case closed.</span>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# Complete Project Contact Details, Helplines, and Support Emails Footer
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; border-radius: 20px; padding: 40px 48px; border: 1px solid #334155; box-shadow: 0 12px 36px rgba(15,23,42,0.3); margin-top: 36px; margin-bottom: 24px;">
<div style="display: grid; grid-template-columns: 2fr 1.5fr 1.5fr 1fr; gap: 36px; padding-bottom: 30px; border-bottom: 1px solid #334155;">

<div>
<h3 style="color: #60a5fa; font-size: 20px; font-weight: 800; margin-top: 0; margin-bottom: 12px; text-transform: uppercase;">National MPIS Portal</h3>
<p style="color: #94a3b8; font-size: 13px; line-height: 1.6; margin-bottom: 16px;">
Centralized Public Safety Infrastructure under the Ministry of Home Affairs Technology Wing. Dedicated to rapid identification, public sighting integration, and law enforcement support for missing person cases.
</p>
<div style="font-size: 12px; color: #cbd5e1;">
📍 <strong>Control Room:</strong> Block IV, CGO Complex, Lodhi Road, New Delhi - 110003
</div>
</div>

<div>
<h4 style="color: #f87171; font-size: 15px; font-weight: 700; margin-top: 0; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.5px;">🚨 Emergency Helplines</h4>
<ul style="list-style: none; padding: 0; margin: 0; font-size: 13px; color: #cbd5e1; line-height: 2;">
<li>📞 <strong>National Emergency Hotline:</strong> <span style="color: #ef4444; font-weight: 800;">112</span></li>
<li>📞 <strong>Missing Persons Helpline (Toll-Free):</strong> <span style="color: #60a5fa; font-weight: 700;">1800-111-365</span></li>
<li>📞 <strong>Child & Rescue Helpline:</strong> <span style="color: #f59e0b; font-weight: 700;">1098</span></li>
<li>📞 <strong>Women Helpline:</strong> <span style="color: #ec4899; font-weight: 700;">1091</span></li>
</ul>
</div>

<div>
<h4 style="color: #34d399; font-size: 15px; font-weight: 700; margin-top: 0; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.5px;">✉️ Support & Email Support</h4>
<ul style="list-style: none; padding: 0; margin: 0; font-size: 13px; color: #cbd5e1; line-height: 2;">
<li>✉️ <strong>Sighting Alerts:</strong> <a href="mailto:alerts@missingpersonportal.gov.in" style="color: #34d399; text-decoration: none;">alerts@missingpersonportal.gov.in</a></li>
<li>✉️ <strong>Public Support:</strong> <a href="mailto:contact@missingpersonportal.gov.in" style="color: #60a5fa; text-decoration: none;">contact@missingpersonportal.gov.in</a></li>
<li>✉️ <strong>Law Enforcement Tech Wing:</strong> <a href="mailto:support@missingtracker.com" style="color: #93c5fd; text-decoration: none;">support@missingtracker.com</a></li>
</ul>
</div>

<div>
<h4 style="color: #fbbf24; font-size: 15px; font-weight: 700; margin-top: 0; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.5px;">🔗 Quick Links</h4>
<ul style="list-style: none; padding: 0; margin: 0; font-size: 13px; color: #cbd5e1; line-height: 2;">
<li>🌐 <a href="pages/public_portal.py" style="color: #cbd5e1; text-decoration: none;">Public Portal</a></li>
<li>📁 <a href="pages/cases.py" style="color: #cbd5e1; text-decoration: none;">Case Directory</a></li>
<li>📍 <a href="pages/map.py" style="color: #cbd5e1; text-decoration: none;">Sighting Map</a></li>
<li>🔐 <a href="pages/login.py" style="color: #cbd5e1; text-decoration: none;">Officer Login</a></li>
</ul>
</div>

</div>

<div style="display: flex; align-items: center; justify-content: space-between; margin-top: 24px; font-size: 12px; color: #64748b;">
<div>© 2026 National Missing Person Identification Portal (MPIS). All Rights Reserved.</div>
<div>Security Standard ISO/IEC 27001 Certified • Ministry of Home Affairs</div>
</div>
</div>
""", unsafe_allow_html=True)

# Real-Time Toast Alerts
if st.session_state.authenticated and "simulated_alerts" in st.session_state and st.session_state.simulated_alerts:
    st.markdown("---", unsafe_allow_html=True)
    st.subheader("🔔 Active Real-Time Alerts")
    for alert in st.session_state.simulated_alerts[-3:]:
        st.toast(f"Match Alert: {alert['case_name']} spotted!", icon="⚠️")
        with st.expander(f"Alert: {alert['subject']} (Confidence: {alert['confidence'] * 100:.1f}%)"):
            st.code(alert['body'])
