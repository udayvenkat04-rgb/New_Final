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

        .stApp, header[data-testid="stHeader"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
        }

        /* Light Cards */
        .glass-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        .glass-card:hover {
            transform: translateY(-3px);
            border-color: #10b981;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        }

        /* Styled Badges */
        .badge {
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge-missing {
            background-color: #fee2e2;
            color: #dc2626;
            border: 1px solid #fca5a5;
        }
        .badge-found {
            background-color: #d1fae5;
            color: #059669;
            border: 1px solid #6ee7b7;
        }
        .badge-pending {
            background-color: #fef3c7;
            color: #d97706;
            border: 1px solid #fcd34d;
        }
        .badge-verified {
            background-color: #dbeafe;
            color: #2563eb;
            border: 1px solid #93c5fd;
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
            border-left: 4px solid #10b981;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border-top: 1px solid #e2e8f0;
            border-right: 1px solid #e2e8f0;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        }
        
        /* Light Sidebar styling with crisp dark text */
        section[data-testid="stSidebar"],
        div[data-testid="stSidebarNav"],
        section[data-testid="stSidebar"] > div {
            background-color: #f8fafc !important;
            border-right: 1px solid #e2e8f0 !important;
        }
        section[data-testid="stSidebar"] *, 
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] a {
            color: #0f172a !important;
        }
        /* Completely hide default auto-generated Streamlit multi-page sidebar navigation */
        div[data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Buttons styling */
        div.stButton > button:first-child {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white !important;
            border: none;
            border-radius: 8px;
            padding: 8px 24px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
            transition: all 0.2s ease;
        }
        div.stButton > button:first-child:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
        }
        
        /* Secondary/Rerun buttons */
        div.stButton > button.secondary {
            background: #f1f5f9 !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }

        /* Map styling helper */
        .map-container {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    render_role_sidebar()


def render_role_sidebar():
    """Dynamically renders role-scoped sidebar navigation links based on user authentication role."""
    authenticated = st.session_state.get("authenticated", False)
    user = st.session_state.get("user", {})
    role = user.get("role") if authenticated else "public"

    with st.sidebar:
        # Render user profile info box at top of sidebar
        if authenticated:
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #cbd5e1; border-left: 4px solid #10b981; margin-bottom: 15px;">
                <span style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">Logged in as</span><br/>
                <strong style="color: #0f172a; font-size: 15px;">{user.get('username', 'User')}</strong><br/>
                <span class="badge badge-found" style="margin-top: 6px;">{role.upper()} ROLE</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color: #fffbeb; padding: 12px; border-radius: 8px; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; margin-bottom: 15px;">
                <strong style="color: #92400e; font-size: 13px;">🔒 Authentication Required</strong><br/>
                <span style="font-size: 12px; color: #b45309;">Please log in to access secure portals.</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<p style='font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;'>📌 Navigation</p>", unsafe_allow_html=True)

        if not authenticated:
            st.page_link("app.py", label="Home Portal", icon="🏠")
            st.page_link("pages/public_portal.py", label="Public Portal", icon="🌐")
            st.page_link("pages/cases.py", label="Case Directory", icon="📁")
            st.page_link("pages/map.py", label="Sightings Map", icon="📍")
            st.page_link("pages/login.py", label="Officer / Admin Login", icon="🔐")

        elif role == "officer":
            st.page_link("pages/officer_dashboard.py", label="Officer Dashboard", icon="👮")
            st.page_link("pages/cases.py", label="Case Directory", icon="📁")
            st.page_link("pages/map.py", label="Sightings Map", icon="📍")
            st.page_link("pages/sightings.py", label="Sighting Reports", icon="👁️")
            st.page_link("pages/public_portal.py", label="Public Portal", icon="🌐")


        elif role == "admin":
            st.page_link("pages/admin_dashboard.py", label="Admin Dashboard", icon="👑")
            st.page_link("pages/case_management.py", label="Case Management", icon="📋")
            st.page_link("pages/admin_face_matching.py", label="Face Match Engine", icon="🔬")
            st.page_link("pages/video_sightings.py", label="Video Sightings", icon="📹")
            st.page_link("pages/admin_map.py", label="Admin Map", icon="🗺️")
            st.page_link("pages/admin_public_submissions.py", label="Public Submissions", icon="📥")
            st.page_link("pages/match_review.py", label="Match Review", icon="⚖️")
            st.page_link("pages/cases.py", label="Case Directory", icon="📁")
            st.page_link("pages/map.py", label="Sightings Map", icon="📍")
            st.page_link("pages/sightings.py", label="Sighting Reports", icon="👁️")
            st.page_link("pages/public_portal.py", label="Public Portal", icon="🌐")

            with st.expander("🛠️ Developer Tools"):
                st.page_link("pages/dev_face_detection.py", label="Dev Face Detection", icon="🧪")
                st.page_link("pages/dev_face_embedding.py", label="Dev Face Embedding", icon="🧬")

        if authenticated:
            st.markdown("---")
            if st.button("🚪 Log Out", key="sidebar_logout_btn", use_container_width=True):
                from backend.auth.authentication import logout_user
                logout_user()


