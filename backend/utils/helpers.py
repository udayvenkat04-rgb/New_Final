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
            margin-top: 0px !important;
        }

        /* 100% Full-Screen Edge-to-Edge Span across all screen resolutions */
        .main .block-container,
        div[data-testid="stBlockContainer"],
        [data-testid="stBlockContainer"] {
            max-width: 100% !important;
            width: 100% !important;
            min-width: 100% !important;
            padding-top: 0px !important;
            padding-bottom: 2rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            margin-top: 0px !important;
            margin-left: 0px !important;
            margin-right: 0px !important;
        }

        @media screen and (min-width: 768px) {
            .main .block-container,
            div[data-testid="stBlockContainer"],
            [data-testid="stBlockContainer"] {
                max-width: 100% !important;
                width: 100% !important;
                min-width: 100% !important;
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
        }

        /* Statistics Metric Cards Row - Position Cards Close Together with Uniform 16px Gap */
        div[data-testid="stHorizontalBlock"] {
            gap: 16px !important;
        }

        .metric-card {
            width: 100% !important;
            box-sizing: border-box !important;
            margin: 0 !important;
        }

        /* Top Header Navbar Row - Strictly Single Horizontal Line (No Line Wrapping) */
        div[data-testid="stHorizontalBlock"]:first-child {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 12px !important;
        }
        div[data-testid="stHorizontalBlock"]:first-child > div {
            width: auto !important;
            min-width: auto !important;
            flex: 0 1 auto !important;
        }

        /* Pull top header navbar flush against top edge of browser window on 100% maximized viewports */
        .main .block-container > div:first-child,
        div[data-testid="stBlockContainer"] > div:first-child {
            margin-top: -55px !important;
            padding-top: 0px !important;
        }

        .main .element-container:first-child,
        .main [data-testid="stVerticalBlock"] > div:first-child,
        div[data-testid="stVerticalBlock"] > div:first-child,
        div[data-testid="stVerticalBlock"] {
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

        /* Buttons styling - Default Form Buttons */
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

        /* National Power Portal Top Navbar Styling (Flat Text Links + Yellow Accent Active Box) */
        div[data-testid="stHorizontalBlock"]:first-child div.stButton > button {
            background: transparent !important;
            color: #0f172a !important;
            border: 2px solid transparent !important;
            border-radius: 4px !important;
            box-shadow: none !important;
            font-weight: 700 !important;
            font-size: 13.5px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            padding: 6px 14px !important;
            transition: all 0.15s ease !important;
            margin: 0 !important;
            white-space: nowrap !important;
            word-break: keep-all !important;
            overflow: visible !important;
        }
        div[data-testid="stHorizontalBlock"]:first-child div.stButton > button:hover {
            background: #f8fafc !important;
            color: #2563eb !important;
            border-color: #cbd5e1 !important;
            transform: none !important;
            box-shadow: none !important;
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

        /* Multi-Device Responsive Support (Mobile, Tablet, Laptop, Laptop L, 4K Display) */
        @media screen and (max-width: 1200px) {
            div[data-testid="stHorizontalBlock"]:first-child div.stButton > button {
                font-size: 12px !important;
                padding: 5px 8px !important;
            }
        }

        @media screen and (max-width: 768px) {
            /* Mobile Devices */
            .main .block-container,
            div[data-testid="stBlockContainer"] {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
            div[data-testid="stHorizontalBlock"] div.stButton > button {
                font-size: 11px !important;
                padding: 4px 6px !important;
            }
        }

        /* Ensure all Streamlit columns stay in a horizontal row */
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            align-items: center !important;
        }

        /* Seamless Light & Dark Theme Adaptability */
        @media (prefers-color-scheme: dark) {
            .stApp {
                background-color: #0b1329 !important;
                color: #f8fafc !important;
            }
            .metric-card, .dashboard-outer-card, .glass-card, div[data-testid="stForm"], div[data-testid="stExpander"] {
                background-color: #1e293b !important;
                border-color: #334155 !important;
                color: #f8fafc !important;
            }
            .metric-card span, .glass-card span {
                color: #cbd5e1 !important;
            }
            div[data-baseweb="input"], div[data-baseweb="select"] {
                background-color: #1e293b !important;
                color: #f8fafc !important;
                border-color: #475569 !important;
            }
            div[data-testid="stHorizontalBlock"]:first-child div.stButton > button {
                color: #f8fafc !important;
            }
            div[data-testid="stHorizontalBlock"]:first-child div.stButton > button[kind="primary"] {
                background: #1e293b !important;
                color: #f8fafc !important;
                border-color: #eab308 !important;
            }
        }

        /* Hide left sidebar completely so top header acts as main navbar */
        section[data-testid="stSidebar"] {
            display: none !important;
            width: 0px !important;
        }
        div[data-testid="stSidebarNav"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    render_top_header()


def render_top_header():
    """Renders a modern National Portal style top header navigation bar across all pages."""
    authenticated = st.session_state.get("authenticated", False)
    user = st.session_state.get("user", {}) or {}
    role = user.get("role") if authenticated else "public"

    import os, base64
    from backend.utils.icons import get_svg_icon

    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "mpis_brand_logo.png")
    logo_b64 = ""
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
        except Exception:
            pass

    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 42px; height: 42px; border-radius: 6px;" />' if logo_b64 else get_svg_icon('brand_logo', size=36)

    if not authenticated:
        hcol1, hcol2 = st.columns([2.8, 5.2])
        with hcol1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 12px; padding: 2px 0;">
                {logo_html}
                <div>
                    <div style="font-size: 20px; font-weight: 900; letter-spacing: -0.3px; font-family: 'Outfit', sans-serif; white-space: nowrap;">
                        <span style="color: #2563eb;">NATIONAL</span> <span style="color: #d97706;">MISSING PORTAL</span>
                    </div>
                    <div style="font-size: 9px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap;">Government of India • Ministry of Home Affairs</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with hcol2:
            cols = st.columns([0.9, 1.1, 1.4, 1.5, 1.5, 1])
            with cols[0]:
                if st.button("HOME", key="hdr_home", use_container_width=True):
                    st.switch_page("app.py")
            with cols[1]:
                if st.button("ABOUT US", key="hdr_about", use_container_width=True):
                    st.switch_page("app.py")
            with cols[2]:
                if st.button("PUBLIC PORTAL", key="hdr_public", type="primary", use_container_width=True):
                    st.switch_page("pages/public_portal.py")
            with cols[3]:
                if st.button("CASE DIRECTORY", key="hdr_cases", use_container_width=True):
                    st.switch_page("pages/cases.py")
            with cols[4]:
                if st.button("SIGHTINGS MAP", key="hdr_map", use_container_width=True):
                    st.switch_page("pages/map.py")
            with cols[5]:
                if st.button("LOGIN", key="hdr_login", use_container_width=True):
                    st.switch_page("pages/login.py")

    elif role == "officer":
        hcol1, hcol2 = st.columns([2.8, 5.2])
        with hcol1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 12px; padding: 2px 0;">
                {logo_html}
                <div>
                    <div style="font-size: 20px; font-weight: 900; letter-spacing: -0.3px; font-family: 'Outfit', sans-serif; white-space: nowrap;">
                        <span style="color: #2563eb;">NATIONAL</span> <span style="color: #d97706;">MISSING PORTAL</span>
                    </div>
                    <div style="font-size: 9.5px; color: #4f46e5; font-weight: 700; text-transform: uppercase;">Officer: {user.get('username', 'User').upper()}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with hcol2:
            cols = st.columns([1, 1.1, 1.1, 1.1, 1.1, 1])
            with cols[0]:
                if st.button("DASHBOARD", key="hdr_off_dash", type="primary", use_container_width=True):
                    st.switch_page("pages/officer_dashboard.py")
            with cols[1]:
                if st.button("CASES", key="hdr_off_cases", use_container_width=True):
                    st.switch_page("pages/cases.py")
            with cols[2]:
                if st.button("MAP", key="hdr_off_map", use_container_width=True):
                    st.switch_page("pages/map.py")
            with cols[3]:
                if st.button("SIGHTINGS", key="hdr_off_sightings", use_container_width=True):
                    st.switch_page("pages/sightings.py")
            with cols[4]:
                if st.button("PUBLIC", key="hdr_off_pub", use_container_width=True):
                    st.switch_page("pages/public_portal.py")
            with cols[5]:
                if st.button("LOGOUT", key="hdr_logout", use_container_width=True):
                    from backend.auth.authentication import logout_user
                    logout_user()

    elif role == "admin":
        hcol1, hcol2 = st.columns([2.5, 5.5])
        with hcol1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 12px; padding: 2px 0;">
                {logo_html}
                <div>
                    <div style="font-size: 19px; font-weight: 900; letter-spacing: -0.3px; font-family: 'Outfit', sans-serif; white-space: nowrap;">
                        <span style="color: #2563eb;">NATIONAL</span> <span style="color: #d97706;">MISSING PORTAL</span>
                    </div>
                    <div style="font-size: 9.5px; color: #dc2626; font-weight: 700; text-transform: uppercase;">Admin: {user.get('username', 'Admin').upper()}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with hcol2:
            cols = st.columns([1, 1, 1, 1, 1, 1, 1, 1])
            with cols[0]:
                if st.button("DASH", key="hdr_adm_dash", type="primary", use_container_width=True):
                    st.switch_page("pages/admin_dashboard.py")
            with cols[1]:
                if st.button("CASES", key="hdr_adm_cases", use_container_width=True):
                    st.switch_page("pages/case_management.py")
            with cols[2]:
                if st.button("MATCH", key="hdr_adm_match", use_container_width=True):
                    st.switch_page("pages/admin_face_matching.py")
            with cols[3]:
                if st.button("VIDEO", key="hdr_adm_vid", use_container_width=True):
                    st.switch_page("pages/video_sightings.py")
            with cols[4]:
                if st.button("MAP", key="hdr_adm_map", use_container_width=True):
                    st.switch_page("pages/admin_map.py")
            with cols[5]:
                if st.button("SUBMISSIONS", key="hdr_adm_sub", use_container_width=True):
                    st.switch_page("pages/admin_public_submissions.py")
            with cols[6]:
                if st.button("REVIEW", key="hdr_adm_rev", use_container_width=True):
                    st.switch_page("pages/match_review.py")
            with cols[7]:
                if st.button("LOGOUT", key="hdr_adm_logout", use_container_width=True):
                    from backend.auth.authentication import logout_user
                    logout_user()

    st.markdown("<div style='height: 2px; background: linear-gradient(90deg, #2563eb 0%, #3b82f6 50%, #eab308 100%); margin: 6px 0 18px 0;'></div>", unsafe_allow_html=True)


def render_role_sidebar():
    """Backwards compatible alias that delegates to render_top_header()."""
    render_top_header()
