import streamlit as st
from backend.utils.file_utils import save_uploaded_file, load_image_safely, get_placeholder_image


def inject_custom_css():
    """Injects a modern, premium 100% Light Theme styling in Streamlit."""
    try:
        from backend.auth.authentication import restore_session_if_needed
        restore_session_if_needed()
    except Exception:
        pass
    authenticated = st.session_state.get("authenticated", False)
    st.markdown("""
    <style>
        /* Import Outfit Google Font */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
        
        /* Custom Custom Sidebar Transition & Width overrides (TEMPORARILY DISABLED FOR DIAGNOSTICS)
        section[data-testid="stSidebar"] {
            background-color: #f8fafc !important;
            border-right: 1px solid #e2e8f0 !important;
            transition: width 0.3s ease, min-width 0.3s ease, transform 0.3s ease !important;
        }
        
        section[data-testid="stSidebar"]:not([data-collapsed="true"]) {
            width: 310px !important;
            min-width: 310px !important;
        }
        
        section[data-testid="stSidebar"][data-collapsed="true"],
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] {
            transform: none !important;
            width: 80px !important;
            min-width: 80px !important;
            display: block !important;
            visibility: visible !important;
        }
        
        section[data-testid="stSidebar"][data-collapsed="true"] [data-testid="stSidebarUserContent"],
        section[data-testid="stSidebar"][data-collapsed="true"] > div,
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"][data-collapsed="true"] *,
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] * {
            visibility: visible !important;
            display: block !important;
            opacity: 1 !important;
        }
        
        section[data-testid="stSidebar"][data-collapsed="true"] .sidebar-brand-text,
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] .sidebar-brand-text {
            display: none !important;
        }
        section[data-testid="stSidebar"][data-collapsed="true"] .sidebar-brand-container,
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] .sidebar-brand-container {
            justify-content: center !important;
            padding-left: 0 !important;
        }
        section[data-testid="stSidebar"][data-collapsed="true"] div[data-testid="stPageLink"] a span:last-child,
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] div[data-testid="stPageLink"] a span:last-child {
            display: none !important;
        }
        section[data-testid="stSidebar"][data-collapsed="true"] div[data-testid="stPageLink"] a,
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] div[data-testid="stPageLink"] a {
            justify-content: center !important;
            padding: 12px 0 !important;
        }
        section[data-testid="stSidebar"][data-collapsed="true"] .st-key-sidebar_logout_btn button,
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] .st-key-sidebar_logout_btn button {
            font-size: 0 !important;
            padding: 8px 0 !important;
            width: 100% !important;
        }
        section[data-testid="stSidebar"][data-collapsed="true"] .st-key-sidebar_logout_btn button::before,
        div[data-testid="stAppViewContainer"][data-sidebar-state="collapsed"] section[data-testid="stSidebar"] .st-key-sidebar_logout_btn button::before {
            content: "🚪" !important;
            font-size: 18px !important;
        }
        */
        
        /* Sidebar Collapse (<<) & Expand (>>) Responsive Arrow Buttons Styling */
        button[data-testid="stSidebarCollapseButton"],
        button[data-testid="stHeaderSidebarCollapseButton"],
        div[data-testid="collapsedControl"] button,
        header[data-testid="stHeader"] button {
            background-color: #ffffff !important;
            border: 1.5px solid #cbd5e1 !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.1) !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            z-index: 999999 !important;
            width: 38px !important;
            height: 38px !important;
            color: #0f172a !important;
            cursor: pointer !important;
            pointer-events: auto !important;
        }
        
        button[data-testid="stSidebarCollapseButton"] svg,
        button[data-testid="stHeaderSidebarCollapseButton"] svg,
        div[data-testid="collapsedControl"] button svg,
        header[data-testid="stHeader"] button svg {
            fill: #0f172a !important;
            color: #0f172a !important;
            transition: fill 0.2s ease, transform 0.2s ease !important;
        }

        button[data-testid="stSidebarCollapseButton"]:hover,
        button[data-testid="stHeaderSidebarCollapseButton"]:hover,
        div[data-testid="collapsedControl"] button:hover,
        header[data-testid="stHeader"] button:hover {
            background-color: #4f46e5 !important;
            border-color: #4338ca !important;
            box-shadow: 0 6px 18px rgba(79, 70, 229, 0.35) !important;
            transform: scale(1.08) !important;
        }

        button[data-testid="stSidebarCollapseButton"]:hover svg,
        button[data-testid="stHeaderSidebarCollapseButton"]:hover svg,
        div[data-testid="collapsedControl"] button:hover svg,
        header[data-testid="stHeader"] button:hover svg {
            fill: #ffffff !important;
            color: #ffffff !important;
        }

        /* Fixed High-Visibility Positioning for Collapsed Expand Arrow Button (>>) */
        div[data-testid="collapsedControl"],
        [data-testid="collapsedControl"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: fixed !important;
            top: 14px !important;
            left: 14px !important;
            z-index: 999999 !important;
        }

        /* Mobile & Tablet Responsiveness for Arrow Controls */
        @media screen and (max-width: 991px) {
            button[data-testid="stSidebarCollapseButton"],
            button[data-testid="stHeaderSidebarCollapseButton"],
            div[data-testid="collapsedControl"] button {
                width: 36px !important;
                height: 36px !important;
                border-radius: 8px !important;
            }
            div[data-testid="collapsedControl"] {
                top: 10px !important;
                left: 10px !important;
            }
        }

        /* Global font & light theme background */
        html, body, [class*="css"], .stMarkdown {
            font-family: 'Outfit', sans-serif;
            color: #0f172a;
        }

        .stApp {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
        }

        /* Remove default Streamlit paddings that were left unchecked by the user and apply compact margins */
        .block-container,
        div[data-testid="stAppViewBlockContainer"],
        .st-emotion-cache-zy6yx3 {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }

        /* Override generated column block wrapper display property to block as requested */
        .st-emotion-cache-tn0cau {
            display: block !important;
        }

        header[data-testid="stHeader"],
        .stAppHeader {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            pointer-events: none !important;
        }

        /* Re-enable pointer events for all interactive header controls (like expand/collapse buttons) */
        button[data-testid="stSidebarCollapseButton"],
        button[data-testid="stHeaderSidebarCollapseButton"],
        div[data-testid="collapsedControl"],
        div[data-testid="collapsedControl"] *,
        .stSidebarCollapseButton {
            pointer-events: auto !important;
        }

        /* Keep header native height so expand chevron/hamburger is always visible */

        /* Hide the raw sidebar navigation page links list under all circumstances */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Donezo-style Outer Dashboard White Card Container */
        .dashboard-outer-card {
            background: #ffffff !important;
            border-radius: 28px !important;
            padding: 32px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 24px !important;
        }

        /* Metric Dashboard Cards Styling - Scaled Down / Reduced Size with increased vertical spacing */
        .metric-card, .donezo-metric-card {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px !important;
            padding: 16px 20px !important;
            margin-bottom: 24px !important; /* Increased distance between cards vertically */
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03) !important;
            transition: all 0.25s ease !important;
            height: 140px !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
            box-sizing: border-box !important;
        }
        .metric-card:hover, .donezo-metric-card:hover {
            transform: translateY(-2px) !important;
            border-color: #4f46e5 !important;
            box-shadow: 0 8px 24px rgba(79, 70, 229, 0.1) !important;
        }
        
        /* Scaled down internal typography and controls inside metric cards */
        .metric-card div:first-child > span:first-child,
        .donezo-metric-card div:first-child > span:first-child {
            font-size: 13.5px !important; /* Keep normal label text size */
        }
        
        .metric-card h1, .donezo-metric-card h1 {
            font-size: 32px !important; /* Keep large value number size */
            margin-bottom: 0px !important;
        }
        
        .metric-card div:last-child, .donezo-metric-card div:last-child {
            font-size: 11.5px !important; /* Keep normal bottom subtext size */
        }
        
        .metric-card .arrow-icon-circle, .donezo-metric-card .arrow-icon-circle {
            width: 24px !important; /* Keep normal arrow circle control */
            height: 24px !important;
            font-size: 11px !important;
        }
        
        /* Premium Interactive Hover - Transforms card background to solid blue/indigo */
        .metric-card:hover, .donezo-metric-card:hover {
            transform: translateY(-4px) !important;
            background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
            border-color: transparent !important;
            box-shadow: 0 12px 30px rgba(79, 70, 229, 0.3) !important;
        }
        
        /* Label text turns white on hover */
        .metric-card:hover div:first-child > span:first-child,
        .donezo-metric-card:hover div:first-child > span:first-child {
            color: #ffffff !important;
        }
        
        /* Large value number turns white on hover */
        .metric-card:hover h1, .donezo-metric-card:hover h1 {
            color: #ffffff !important;
        }
        
        /* Bottom subtext wrapper turns light white on hover (preserves bullet point color via inheritance) */
        .metric-card:hover div:last-child, .donezo-metric-card:hover div:last-child {
            color: rgba(255, 255, 255, 0.9) !important;
        }
        
        /* Arrow icon circle turns white outline and translucent white background on hover */
        .metric-card:hover .arrow-icon-circle, .donezo-metric-card:hover .arrow-icon-circle {
            border-color: rgba(255, 255, 255, 0.4) !important;
            color: #ffffff !important;
            background-color: rgba(255, 255, 255, 0.15) !important;
        }

        /* Donezo Hero Cards Styling - Scaled Down / Reduced Size */
        .donezo-hero-card {
            background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            padding: 16px 20px !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15) !important;
            transition: all 0.25s ease !important;
            margin-bottom: 24px !important;
            border: none !important;
            height: 140px !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
            box-sizing: border-box !important;
        }
        .donezo-hero-card:hover {
            transform: translateY(-4px) !important;
            box-shadow: 0 10px 25px rgba(79, 70, 229, 0.35) !important;
        }

        /* Hide Streamlit Deploy button, Main Menu (three dots), and Decoration Line */
        .stDeployButton, .stAppDeployButton, div[data-testid="stConnectionStatus"] {
            display: none !important;
        }
        #MainMenu, [data-testid="stMainMenu"] {
            visibility: hidden !important;
            display: none !important;
        }
        div[data-testid="stDecoration"] {
            display: none !important;
        }
        div[data-testid="stToolbar"] {
            display: none !important;
        }

        /* Main Page Viewport - 100% Full Width Span (Left to Right Edge) */
        div[data-testid="stAppViewContainer"],
        section.main {
            margin-top: 0px !important;
        }

        /* 100% Full-Screen Edge-to-Edge Span across all screen resolutions */
        .main .block-container,
        div[data-testid="stBlockContainer"],
        [data-testid="stBlockContainer"],
        div[data-testid="stAppViewBlockContainer"],
        .stAppViewBlockContainer {
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

        .main .element-container:first-child,
        .main [data-testid="stVerticalBlock"] > div:first-child,
        div[data-testid="stVerticalBlock"] > div:first-child,
        div[data-testid="stVerticalBlock"] {
            margin-top: 0px !important;
            padding-top: 0px !important;
        }

        /* Deep Navy Sidebar Styling matching Reference Design (Image 2) */
        section[data-testid="stSidebar"] {
            background-color: #0b192c !important;
            border-right: 1px solid #1e293b !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            padding: 1.25rem 0.8rem 1.5rem 0.8rem !important;
            background-color: #0b192c !important;
            color: #ffffff !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
        section[data-testid="stSidebar"] div[data-testid="element-container"] {
            width: 100% !important;
            padding-left: 0px !important;
            padding-right: 0px !important;
            margin-left: 0px !important;
            margin-right: 0px !important;
        }

        /* Sidebar Section Category Headers (MAIN, MANAGEMENT, OPERATIONS, SYSTEM) */
        .sidebar-section-header {
            font-size: 10.5px !important;
            font-weight: 700 !important;
            color: #475569 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            margin-top: 14px !important;
            margin-bottom: 6px !important;
            padding-left: 10px !important;
            display: block !important;
        }

        /* Full-Width Page Link Cards in Deep Navy Sidebar (Scoped to Sidebar) */
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] {
            width: 100% !important;
            margin-bottom: 4px !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a {
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;
            width: 100% !important;
            height: 42px !important;
            min-height: 42px !important;
            box-sizing: border-box !important;
            padding: 0 14px !important;
            border-radius: 12px !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            color: #cbd5e1 !important;
            background-color: transparent !important;
            border: none !important;
            transition: all 0.2s ease !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a p,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a span,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a label,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a div {
            color: #cbd5e1 !important;
            font-weight: 500 !important;
            font-size: 14px !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 42px !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover {
            background-color: rgba(255, 255, 255, 0.08) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover p,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover span,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover label,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover div {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        /* Active Page Link Card in Sidebar: Light Blue Soft Fill (matching Image 2) */
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] {
            background-color: #dbeafe !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] p,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] span,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] label,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] div,
        section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] * {
            color: #1e3a8a !important;
            font-weight: 700 !important;
        }

        /* Bottom User Profile Card */
        .sidebar-user-card {
            background: #112240 !important;
            border: 1px solid #1e293b !important;
            border-radius: 14px !important;
            padding: 10px 14px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2) !important;
        }

        /* Sidebar Dedicated Logout Button Styling - Full Width (44px) */
        section[data-testid="stSidebar"] div.stButton > button {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            height: 44px !important;
            min-height: 44px !important;
            padding: 0 18px !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            margin-top: 4px !important;
            box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3) !important;
            transition: all 0.25s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
        }
        section[data-testid="stSidebar"] div.stButton > button p,
        section[data-testid="stSidebar"] div.stButton > button span,
        section[data-testid="stSidebar"] div.stButton > button * {
            color: #ffffff !important;
            font-weight: 700 !important;
        }
        section[data-testid="stSidebar"] div.stButton > button:hover {
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
            box-shadow: 0 6px 18px rgba(239, 68, 68, 0.45) !important;
            transform: translateY(-1px) !important;
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

        /* Ensure all Streamlit columns stay in a horizontal row only on tablet/desktop */
        @media screen and (min-width: 768px) {
            div[data-testid="stHorizontalBlock"] {
                flex-direction: row !important;
                align-items: center !important;
            }
        }

        /* Seamless Light & Dark Theme Adaptability */
        @media (prefers-color-scheme: dark) {
            .stApp {
                background-color: #0b1329 !important;
                color: #f8fafc !important;
            }
            .metric-card, .donezo-metric-card, .dashboard-outer-card, .glass-card, div[data-testid="stForm"], div[data-testid="stExpander"] {
                background-color: #1e293b !important;
                border-color: #334155 !important;
                color: #f8fafc !important;
            }
            .metric-card span, .donezo-metric-card span, .glass-card span {
                color: #cbd5e1 !important;
            }
            .metric-card h1, .donezo-metric-card h1 {
                color: #f8fafc !important;
            }
            .metric-card div, .donezo-metric-card div {
                color: #cbd5e1 !important;
            }
            .donezo-metric-card .arrow-icon-circle {
                color: #f8fafc !important;
                border-color: #475569 !important;
                background-color: transparent !important;
            }
            .metric-card:hover, .donezo-metric-card:hover {
                border-color: #818cf8 !important;
                box-shadow: 0 8px 24px rgba(129, 140, 248, 0.15) !important;
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
            /* Dark Mode Sidebar text and link colors */
            .sidebar-brand-text div {
                color: #f8fafc !important;
            }
            .sidebar-brand-text div:last-child {
                color: #818cf8 !important;
            }
            div[data-testid="stPageLink"] a {
                color: #cbd5e1 !important;
            }
            div[data-testid="stPageLink"] a:hover {
                background-color: rgba(255, 255, 255, 0.08) !important;
                color: #ffffff !important;
            }
            
            /* Dark Mode Floating mobile logout button colors */
            @media screen and (max-width: 991px) {
                div[class*="st-key-mobile_header_logout"] button {
                    background: #1e293b !important;
                    color: #f87171 !important;
                    border-color: #475569 !important;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
                }
                div[class*="st-key-mobile_header_logout"] button:hover {
                    background-color: #334155 !important;
                    border-color: #64748b !important;
                }
            }
            
            /* Dark Mode Sidebar Collapse / Expand button colors */
            button[data-testid="stSidebarCollapseButton"],
            button[data-testid="stHeaderSidebarCollapseButton"],
            div[data-testid="collapsedControl"] button,
            header[data-testid="stHeader"] button {
                background-color: #1e293b !important;
                border-color: #475569 !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
                color: #f8fafc !important;
            }
            button[data-testid="stSidebarCollapseButton"] svg,
            button[data-testid="stHeaderSidebarCollapseButton"] svg,
            div[data-testid="collapsedControl"] button svg,
            header[data-testid="stHeader"] button svg {
                fill: #f8fafc !important;
                color: #f8fafc !important;
            }
            button[data-testid="stSidebarCollapseButton"]:hover,
            button[data-testid="stHeaderSidebarCollapseButton"]:hover,
            div[data-testid="collapsedControl"] button:hover,
            header[data-testid="stHeader"] button:hover {
                background-color: #334155 !important;
                border-color: #64748b !important;
            }
        }
        
        /* Floating mobile logout button in the top right corner */
        @media screen and (max-width: 991px) {
            div.element-container:has(div[class*="st-key-mobile_header_logout"]) {
                position: fixed !important;
                top: 10px !important;
                right: 16px !important;
                z-index: 999995 !important;
                margin: 0 !important;
                padding: 0 !important;
                width: 40px !important;
                height: 40px !important;
            }
            div[class*="st-key-mobile_header_logout"] button {
                background: #ffffff !important;
                color: #ef4444 !important;
                border: 1.5px solid #cbd5e1 !important;
                border-radius: 50% !important;
                width: 40px !important;
                height: 40px !important;
                min-width: 40px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08) !important;
                font-size: 16px !important;
                padding: 0 !important;
                pointer-events: auto !important;
            }
            div[class*="st-key-mobile_header_logout"] button:hover {
                background-color: #f8fafc !important;
                border-color: #94a3b8 !important;
            }
        }
        @media screen and (min-width: 992px) {
            div.element-container:has(div[class*="st-key-mobile_header_logout"]),
            div[class*="st-key-mobile_header_logout"] {
                display: none !important;
                visibility: hidden !important;
                height: 0px !important;
                width: 0px !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            div[class*="st-key-mobile_header_logout"] button {
                display: none !important;
                visibility: hidden !important;
                height: 0px !important;
                width: 0px !important;
            }
        }
        
        /* Styled st.container(border=True) */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff !important;
            border-radius: 16px !important;
            border: 1.5px solid #cbd5e1 !important;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05) !important;
            padding: 16px 20px !important;
            transition: all 0.25s ease !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-2px) !important;
            border-color: #4f46e5 !important;
            box-shadow: 0 8px 24px rgba(79, 70, 229, 0.12) !important;
        }

        /* Mobile 2x2 Grid Layout for Statistic Cards */
        @media screen and (max-width: 767px) {
            /* Force horizontal columns blocks containing statistic cards to display as flex wrap on mobile */
            div[data-testid="stHorizontalBlock"]:has(.donezo-metric-card, .donezo-hero-card, .metric-card) {
                display: flex !important;
                flex-flow: row wrap !important;
                gap: 12px !important;
            }
            /* Force each child column containing statistic cards to be exactly 50% width minus gap */
            div[data-testid="stHorizontalBlock"]:has(.donezo-metric-card, .donezo-hero-card, .metric-card) > div[data-testid="column"],
            div[data-testid="stHorizontalBlock"]:has(.donezo-metric-card, .donezo-hero-card, .metric-card) > div.stColumn {
                flex: 1 1 calc(50% - 6px) !important;
                min-width: calc(50% - 6px) !important;
                max-width: calc(50% - 6px) !important;
                margin-top: 0 !important;
                margin-left: 0 !important;
                margin-right: 0 !important;
                margin-bottom: 16px !important; /* Force bottom spacing between rows */
                padding: 0 !important;
            }
            
            /* Adjust metric cards styling inside the 2x2 grid */
            .metric-card, .donezo-metric-card, .donezo-hero-card {
                height: 140px !important; /* Enforce uniform 140px height to prevent overflow and maintain same length/width */
                padding: 12px 14px !important;
                margin-bottom: 16px !important; /* Force bottom spacing between rows */
            }
            
            /* Scale down values & text sizes on mobile to prevent overflow */
            .metric-card h1, .donezo-metric-card h1 {
                font-size: 20px !important;
                margin-bottom: 2px !important;
            }
            
            .metric-card div:first-child > span:first-child,
            .donezo-metric-card div:first-child > span:first-child,
            .donezo-hero-card div:first-child > span:first-child {
                font-size: 10px !important;
            }
            
            .metric-card div:last-child, .donezo-metric-card div:last-child,
            .donezo-hero-card div:last-child {
                font-size: 9px !important;
            }
            
            .metric-card .arrow-icon-circle, .donezo-metric-card .arrow-icon-circle {
                width: 16px !important;
                height: 16px !important;
                font-size: 8px !important;
            }

            /* Mobile Overrides for responsive containers & grids */
            .about-container-card {
                padding: 20px 16px !important;
                border-radius: 14px !important;
                box-sizing: border-box !important;
                width: 100% !important;
            }
            .mission-synergy-grid {
                grid-template-columns: 1fr !important;
                gap: 16px !important;
                margin-bottom: 16px !important;
                box-sizing: border-box !important;
                width: 100% !important;
            }
            .workflow-grid {
                grid-template-columns: 1fr !important;
                gap: 20px !important;
                padding: 16px !important;
                box-sizing: border-box !important;
                width: 100% !important;
            }
            .footer-container-card {
                padding: 24px 16px !important;
                border-radius: 14px !important;
                box-sizing: border-box !important;
                width: 100% !important;
            }
            .footer-grid {
                grid-template-columns: 1fr !important;
                gap: 24px !important;
                padding-bottom: 20px !important;
                box-sizing: border-box !important;
                width: 100% !important;
            }
            .features-grid {
                grid-template-columns: 1fr !important;
                gap: 16px !important;
                box-sizing: border-box !important;
                width: 100% !important;
            }
            .feature-card {
                height: auto !important;
                min-height: 175px !important;
                box-sizing: border-box !important;
                width: 100% !important;
            }
            /* Mobile tab bar adjustments to prevent squishing and overlap */
            button[data-baseweb="tab"] {
                font-size: 12px !important;
                padding: 6px 12px !important;
                margin-right: 4px !important;
            }
            div[role="tablist"] {
                overflow-x: auto !important;
                flex-wrap: nowrap !important;
                gap: 4px !important;
            }
        }

        /* Desktop/Default Styles for responsive containers & grids */
        .about-container-card {
            background: #ffffff;
            border-radius: 20px;
            padding: 36px 40px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 8px 30px rgba(15, 23, 42, 0.05);
            margin-top: 10px;
            box-sizing: border-box !important;
            width: 100% !important;
        }
        .mission-synergy-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 28px;
            margin-bottom: 28px;
            box-sizing: border-box !important;
            width: 100% !important;
        }
        .workflow-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            background: #f8fafc;
            padding: 24px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-sizing: border-box !important;
            width: 100% !important;
        }
        .footer-container-card {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #ffffff;
            border-radius: 20px;
            padding: 40px 48px;
            border: 1px solid #334155;
            box-shadow: 0 12px 36px rgba(15, 23, 42, 0.3);
            margin-top: 36px;
            margin-bottom: 24px;
            box-sizing: border-box !important;
            width: 100% !important;
        }
        .footer-grid {
            display: grid;
            grid-template-columns: 2fr 1.5fr 1.5fr 1fr;
            gap: 36px;
            padding-bottom: 30px;
            border-bottom: 1px solid #334155;
            box-sizing: border-box !important;
            width: 100% !important;
        }
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
            box-sizing: border-box !important;
            width: 100% !important;
        }
        .feature-card {
            padding: 20px;
            background: #ffffff;
            border: 1.5px solid #cbd5e1;
            border-radius: 14px;
            box-shadow: 0 4px 14px rgba(15,23,42,0.03);
            height: 175px; /* Fixed height for uniform desktop alignment */
            box-sizing: border-box !important;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            width: 100% !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    if not authenticated:
        st.markdown("""
        <style>
            /* Hide the sidebar completely for unauthenticated users */
            section[data-testid="stSidebar"],
            [data-testid="stSidebar"] {
                display: none !important;
                width: 0px !important;
                visibility: hidden !important;
            }

            /* Force main container to use 100% width and remove any sidebar spacer for unauthenticated users */
            div[data-testid="stAppViewContainer"] {
                margin: 0 !important;
                padding: 0 !important;
            }
            div[data-testid="stAppViewContainer"] > section.main {
                width: 100% !important;
                max-width: 100% !important;
                margin-left: 0px !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            /* Dynamic Sidebar Responsiveness & Content Layout */
            @media screen and (min-width: 992px) {
                /* When sidebar is visible, main content automatically adjusts margin */
                div[data-testid="stAppViewContainer"]:has(section[data-testid="stSidebar"]:not([data-collapsed="true"])) > section.main {
                    margin-left: 0px !important;
                }
            }

            @media screen and (max-width: 991px) {
                div[data-testid="stAppViewContainer"] > section.main {
                    margin-left: 0px !important;
                    width: 100% !important;
                    max-width: 100% !important;
                }
            }

        /* Sidebar Header & Brand Container Layout - 100% Fully Visible with No Top Clipping */
        div[data-testid="stSidebarHeader"] {
            display: flex !important;
            align-items: center !important;
            justify-content: flex-end !important;
            padding: 20px 16px 0px 16px !important;
            height: 56px !important;
            min-height: 56px !important;
            margin-bottom: 0px !important;
        }

        div[data-testid="stSidebarUserContent"] {
            padding-top: 0px !important;
            margin-top: 0px !important;
        }

        .sidebar-brand-container {
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            gap: 10px !important;
            height: 44px !important;
            margin-top: -44px !important; /* Safely align with arrow button inside the 56px padded header */
            margin-bottom: 28px !important;
            padding-left: 10px !important;
            padding-right: 52px !important;
        }

        div[data-testid="stSidebarUserContent"] > div[data-testid="stPageLink"]:first-of-type {
            margin-top: 0px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    render_top_header()


def render_top_header():
    """Renders the navigation in a modern horizontal top navbar at the top of the main page."""
    try:
        from backend.auth.authentication import restore_session_if_needed
        restore_session_if_needed()
    except Exception:
        pass
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

    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 42px; height: 42px; border-radius: 8px; display: block; object-fit: contain;" />' if logo_b64 else get_svg_icon('brand_logo', size=36)

    # Styling for the horizontal navbar container and links
    st.markdown("""
    <style>
        /* System Statistics Equal Width Grid Layout */
        .system-stats-grid {
            display: grid !important;
            grid-template-columns: repeat(4, 1fr) !important;
            gap: 20px !important;
            width: 100% !important;
            margin-top: 20px !important;
            margin-bottom: 20px !important;
            box-sizing: border-box !important;
        }
        @media screen and (max-width: 991px) {
            .system-stats-grid {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 14px !important;
            }
        }
        @media screen and (max-width: 480px) {
            .system-stats-grid {
                grid-template-columns: 1fr !important;
            }
        }

        /* Target the top navbar container by its Streamlit key to stretch edge-to-edge on Desktop */
        @media screen and (min-width: 992px) {
            div.st-key-navbar_container {
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            div.st-key-navbar_container div[data-testid="stVerticalBlockBorderWrapper"] {
                padding: 8px 24px !important;
                margin-top: 0px !important;
                margin-left: -0.5rem !important;
                margin-right: -0.5rem !important;
                margin-bottom: 24px !important;
                width: calc(100% + 1rem) !important;
                max-width: calc(100% + 1rem) !important;
                min-width: calc(100% + 1rem) !important;
                background-color: #ffffff !important;
                border-top: none !important;
                border-left: none !important;
                border-right: none !important;
                border-bottom: 1px solid #e2e8f0 !important;
                border-radius: 0px !important;
                box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
        }

        /* On Mobile/Tablet: style the navbar container as a neat centered card with correct margins and borders visible */
        @media screen and (max-width: 991px) {
            div.st-key-navbar_container {
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                box-sizing: border-box !important;
            }
            div.st-key-navbar_container div[data-testid="stVerticalBlockBorderWrapper"] {
                padding: 10px 16px !important;
                margin-top: 10px !important;
                margin-left: 0px !important;
                margin-right: 0px !important;
                margin-bottom: 20px !important;
                width: 100% !important;
                max-width: 100% !important;
                min-width: 100% !important;
                background-color: #ffffff !important;
                border: 1.5px solid #cbd5e1 !important;
                border-radius: 16px !important;
                box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05) !important;
                box-sizing: border-box !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
        }

        /* Zero out internal padding & margins inside the top navbar container to lock logo dead-center vertically */
        div.st-key-navbar_container div[data-testid="stHorizontalBlock"] {
            align-items: center !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div.st-key-navbar_container div[data-testid="column"] {
            display: flex !important;
            align-items: center !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div.st-key-navbar_container .element-container,
        div.st-key-navbar_container .stMarkdown {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            display: flex !important;
            align-items: center !important;
        }
        
        /* Top Navbar Horizontal Page Links Styling - Settled Equal Pills with High Contrast Dark Font */
        div.st-key-navbar_container div[data-testid="stPageLink"] {
            width: 100% !important;
            display: flex !important;
            justify-content: center !important;
        }
        div.st-key-navbar_container div[data-testid="stPageLink"] a {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 6px !important;
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            height: 40px !important;
            min-height: 40px !important;
            max-height: 40px !important;
            box-sizing: border-box !important;
            background-color: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            color: #0f172a !important;
            font-size: 13.5px !important;
            font-weight: 700 !important;
            padding: 0 8px !important;
            border-radius: 10px !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            text-align: center !important;
        }
        div.st-key-navbar_container div[data-testid="stPageLink"] a p,
        div.st-key-navbar_container div[data-testid="stPageLink"] a span,
        div.st-key-navbar_container div[data-testid="stPageLink"] a label,
        div.st-key-navbar_container div[data-testid="stPageLink"] a div,
        div.st-key-navbar_container div[data-testid="stPageLink"] a * {
            color: #0f172a !important;
            font-weight: 700 !important;
            font-size: 13.5px !important;
            margin: 0 !important;
            padding: 0 !important;
            white-space: nowrap !important;
        }
        div.st-key-navbar_container div[data-testid="stPageLink"] a:hover {
            background-color: #eef2ff !important;
            border-color: #c7d2fe !important;
            transform: translateY(-1px) !important;
        }
        div.st-key-navbar_container div[data-testid="stPageLink"] a:hover p,
        div.st-key-navbar_container div[data-testid="stPageLink"] a:hover span,
        div.st-key-navbar_container div[data-testid="stPageLink"] a:hover label,
        div.st-key-navbar_container div[data-testid="stPageLink"] a:hover div,
        div.st-key-navbar_container div[data-testid="stPageLink"] a:hover * {
            color: #4f46e5 !important;
            font-weight: 800 !important;
        }
        div.st-key-navbar_container div[data-testid="stPageLink"] a[aria-current="page"] {
            background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
            border-color: transparent !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
        }
        div.st-key-navbar_container div[data-testid="stPageLink"] a[aria-current="page"] p,
        div.st-key-navbar_container div[data-testid="stPageLink"] a[aria-current="page"] span,
        div.st-key-navbar_container div[data-testid="stPageLink"] a[aria-current="page"] label,
        div.st-key-navbar_container div[data-testid="stPageLink"] a[aria-current="page"] div,
        div.st-key-navbar_container div[data-testid="stPageLink"] a[aria-current="page"] * {
            color: #ffffff !important;
            font-weight: 800 !important;
        }

        /* Seamless Dark Theme Adaptability for the top navbar */
        @media (prefers-color-scheme: dark) and (min-width: 992px) {
            div.st-key-navbar_container div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #1a2238 !important;
                border-color: #2e3b5e !important;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
            }
        }
        @media (prefers-color-scheme: dark) and (max-width: 991px) {
            div.st-key-navbar_container div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #1e293b !important;
                border-color: #334155 !important;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # Determine pages based on role and authentication
    pages = []
    if not authenticated:
        pages = [
            ("app.py", "Home", "🏠"),
            ("pages/public_portal.py", "Public Portal", "🌐"),
            ("pages/cases.py", "Cases", "📁"),
            ("pages/map.py", "Map", "📍"),
            ("pages/login.py", "Login", "🔑"),
        ]

    # Sidebar navigation items with category section headers matching Image 2
    if not authenticated:
        sidebar_pages = [
            ("MAIN", "app.py", "Home", "🏠"),
            ("MAIN", "pages/public_portal.py", "Public Portal", "🌐"),
            ("CASE DIRECTORY", "pages/cases.py", "Case Directory", "📁"),
            ("CASE DIRECTORY", "pages/map.py", "Sighting Map", "📍"),
            ("CASE DIRECTORY", "pages/login.py", "Officer Login", "🔑"),
        ]
    elif role == "admin":
        sidebar_pages = [
            ("MAIN", "pages/admin_dashboard.py", "Dashboard", "📊"),
            ("MANAGEMENT", "pages/cases.py", "Register Case", "✍️"),
            ("MANAGEMENT", "pages/case_management.py", "Case Management", "📁"),
            ("MANAGEMENT", "pages/admin_face_matching.py", "AI Face Match", "🔍"),
            ("MANAGEMENT", "pages/video_sightings.py", "CCTV Surveillance", "📹"),
            ("MANAGEMENT", "pages/admin_map.py", "GIS Map", "📍"),
            ("OPERATIONS", "pages/admin_public_submissions.py", "Public Submissions", "🌐"),
            ("OPERATIONS", "pages/match_review.py", "Match Reviews", "⚖️"),
            ("SYSTEM", "app.py", "Portal Home", "🏠"),
        ]
    elif role == "officer":
        sidebar_pages = [
            ("MAIN", "pages/officer_dashboard.py", "Dashboard", "📊"),
            ("MANAGEMENT", "pages/cases.py", "Case Directory", "📁"),
            ("MANAGEMENT", "pages/map.py", "GIS Map", "📍"),
            ("MANAGEMENT", "pages/sightings.py", "Sighting Reports", "👁️"),
            ("OPERATIONS", "pages/public_portal.py", "Public Portal", "🌐"),
            ("SYSTEM", "app.py", "Portal Home", "🏠"),
        ]
    else:
        sidebar_pages = [
            ("MAIN", "app.py", "Home", "🏠"),
            ("MAIN", "pages/public_portal.py", "Public Portal", "🌐"),
            ("CASE DIRECTORY", "pages/cases.py", "Case Directory", "📁"),
            ("CASE DIRECTORY", "pages/map.py", "Sighting Map", "📍"),
            ("CASE DIRECTORY", "pages/login.py", "Officer Login", "🔑"),
        ]

    # Dynamically build horizontal layout using st.container & st.columns (ONLY for public guest navigation)
    if not authenticated:
        with st.container(key="navbar_container", border=True):
            # Logo (Left) + Middle Spacer + 5 Right-Aligned Settled Page Buttons
            col_spec = [2.2, 4.0] + [1.2] * len(pages)
            cols = st.columns(col_spec, vertical_alignment="center")
            
            # Left Logo & Brand Badge
            with cols[0]:
                st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; height: 40px; margin: 0; padding: 0;">
                    <div style="display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        {logo_html}
                    </div>
                    <div style="line-height: 1.15; display: flex; flex-direction: column; justify-content: center; text-align: left;">
                        <div style="font-size: 15px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px; white-space: nowrap; font-family: 'Outfit', sans-serif;">MPIS PORTAL</div>
                        <div style="font-size: 9px; color: #4f46e5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;">{role.upper()} PORTAL</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Right Page Links (Home, Public Portal, Cases, Map, Login)
            for i, (path, label, icon) in enumerate(pages):
                with cols[i + 2]:
                    st.page_link(path, label=label, icon=icon)

    # Render custom Deep Navy sidebar matching reference design (Image 2)
    st.sidebar.markdown(f"""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 24px; padding: 4px 6px;">
        <div style="width: 44px; height: 44px; border-radius: 50%; background: #ffffff; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3); flex-shrink: 0; padding: 4px;">
            {logo_html}
        </div>
        <div style="line-height: 1.2;">
            <div style="font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px; font-family: 'Outfit', sans-serif;">MPIS PORTAL</div>
            <div style="font-size: 9.5px; color: #93c5fd; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;">{role.upper()} MANAGEMENT SYSTEM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    current_cat = None
    for item in sidebar_pages:
        if len(item) == 4:
            cat, path, label, icon = item
            if cat != current_cat:
                current_cat = cat
                st.sidebar.markdown(f"<span class='sidebar-section-header'>{cat}</span>", unsafe_allow_html=True)
            st.sidebar.page_link(path, label=label, icon=icon)
        else:
            path, label, icon = item
            st.sidebar.page_link(path, label=label, icon=icon)

    st.sidebar.divider()

    if authenticated:
        import sys
        main_mod = sys.modules.get("__main__")
        page_file = getattr(main_mod, "__file__", "default_page")
        page_name = os.path.basename(page_file).replace(".py", "")
        
        username = user.get("username") or user.get("name", "User")
        user_role_str = user.get("role", "user").capitalize()
        user_initial = username[0].upper() if username else "U"

        st.sidebar.markdown(f"""
        <div class="sidebar-user-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 36px; height: 36px; border-radius: 50%; background: #dbeafe; color: #1e3a8a; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px;">
                    {user_initial}
                </div>
                <div style="line-height: 1.2;">
                    <div style="font-size: 13px; font-weight: 700; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px;">{username}</div>
                    <div style="font-size: 9.5px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">{user_role_str}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        logout_key = f"sidebar_logout_btn_{page_name}"
        if st.sidebar.button("🚪 Logout", key=logout_key, use_container_width=True):
            from backend.auth.authentication import logout_user
            logout_user()

        pass




def render_role_sidebar():
    """Backwards compatible alias that delegates to render_top_header()."""
    render_top_header()

