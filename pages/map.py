"""
India Case Density & Sightings Tracking Map Page.
Uses MapService to render India overview, case density heatmaps, and city/state statistics.
"""

import streamlit as st
from streamlit_folium import st_folium
from backend.database import check_connection
from backend.auth.permissions import require_role
from backend.utils.helpers import inject_custom_css
from backend.services.map_service import MapService

# Page Setup
st.set_page_config(page_title="India Case Map", page_icon="🗺️", layout="wide")
inject_custom_css()
require_role(["admin", "officer"])

st.markdown("<h2 style='color: #10b981; margin-bottom: 0;'>🗺️ India Live Case & Density Dashboard</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Geographic case density, state-level aggregation, and city clusters for active and resolved missing person cases across India.</p>", unsafe_allow_html=True)
st.markdown("---", unsafe_allow_html=True)

# Database Connection Check
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning("Please ensure MongoDB is running and configured correctly in `.env`.")
    st.stop()

# Initialize Map Service
map_service = MapService()
current_user = st.session_state.get("user")

# ── Control Filters Section ──────────────────────────────────────────
st.markdown("#### ⚙️ Map Display Filters & Controls")
fcol1, fcol2, fcol3, fcol4 = st.columns([2, 2, 3, 2])

with fcol1:
    status_choice = st.selectbox(
        "Case Status",
        options=["All", "Active", "Resolved", "Closed"],
        index=0,
        key="map_filter_status_page",
    )

with fcol2:
    time_choice = st.selectbox(
        "Time Range",
        options=["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
        index=0,
        key="map_filter_time_page",
    )

days_param = None
if time_choice == "Last 7 Days":
    days_param = 7
elif time_choice == "Last 30 Days":
    days_param = 30
elif time_choice == "Last 90 Days":
    days_param = 90

try:
    initial_data = map_service.get_map_dashboard_data(
        user=current_user,
        status_filter=status_choice,
        days_filter=days_param,
        state_filter="All India",
    )
    all_indian_states = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu & Kashmir",
        "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
        "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
        "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
        "Uttar Pradesh", "Uttarakhand", "West Bengal"
    ]
    db_states = [
        s["state"] for s in initial_data.get("states_summary", [])
        if s.get("state") and s.get("state") != "Unknown State"
    ]
    available_states = ["All India"] + sorted(list(set(all_indian_states + db_states)))
except Exception as exc:
    st.error(f"Failed to load map statistics: {exc}")
    st.stop()

with fcol3:
    state_choice = st.selectbox(
        "Geographic State",
        options=available_states,
        index=0,
        key="map_filter_state_page",
    )

with fcol4:
    st.write("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Map Data", use_container_width=True, key="btn_refresh_map_page"):
        st.cache_data.clear()
        st.rerun()

# Fetch Map Data
map_data = map_service.get_map_dashboard_data(
    user=current_user,
    status_filter=status_choice,
    days_filter=days_param,
    state_filter=state_choice,
)

summary = map_data.get("summary", {})

# Summary Metrics
m1, m2, m3, m4, m5, m6 = st.columns(6)

def _metric_box(label: str, value: int, color: str, icon: str):
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: {color}; padding: 12px 14px;">
        <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">{icon} {label}</span>
        <h3 style="margin: 2px 0 0 0; color: {color}; font-size: 26px; font-weight: 700;">{value}</h3>
    </div>
    """, unsafe_allow_html=True)

with m1:
    _metric_box("Total Cases", summary.get("total_cases", 0), "#3b82f6", "📁")
with m2:
    _metric_box("Active (Missing)", summary.get("active_cases", 0), "#ef4444", "🔴")
with m3:
    _metric_box("Resolved (Found)", summary.get("resolved_cases", 0), "#10b981", "✅")
with m4:
    _metric_box("States Affected", summary.get("states_affected", 0), "#8b5cf6", "🗺️")
with m5:
    _metric_box("Cities Affected", summary.get("cities_affected", 0), "#f59e0b", "🏙️")
with m6:
    _metric_box("Unmapped Locs", summary.get("locations_unavailable", 0), "#64748b", "⚠️")

st.markdown("<br>", unsafe_allow_html=True)

# Folium Map
st.markdown("### 🗺️ India Geographic Case Density & Location Clusters")
folium_map = map_service.generate_india_folium_map(map_data)
st_folium(folium_map, width=1200, height=520)

st.markdown("---")

# Summary Tables
tcol1, tcol2 = st.columns(2)

with tcol1:
    st.markdown("#### 🏛️ State-Level Case Summary")
    states_summary = map_data.get("states_summary", [])
    if not states_summary:
        st.info("No state data available.")
    else:
        st.dataframe(
            [{"State": s["state"], "Total Cases": s["total_cases"], "Active (Missing)": s["active_cases"], "Resolved (Found)": s["resolved_cases"]} for s in states_summary],
            use_container_width=True,
            hide_index=True,
        )

with tcol2:
    st.markdown("#### 🏙️ City-Level Case Summary")
    cities_summary = map_data.get("cities_summary", [])
    if not cities_summary:
        st.info("No city data available.")
    else:
        st.dataframe(
            [{"City": c["city"], "State": c["state"], "Total Cases": c["total_cases"], "Active (Missing)": c["active_cases"], "Resolved (Found)": c["resolved_cases"]} for c in cities_summary],
            use_container_width=True,
            hide_index=True,
        )
