import streamlit as st
from datetime import datetime
from backend.database import check_connection
from backend.auth.permissions import require_role, ROLE_ADMIN
from backend.utils.helpers import inject_custom_css
from backend.services.dashboard_service import DashboardService

# ── Page config & auth guard ─────────────────────────────────────────
st.set_page_config(page_title="Admin Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
inject_custom_css()
require_role([ROLE_ADMIN])

# ── Database connection check ─────────────────────────────────────────
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning(
        "Please ensure MongoDB is running and your `DATABASE_URL` is "
        "configured correctly in `.env`."
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════
# Data Loading (via DashboardService — no repo logic or queries in UI)
# ══════════════════════════════════════════════════════════════════════

def load_dashboard_data(_current_user: dict | None = None):
    """
    Loads all dashboard statistics from MongoDB via DashboardService.

    The `_current_user` prefix tells Streamlit not to hash the user dict
    (it's not hashable in all cases), while still passing it to the service
    for role-based filtering.
    """
    dashboard_service = DashboardService()
    return dashboard_service.get_dashboard_data(current_user=_current_user)


# ── Load data with spinner and graceful error handling ────────────────

current_user = st.session_state.get("user")
data = None
load_error = None

try:
    with st.spinner("Loading dashboard data from MongoDB..."):
        data = load_dashboard_data(_current_user=current_user)
except PermissionError as exc:
    load_error = f"🔒 Permission error: {exc}"
except ConnectionError as exc:
    load_error = f"🔌 Database connection error: {exc}"
except Exception as exc:
    load_error = f"⚠️ Failed to load dashboard data: {exc}"

if load_error:
    st.error(load_error)
    st.info("Please try again in a few moments or contact support if the issue persists.")
    st.stop()

if data is None:
    st.warning("Dashboard data is unavailable right now.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════
# UI Components (modular, each section is a separate function)
# ══════════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────────────
# 1. Header Section
# ──────────────────────────────────────────────────────────────────────

def render_header():
    """Renders the dashboard title, welcome message, and refresh timestamp."""
    user = st.session_state.get("user", {})
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="header-left">
            <h1 class="header-title">Dashboard</h1>
            <p class="header-subtitle">Plan, prioritize, and accomplish case investigations with ease.</p>
        </div>
        <div class="header-right">
            <div class="role-badge">
                👑 {user.get('username', 'Admin').upper()} (ADMIN)
            </div>
            <div class="refresh-time">Last refreshed: {datetime.now().strftime('%H:%M:%S')}</div>
        </div>
    </div>

    <style>
    .dashboard-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 18px;
        border-bottom: 1px solid #e2e8f0;
        gap: 16px;
    }}
    .header-title {{
        color: #0f172a;
        margin: 0;
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.5px;
    }}
    .header-subtitle {{
        color: #64748b;
        margin: 4px 0 0 0;
        font-size: 14px;
    }}
    .header-right {{
        text-align: right;
        flex-shrink: 0;
    }}
    .role-badge {{
        background: #eef2ff;
        color: #4f46e5;
        font-weight: 700;
        padding: 6px 16px;
        border-radius: 9999px;
        font-size: 13px;
        display: inline-block;
        margin-bottom: 4px;
        border: 1px solid #c7d2fe;
        white-space: nowrap;
    }}
    .refresh-time {{
        color: #94a3b8;
        font-size: 12px;
    }}

    @media screen and (max-width: 767px) {{
        .dashboard-header {{
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
        }}
        .header-right {{
            text-align: left;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .role-badge {{
            margin-bottom: 0;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# 2. Statistic Cards Section
# ──────────────────────────────────────────────────────────────────────

def _stat_card(label: str, value, color: str, icon: str, is_hero: bool = False, sub_text: str = "") -> str:
    """Returns HTML for a single Donezo-style statistic card."""
    if is_hero:
        return f"""
        <div class="donezo-hero-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 13.5px; font-weight: 600; opacity: 0.9; text-transform: capitalize;">{label}</span>
                <span style="background: rgba(255,255,255,0.2); width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px;">↗</span>
            </div>
            <h1 style="font-size: 38px; font-weight: 800; margin: 0 0 10px 0; color: #ffffff; line-height: 1;">{value}</h1>
            <div style="font-size: 11.5px; opacity: 0.85; font-weight: 500;">
                <span style="background: rgba(255,255,255,0.25); padding: 2px 8px; border-radius: 6px; margin-right: 4px;">↗</span> {sub_text or 'System Active'}
            </div>
        </div>
        """
    return f"""
    <div class="donezo-metric-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 13.5px; font-weight: 700; color: #334155; text-transform: capitalize;">{label}</span>
            <span class="arrow-icon-circle" style="border: 1px solid #cbd5e1; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; color: #475569; transition: all 0.3s ease;">↗</span>
        </div>
        <h1 style="font-size: 36px; font-weight: 800; margin: 0 0 10px 0; color: #0f172a; line-height: 1;">{value}</h1>
        <div style="font-size: 12px; color: #64748b; font-weight: 600;">
            <span style="color: {color}; font-weight: 800; margin-right: 4px;">●</span> {sub_text or 'Updated live'}
        </div>
    </div>
    """


def render_statistics_cards(d: dict):
    """Renders the 8 dashboard statistics as a perfectly aligned 4x2 grid with ample gap spacing."""
    row1 = st.columns(4, gap="large")
    row2 = st.columns(4, gap="large")

    with row1[0]:
        st.markdown(_stat_card("Total Cases", d["total_cases"], "#4f46e5", "📁", sub_text="Total Registered"), unsafe_allow_html=True)
    with row1[1]:
        st.markdown(_stat_card("Active Cases", d["active_cases"], "#ef4444", "🔴", sub_text="Investigation Active"), unsafe_allow_html=True)
    with row1[2]:
        st.markdown(_stat_card("Pending Review", d["pending_review"], "#f59e0b", "⏳", sub_text="Requires Attention"), unsafe_allow_html=True)
    with row1[3]:
        st.markdown(_stat_card("Potential Matches", d["potential_matches"], "#8b5cf6", "🔗", sub_text="AI Engine Hits"), unsafe_allow_html=True)

    with row2[0]:
        st.markdown(_stat_card("Confirmed Matches", d["confirmed_matches"], "#10b981", "✅", sub_text="Verified Match"), unsafe_allow_html=True)
    with row2[1]:
        st.markdown(_stat_card("Resolved Cases", d["resolved_cases"], "#06b6d4", "🏠", sub_text="Reunited / Closed"), unsafe_allow_html=True)
    with row2[2]:
        st.markdown(_stat_card("Video Sightings", d["video_sightings"], "#ec4899", "🎥", sub_text="CCTV Feeds"), unsafe_allow_html=True)
    with row2[3]:
        st.markdown(_stat_card("Public Reports", d.get("public_submissions", 0), "#6366f1", "🌐", sub_text="Citizen Submissions"), unsafe_allow_html=True)



# ──────────────────────────────────────────────────────────────────────
# 3. Recent Cases Section
# ──────────────────────────────────────────────────────────────────────

def _case_badge_class(status: str) -> str:
    return {
        "Missing": "badge-missing",
        "Found": "badge-found",
    }.get(status, "badge-pending")


def _format_timestamp(ts_value) -> str:
    """Formats a date/datetime/str value to a friendly display string."""
    if isinstance(ts_value, datetime):
        return ts_value.strftime("%d %b %Y, %H:%M")
    if ts_value:
        return str(ts_value)
    return ""


def render_recent_cases(cases: list):
    """Renders the 'Recent Cases' tab content."""
    st.markdown("#### 📂 Recently Registered Cases")
    if not cases:
        st.info("No cases registered yet. Head to **Register Case** to file the first bulletin.")
        st.page_link("pages/cases.py", label="✍️ Register New Case Now", icon="➕")
        return

    for case in cases:
        badge_class = _case_badge_class(case.status)
        created_str = _format_timestamp(getattr(case, "created_at", None))

        st.markdown(f"""
<div class="glass-card" style="padding: 16px 22px; margin-bottom: 14px;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span style="font-size: 17px; font-weight: 700; color: #0f172a;">
                {case.name}
            </span>
            <span style="margin-left: 10px; color: #334155; font-size: 13.5px; font-weight: 600;">
                ID #{case.id} · {case.gender}, Age {case.age}
            </span>
        </div>
        <span class="badge {badge_class}">{case.status}</span>
    </div>
    <div style="margin-top: 8px; color: #334155; font-size: 13.5px; font-weight: 500;">
        📍 <strong style="color: #1e293b;">{case.last_seen_location or 'Unknown'}</strong> · 🕐 {created_str}
        {f" · 👤 By <strong style='color: #4338ca;'>{case.created_by}</strong>" if case.created_by else ""}
    </div>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# 4. Recent Potential Matches Section
# ──────────────────────────────────────────────────────────────────────

def _match_status_color(status: str) -> str:
    return {
        "Pending Review": "#d97706",
        "Confirmed Match": "#16a34a",
        "False Positive": "#dc2626",
    }.get(status, "#64748b")


def render_recent_matches(matches: list):
    """Renders the 'Recent Potential Matches' tab content."""
    st.markdown("#### 🔗 Recent Potential Matches")
    if not matches:
        st.info("No match results recorded yet. Run the **Face Matching** engine to generate biometric comparisons.")
        return

    for match in matches:
        status_color = _match_status_color(match.status)

        st.markdown(f"""
<div class="glass-card" style="padding: 16px 22px; margin-bottom: 14px;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span style="font-size: 17px; font-weight: 700; color: #0f172a;">
                Match #{match.id}
            </span>
            <span style="margin-left: 10px; color: #334155; font-size: 13.5px; font-weight: 600;">
                Case #{match.case_id} ↔ Sighting #{match.sighting_id}
            </span>
        </div>
        <span style="color: {status_color}; font-weight: 700; font-size: 13.5px; background: rgba(0,0,0,0.04); padding: 4px 10px; border-radius: 6px;">
            {match.status}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# 5. Case Status Summary Section
# ──────────────────────────────────────────────────────────────────────

def render_case_status_summary(status_breakdown: dict, total_sightings: int, video_sightings: int):
    """Renders the 'Case Status Summary' tab content with breakdown cards."""
    st.markdown("#### 📈 Case Status Breakdown")

    if not status_breakdown:
        st.info("No case status data available yet.")
    else:
        total = sum(status_breakdown.values())

        status_config = {
            "Missing": {"color": "#ef4444", "icon": "🔴", "desc": "Active missing person bulletins"},
            "Found": {"color": "#10b981", "icon": "✅", "desc": "Successfully located and reunited"},
            "Closed": {"color": "#64748b", "icon": "📁", "desc": "Investigations closed"},
        }

        cols = st.columns(max(len(status_breakdown), 1), gap="medium")
        for idx, (status, count) in enumerate(sorted(status_breakdown.items())):
            cfg = status_config.get(status, {"color": "#94a3b8", "icon": "📋", "desc": status})
            with cols[idx % len(cols)]:
                pct = (count / total * 100) if total else 0
                st.markdown(f"""
                <div class="glass-card" style="text-align: center; padding: 24px; margin-bottom: 16px;">
                    <div style="font-size: 36px; margin-bottom: 8px;">{cfg['icon']}</div>
                    <div style="font-size: 32px; font-weight: 700; color: {cfg['color']};">{count}</div>
                    <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin: 4px 0;">
                        {status}
                    </div>
                    <div style="font-size: 12px; color: #64748b;">{cfg['desc']}</div>
                    <div style="margin-top: 10px;">
                        <div style="background: #e2e8f0; border-radius: 4px; height: 6px; overflow: hidden;">
                            <div style="width: {pct:.0f}%; height: 100%; background: {cfg['color']}; border-radius: 4px;"></div>
                        </div>
                        <span style="font-size: 11px; color: #64748b; font-weight: 600;">{pct:.1f}% of total</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Sightings summary row
    st.markdown("<div style='margin: 24px 0 16px 0;'><hr style='border: none; border-top: 1px solid #e2e8f0;' /></div>", unsafe_allow_html=True)
    st.markdown("#### 📍 Sightings Overview")
    sc1, sc2 = st.columns(2, gap="medium")
    with sc1:
        st.markdown(
            _stat_card("Total Sightings", total_sightings, "#3b82f6", "📍"),
            unsafe_allow_html=True,
        )
    with sc2:
        st.markdown(
            _stat_card("Video-Sourced Sightings", video_sightings, "#ec4899", "🎥"),
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────────────────
# 6. Quick Actions Section
# ──────────────────────────────────────────────────────────────────────

from backend.utils.icons import get_svg_icon

QUICK_ACTIONS = [
    {
        "icon": get_svg_icon("folder", size=32, color="#10b981"),
        "label": "Register Missing Person",
        "desc": "File a new missing person bulletin",
        "page": "pages/cases.py",
        "color": "#10b981",
    },
    {
        "icon": get_svg_icon("face_scan", size=32, color="#8b5cf6"),
        "label": "Face Matching",
        "desc": "Run biometric face comparison engine",
        "page": "pages/admin_face_matching.py",
        "color": "#8b5cf6",
    },
    {
        "icon": get_svg_icon("video", size=32, color="#ec4899"),
        "label": "Video Sightings",
        "desc": "Process surveillance video feeds",
        "page": "pages/video_sightings.py",
        "color": "#ec4899",
    },
    {
        "icon": get_svg_icon("check", size=32, color="#f59e0b"),
        "label": "Match Review",
        "desc": "Review and confirm/reject potential matches",
        "page": "pages/match_review.py",
        "color": "#f59e0b",
    },
    {
        "icon": get_svg_icon("map_pin", size=32, color="#06b6d4"),
        "label": "India Map",
        "desc": "View sighting locations on the map",
        "page": "pages/map.py",
        "color": "#06b6d4",
    },
    {
        "icon": get_svg_icon("inbox", size=32, color="#10b981"),
        "label": "Public Submissions",
        "desc": "Review and verify public reports",
        "page": "pages/admin_public_submissions.py",
        "color": "#10b981",
    },
]


def _navigate_to(page_path: str):
    """Attempts a Streamlit page switch, warning if the page is unavailable."""
    try:
        st.switch_page(page_path)
    except Exception:
        st.warning(f"Page `{page_path}` is not available yet.")


def render_quick_actions():
    """Renders the 'Quick Actions' tab content with navigation cards."""
    st.markdown("#### ⚡ Quick Actions")
    st.markdown(
        "<p style='color: #64748b; font-size: 14px; margin-bottom: 20px;'>Jump to frequently used modules.</p>",
        unsafe_allow_html=True,
    )

    cols = st.columns(3, gap="medium")
    for idx, action in enumerate(QUICK_ACTIONS):
         with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"""
                <div style="text-align: center; padding: 10px 0 0 0;">
                    <div style="font-size: 32px; margin-bottom: 8px;">{action['icon']}</div>
                    <div style="font-size: 16px; font-weight: 700; color: {action['color']};">
                        {action['label']}
                    </div>
                    <div style="font-size: 12.5px; color: #64748b; margin-top: 6px; margin-bottom: 12px;">
                        {action['desc']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(
                    f"Open {action['label']}",
                    key=f"qa_{idx}",
                    use_container_width=True,
                ):
                    _navigate_to(action["page"])


# ──────────────────────────────────────────────────────────────────────
# 7. Footer
# ──────────────────────────────────────────────────────────────────────

def render_footer():
    """Renders the dashboard footer."""
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #475569; font-size: 12px; margin-top: 24px;'>"
        "Missing Person Identification System · Admin Dashboard · "
        "Data sourced from MongoDB"
        "</p>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════
# Main Render — assemble sections in order with generous spacing
# ══════════════════════════════════════════════════════════════════════

render_header()
render_statistics_cards(data)

st.markdown("<div style='margin-bottom: 28px;'></div>", unsafe_allow_html=True)

tab_cases, tab_matches, tab_status, tab_actions = st.tabs([
    "📂 Recent Cases",
    "🔗 Recent Potential Matches",
    "📈 Case Status Summary",
    "⚡ Quick Actions",
])

with tab_cases:
    render_recent_cases(data["recent_cases"])
with tab_matches:
    render_recent_matches(data["recent_matches"])
with tab_status:
    render_case_status_summary(
        status_breakdown=data["case_status_breakdown"],
        total_sightings=data["total_sightings"],
        video_sightings=data["video_sightings"],
    )
with tab_actions:
    render_quick_actions()

render_footer()
