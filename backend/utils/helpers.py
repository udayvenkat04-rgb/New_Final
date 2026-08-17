import streamlit as st
from backend.utils.file_utils import save_uploaded_file, load_image_safely, get_placeholder_image


def inject_custom_css():
    """Injects a modern, premium 100% Light Theme styling in Streamlit."""
    st.markdown("""
    <style>
        /* Import Outfit Google Font */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
        
        /* Global font & light theme background */
        html, body, [class*="css"], .stMarkdown {
            font-family: 'Outfit', sans-serif;
            color: #0f172a;
        }

        .stApp {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
        }

        header[data-testid="stHeader"] {
            background-color: transparent !important;
        }

        /* Constrain block container width & center alignment */
        .main .block-container {
            max-width: 1240px !important;
            padding-top: 25px !important;
            padding-bottom: 40px !important;
        }

        /* Donezo-style Outer Dashboard White Card Container */
        .dashboard-outer-card {
            background: #ffffff !important;
            border-radius: 28px !important;
            padding: 32px 32px 36px 32px !important;
            box-shadow: 0 20px 60px rgba(15, 23, 42, 0.07), 0 4px 16px rgba(15, 23, 42, 0.03) !important;
            border: 1px solid #e2e8f0 !important;
            margin-bottom: 24px !important;
        }

        /* Donezo-style Metric Cards with Interactive Blue Theme Hover */
        .donezo-hero-card {
            background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
            border-radius: 20px !important;
            padding: 22px !important;
            color: #ffffff !important;
            box-shadow: 0 10px 28px rgba(79, 70, 229, 0.35) !important;
            border: none !important;
            position: relative;
            margin-bottom: 20px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
        }
        .donezo-hero-card:hover {
            transform: translateY(-5px) scale(1.02) !important;
            box-shadow: 0 16px 40px rgba(79, 70, 229, 0.5) !important;
        }

        .donezo-metric-card {
            background: #ffffff !important;
            border-radius: 20px !important;
            padding: 22px !important;
            border: 1.5px solid #cbd5e1 !important;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 20px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            position: relative;
            cursor: pointer !important;
        }
        .donezo-metric-card:hover {
            transform: translateY(-5px) scale(1.02) !important;
            background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 14px 36px rgba(79, 70, 229, 0.45) !important;
            border-color: transparent !important;
        }
        .donezo-metric-card:hover * {
            color: #ffffff !important;
            opacity: 1 !important;
        }
        .donezo-metric-card:hover .arrow-icon-circle {
            background: rgba(255, 255, 255, 0.25) !important;
            border-color: transparent !important;
            color: #ffffff !important;
        }

        /* Light Cards */
        .glass-card {
            background: #ffffff !important;
            border-radius: 16px !important;
            padding: 20px 24px !important;
            border: 1.5px solid #cbd5e1 !important;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05) !important;
            margin-bottom: 16px !important;
            transition: all 0.25s ease !important;
        }
        .glass-card:hover {
            transform: translateY(-2px) !important;
            border-color: #4f46e5 !important;
            box-shadow: 0 8px 24px rgba(79, 70, 229, 0.12) !important;
        }

        /* Styled Badges */
        .badge {
            padding: 5px 12px !important;
            border-radius: 9999px !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            display: inline-block !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }
        .badge-missing {
            background-color: #ffe4e6 !important;
            color: #e11d48 !important;
            border: 1.5px solid #fda4af !important;
        }
        .badge-found {
            background-color: #dcfce7 !important;
            color: #15803d !important;
            border: 1.5px solid #86efac !important;
        }
        .badge-pending {
            background-color: #fef3c7 !important;
            color: #b45309 !important;
            border: 1.5px solid #fcd34d !important;
        }
        .badge-verified {
            background-color: #dbeafe !important;
            color: #1d4ed8 !important;
            border: 1.5px solid #93c5fd !important;
        }

        /* Card Image container styling */
        .card-img-container {
            width: 100%;
            height: 200px;
            border-radius: 8px;
            overflow: hidden;
            background-color: #f1f5f9;
            border: 1px solid #e2e8f0;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .card-img-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        /* Metric Dashboard Cards */
        .metric-card {
            background: #ffffff;
            border-left: 4px solid #4f46e5;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 15px;
            border-top: 1px solid #e2e8f0;
            border-right: 1px solid #e2e8f0;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
            transition: all 0.25s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(79, 70, 229, 0.12);
            border-color: #c7d2fe;
        }
        
        /* Light Sidebar styling - PYDAH Reference Design */
        section[data-testid="stSidebar"] {
            background-color: #f8fafc !important;
            border-right: 1px solid #e2e8f0 !important;
            width: 310px !important;
            min-width: 310px !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            padding: 0 !important;
        }
        /* Forcefully collapse top Streamlit header, toolbar, and decoration bar */
        header[data-testid="stHeader"],
        div[data-testid="stHeader"],
        div[data-testid="stDecoration"],
        div[data-testid="stToolbar"] {
            display: none !important;
            height: 0px !important;
            min-height: 0px !important;
            padding: 0px !important;
            margin: 0px !important;
            visibility: hidden !important;
        }

        /* Main Page Viewport - 100% Full Width Span (Left to Right Edge) & Top Edge Placement */
        div[data-testid="stAppViewContainer"],
        section.main {
            padding-top: 0px !important;
        }

        .main .block-container,
        div[data-testid="stBlockContainer"] {
            max-width: 100% !important;
            width: 100% !important;
            padding-top: 1rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            margin-top: 0px !important;
            margin-left: 0px !important;
            margin-right: 0px !important;
        }

        .main .element-container:first-child,
        .main [data-testid="stVerticalBlock"] > div:first-child {
            margin-top: 0px !important;
            padding-top: 0px !important;
        }

        /* Sidebar Brand Header White Text Enforcement */
        .sidebar-brand-header * {
            color: #ffffff !important;
        }
        /* Completely hide default auto-generated Streamlit multi-page sidebar navigation */
        div[data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* 100% Full-Width Span Page Link Cards in Sidebar (PYDAH Pill Cards) */
        div[data-testid="stPageLink"] {
            width: 100% !important;
        }
        div[data-testid="stPageLink"] a {
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
            box-sizing: border-box !important;
            padding: 9px 14px !important;
            border-radius: 12px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #334155 !important;
            background-color: transparent !important;
            border: none !important;
            margin-bottom: 2px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stPageLink"] a:hover {
            background-color: #f1f5f9 !important;
            color: #4f46e5 !important;
        }
        /* Active Page Link: Solid Blue Pill Fill like PYDAH reference */
        div[data-testid="stPageLink"] a[aria-current="page"] {
            background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35) !important;
        }
        div[data-testid="stPageLink"] a[aria-current="page"] * {
            color: #ffffff !important;
        }

        /* Buttons styling - Indigo Theme Gradient */
        div.stButton > button:first-child {
            background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
            color: white !important;
            border: none;
            border-radius: 12px;
            padding: 8px 18px;
            font-weight: 700;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3);
            transition: all 0.25s ease;
        }
        div.stButton > button:first-child:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(79, 70, 229, 0.45);
            background: linear-gradient(135deg, #4338ca 0%, #3730a3 100%);
        }
        
        /* Inputs & Selectboxes */
        div[data-baseweb="input"], div[data-baseweb="select"] {
            border-radius: 12px !important;
            border: 1.5px solid #cbd5e1 !important;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03) !important;
        }
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18) !important;
        }

        /* Tabs styling - High Contrast Active and Inactive Tabs */
        button[data-baseweb="tab"] {
            border-radius: 10px !important;
            font-weight: 600 !important;
            color: #334155 !important;
            font-size: 14.5px !important;
            padding: 10px 20px !important;
            margin-right: 6px !important;
        }
        button[data-baseweb="tab"] * {
            color: #334155 !important;
            font-weight: 600 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #4f46e5 !important;
            border-bottom: 3px solid #4f46e5 !important;
            font-weight: 700 !important;
            background-color: #eef2ff !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] * {
            color: #4f46e5 !important;
            font-weight: 700 !important;
        }

        /* Expanders */
        div[data-testid="stExpander"] {
            background: #ffffff !important;
            border-radius: 14px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03) !important;
            margin-bottom: 6px !important;
        }

        /* Form containers */
        div[data-testid="stForm"] {
            background: #ffffff !important;
            border-radius: 20px !important;
            padding: 24px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04) !important;
        }

        /* Map styling helper */
        .map-container {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    render_role_sidebar()


def render_role_sidebar():
    """Dynamically renders role-scoped sidebar navigation links based on user authentication role (PYDAH Design)."""
    import os, base64
    from backend.utils.icons import get_svg_icon
    authenticated = st.session_state.get("authenticated", False)
    user = st.session_state.get("user", {})
    role = user.get("role") if authenticated else "public"

    # Load 3D Brand Logo image as base64
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "mpis_brand_logo.png")
    logo_b64 = ""
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
        except Exception:
            pass

    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 44px; height: 44px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); border: 1.5px solid rgba(255,255,255,0.3);" />' if logo_b64 else get_svg_icon('brand_logo', size=32)

    with st.sidebar:
        # Top Blue Brand Header Container with 3D Brand Logo
        st.markdown(f"""
        <div class="sidebar-brand-header" style="background: linear-gradient(135deg, #1e1b4b 0%, #3730a3 50%, #4f46e5 100%); padding: 24px 16px 32px 16px; margin-top: -60px; text-align: center; color: white;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 6px;">
                {logo_html}
                <span style="font-size: 22px; font-weight: 800; letter-spacing: 0.5px; color: #ffffff !important;">MPIS PORTAL</span>
            </div>
            <div style="font-size: 11px; opacity: 0.9; margin-top: 2px; color: #e0e7ff !important; font-style: italic;">Missing Persons Identification System</div>
        </div>
        <div style="background: #ffffff; border-top-left-radius: 24px; border-top-right-radius: 24px; margin-top: -18px; padding: 14px 12px 12px 12px; box-shadow: 0 -4px 20px rgba(0,0,0,0.06);">
        """, unsafe_allow_html=True)

        if not authenticated:
            st.page_link("app.py", label="Dashboard", icon="🏠")
            st.page_link("pages/public_portal.py", label="Public Portal", icon="🌐")
            st.page_link("pages/cases.py", label="Case Directory", icon="📁")
            st.page_link("pages/map.py", label="Sightings Map", icon="📍")
            st.page_link("pages/login.py", label="Officer / Admin Login", icon="🔐")

        elif role == "officer":
            st.page_link("pages/officer_dashboard.py", label="Dashboard", icon="👮")
            st.page_link("pages/cases.py", label="Case Directory", icon="📁")
            
            # PYDAH Section Divider Line
            st.markdown("""
            <div style="text-align: center; margin: 12px 0 6px 0; border-bottom: 1px solid #f1f5f9; line-height: 0.1em;">
                <span style="background:#fff; padding:0 8px; font-size: 10px; font-weight: 800; color: #94a3b8; letter-spacing: 0.08em;">CASE OPERATIONS</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.page_link("pages/map.py", label="Sightings Map", icon="📍")
            st.page_link("pages/sightings.py", label="Sighting Reports", icon="👁️")
            st.page_link("pages/public_portal.py", label="Public Portal", icon="🌐")

        elif role == "admin":
            st.page_link("pages/admin_dashboard.py", label="Dashboard", icon="👑")
            st.page_link("pages/case_management.py", label="Case Management", icon="📋")

            # PYDAH Section Divider Line 1
            st.markdown("""
            <div style="text-align: center; margin: 12px 0 6px 0; border-bottom: 1px solid #f1f5f9; line-height: 0.1em;">
                <span style="background:#fff; padding:0 8px; font-size: 10px; font-weight: 800; color: #94a3b8; letter-spacing: 0.08em;">INTELLIGENCE & AI</span>
            </div>
            """, unsafe_allow_html=True)

            st.page_link("pages/admin_face_matching.py", label="Face Match Engine", icon="🔬")
            st.page_link("pages/video_sightings.py", label="Video Sightings", icon="📹")
            st.page_link("pages/admin_map.py", label="Admin Map", icon="🗺️")
            st.page_link("pages/admin_public_submissions.py", label="Public Submissions", icon="📥")
            st.page_link("pages/match_review.py", label="Match Review", icon="⚖️")

            # PYDAH Section Divider Line 2
            st.markdown("""
            <div style="text-align: center; margin: 12px 0 6px 0; border-bottom: 1px solid #f1f5f9; line-height: 0.1em;">
                <span style="background:#fff; padding:0 8px; font-size: 10px; font-weight: 800; color: #94a3b8; letter-spacing: 0.08em;">DIRECTORIES & REPORTS</span>
            </div>
            """, unsafe_allow_html=True)

            st.page_link("pages/cases.py", label="Case Directory", icon="📁")
            st.page_link("pages/map.py", label="Sightings Map", icon="📍")
            st.page_link("pages/sightings.py", label="Sighting Reports", icon="👁️")
            st.page_link("pages/public_portal.py", label="Public Portal", icon="🌐")

        st.markdown("</div>", unsafe_allow_html=True)

        # Bottom Profile Row (PYDAH Reference Design)
        if authenticated:
            st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: #ffffff; border-radius: 14px; border: 1px solid #e2e8f0; margin-top: 14px; margin-bottom: 6px; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);">
                        {user.get('username', 'U')[:2].upper()}
                    </div>
                    <div>
                        <strong style="font-size: 13px; color: #0f172a; display: block; line-height: 1.2;">{user.get('username', 'User').upper()}</strong>
                        <span style="font-size: 10px; color: #4f46e5; font-weight: 700; text-transform: uppercase;">{role.upper()} ROLE</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🚪 Log Out", key="sidebar_logout_btn", use_container_width=True):
                from backend.auth.authentication import logout_user
                logout_user()
