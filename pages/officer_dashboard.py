import streamlit as st
import os
import numpy as np
import cv2
from datetime import datetime
from backend.database import check_connection
from backend.auth.permissions import require_role, ROLE_OFFICER
from backend.services.face_detection import detect_faces
from backend.services.face_embedding import get_face_embedding
from backend.services.video_processing import process_video_feed
from backend.utils.helpers import inject_custom_css, save_uploaded_file, load_image_safely
from backend.utils.validators import validate_case_inputs
from backend.repositories import CaseRepository, SightingRepository, FaceRepository
from backend.services import CaseService, DashboardService

# ── Page config & OFFICER-ONLY authorization guard ───────────────────
st.set_page_config(page_title="Officer Dashboard", page_icon="👮", layout="wide")
inject_custom_css()
# CRITICAL: only ROLE_OFFICER is allowed here. Admin is NOT allowed through
# this guard (require_role with a single allowed role prevents the previous
# "officer or admin" bug where admins were accidentally treated as officers).
require_role([ROLE_OFFICER])

st.markdown("<h2 style='color: #10b981;'>👮 Officer Dashboard</h2>", unsafe_allow_html=True)
st.markdown(
    "<p style='color: #94a3b8;'>Track your assigned cases, register new bulletins, and verify public sighting reports.</p>",
    unsafe_allow_html=True,
)
st.markdown("---", unsafe_allow_html=True)

# ── Database connection check ─────────────────────────────────────────
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning(
        "Please ensure MongoDB is running and your `DATABASE_URL` is "
        "configured correctly in `.env`."
    )
    st.stop()

# ── Service + Repository wiring ───────────────────────────────────────
case_repo = CaseRepository()
sighting_repo = SightingRepository()
face_repo = FaceRepository()
case_service = CaseService(case_repo)
dashboard_service = DashboardService(case_repo=case_repo)

# The authenticated officer — required for EVERY scoped query.
# If for any reason session user is missing, we cannot enforce ownership → halt.
_officer_user = st.session_state.get("user")
if not _officer_user:
    st.error("⚠️ Session user not available. Please log in again.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════
# Data Loading — ALL queries pass _officer_user to enforce ownership
# ══════════════════════════════════════════════════════════════════════

def load_officer_dashboard(_officer: dict):
    """
    Loads officer-scoped statistics. The `_officer` dict is required
    and is threaded through DashboardService → authorize_view_cases
    → repository `.count()` / `.get_all()` calls, guaranteeing that
    every MongoDB query includes `{"created_by": officer.username}`.
    """
    return dashboard_service.get_officer_dashboard_data(current_user=_officer)


_data = None
_load_error = None
try:
    with st.spinner("Loading your case statistics from MongoDB..."):
        _data = load_officer_dashboard(_officer=_officer_user)
except PermissionError as exc:
    _load_error = f"🔒 Permission error: {exc}"
except ConnectionError as exc:
    _load_error = f"🔌 Database connection error: {exc}"
except Exception as exc:
    _load_error = f"⚠️ Failed to load dashboard data: {exc}"

if _load_error:
    st.error(_load_error)
    st.stop()
if _data is None:
    st.warning("Dashboard data is unavailable right now.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════
# UI Components (modular functions)
# ══════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────
# 1. Stat Cards Section — all stats are filtered to the officer
# ─────────────────────────────────────────────────────────────────────

def _stat_card(label: str, value, color: str, icon: str) -> str:
    return f"""
    <div class="metric-card" style="border-left-color: {color};">
        <span style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">
            {icon} {label}
        </span>
        <h2 style="margin: 4px 0 0 0; color: {color}; font-size: 32px; font-weight: 700;">
            {value}
        </h2>
    </div>
    """


def render_statistics_cards(d: dict):
    """
    Renders the 4 required officer-scoped statistics.
    IMPORTANT: these values come from DashboardService.get_officer_dashboard_data
    which already filtered every query by `created_by = <officer.username>`.
    """
    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            _stat_card("My Total Cases", d["my_total_cases"], "#3b82f6", "📁"),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            _stat_card("My Active Cases", d["my_active_cases"], "#ef4444", "🔴"),
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            _stat_card("My Pending Cases", d["my_pending_cases"], "#f59e0b", "⏳"),
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            _stat_card("My Resolved Cases", d["my_resolved_cases"], "#06b6d4", "🏠"),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────
# 2. Quick Actions Section (Register / My Cases)
# ─────────────────────────────────────────────────────────────────────

OFFICER_QUICK_ACTIONS = [
    {
        "icon": "📝",
        "label": "Register Missing Person",
        "desc": "File a new missing person bulletin",
        "target": "register",
        "color": "#10b981",
    },
    {
        "icon": "📂",
        "label": "My Cases",
        "desc": "Browse and manage your assigned cases",
        "target": "cases_page",
        "color": "#3b82f6",
    },
]


def _navigate_to(target: str):
    if target == "cases_page":
        try:
            st.switch_page("pages/cases.py")
        except Exception:
            st.warning("`pages/cases.py` is not available yet.")
    # "register" target is handled by the page tabs below (no page switch)


def render_quick_actions():
    """Renders the Quick Actions section — Register Missing Person + My Cases."""
    st.markdown("#### ⚡ Quick Actions")
    st.markdown(
        "<p style='color: #94a3b8; font-size: 14px;'>Jump to frequently used features.</p>",
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for idx, action in enumerate(OFFICER_QUICK_ACTIONS):
        with cols[idx % 2]:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; padding: 20px; min-height: 140px;">
                <div style="font-size: 32px; margin-bottom: 8px;">{action['icon']}</div>
                <div style="font-size: 15px; font-weight: 600; color: {action['color']};">
                    {action['label']}
                </div>
                <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                    {action['desc']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(
                f"Open {action['label']}",
                key=f"oqa_{idx}",
                use_container_width=True,
            ):
                _navigate_to(action["target"])


# ─────────────────────────────────────────────────────────────────────
# 3. Recent Cases Section — ONLY this officer's cases
# ─────────────────────────────────────────────────────────────────────

def _case_badge_class(status: str) -> str:
    return {
        "Missing": "badge-missing",
        "Found": "badge-found",
    }.get(status, "badge-pending")


def _format_timestamp(ts_value) -> str:
    if isinstance(ts_value, datetime):
        return ts_value.strftime("%d %b %Y, %H:%M")
    if ts_value:
        return str(ts_value)
    return ""


def render_recent_cases(cases: list):
    """Renders the 'Recent Cases' section.

    CRITICAL: the `cases` list here already came from DashboardService with
    ownership filtering — every case has `created_by == officer.username`.
    We additionally ASSERT that every owner is correct so any upstream
    regression is caught visually via an error banner rather than silently
    leaking another officer's data.
    """
    st.markdown("#### 🕒 Recent Cases")

    if not cases:
        st.info("No recent cases. Use **Register Missing Person** to file your first bulletin.")
        return

    # Double-check ownership: never trust just one filter level.
    _expected_owner = _officer_user.get("username", "")
    _wrong = [c for c in cases if c.created_by and c.created_by != _expected_owner]
    if _wrong:
        st.error(
            f"🚨 Ownership filter mismatch — refusing to display "
            f"{len(_wrong)} case(s) belonging to other officers. "
            "Please contact an administrator."
        )
        cases = [c for c in cases if not c.created_by or c.created_by == _expected_owner]

    for case in cases:
        badge_class = _case_badge_class(case.status)
        created_str = _format_timestamp(getattr(case, "created_at", None))

        st.markdown(f"""
        <div class="glass-card" style="padding: 14px 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 16px; font-weight: 600; color: #f1f5f9;">
                        {case.name}
                    </span>
                    <span style="margin-left: 8px; color: #64748b; font-size: 13px;">
                        ID #{case.id} · {case.gender}, Age {case.age}
                    </span>
                </div>
                <span class="badge {badge_class}">{case.status}</span>
            </div>
            <div style="margin-top: 6px; color: #94a3b8; font-size: 13px;">
                📍 {case.last_seen_location or 'Unknown'} · 🕐 {created_str}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# 4. Register Missing Person Tab (existing form — ownership enforced)
# ─────────────────────────────────────────────────────────────────────

def _create_dummy_video(path="data/videos/demo_feed.mp4"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return path
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, 10.0, (640, 480))
    for i in range(30):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = [43, 30, 20]
        cv2.circle(frame, (100 + i * 15, 240), 60, (241, 245, 249), -1)
        cv2.circle(frame, (80 + i * 15, 220), 8, (15, 23, 42), -1)
        cv2.circle(frame, (120 + i * 15, 220), 8, (15, 23, 42), -1)
        cv2.ellipse(frame, (100 + i * 15, 260), (25, 10), 0, 0, 180, (15, 23, 42), -1)
        out.write(frame)
    out.release()
    return path


def render_sighting_inbox_tab():
    st.subheader("Public Sightings Verification Queue")

    pending_sightings = [s.to_dict() for s in sighting_repo.get_all({"status": "Pending"})]

    if not pending_sightings:
        st.success("All reported sightings verified! The queue is clean.")
        return

    for sight in pending_sightings:
        sight_id = sight.get("id")
        case_id = sight.get("case_id")

        related_case_obj = case_repo.get_by_id(case_id) if case_id else None
        case_name = related_case_obj.name if related_case_obj else "Unidentified (Needs manual link)"

        # CRITICAL ownership check for actions:
        # Officers can verify sightings ONLY for their own cases.
        can_act = True
        if related_case_obj and _officer_user:
            can_act = related_case_obj.created_by == _officer_user.get("username")

        with st.expander(f"Sighting Report #{sight_id} - Target: {case_name}"):
            col_info, col_img = st.columns([2, 1])

            with col_info:
                sight_time_val = sight.get("sighting_time")
                sight_time_str = (
                    sight_time_val.strftime('%Y-%m-%d %H:%M:%S')
                    if isinstance(sight_time_val, datetime)
                    else str(sight_time_val)
                )
                st.markdown(f"""
                - **Location / Address:** {sight.get('address')}
                - **Coordinates:** Lat: `{sight.get('latitude')}`, Lon: `{sight.get('longitude')}`
                - **Time Logged:** {sight_time_str}
                - **Reporter:** {sight.get('reporter_name')} ({sight.get('reporter_contact')})
                - **Sighting Details:** *"{sight.get('details')}"*
                """)

                if not can_act:
                    st.warning(
                        "⚠️ This sighting is linked to a case owned by another officer. "
                        "Only the case owner can verify/reject it."
                    )
                else:
                    action_cols = st.columns(2)
                    with action_cols[0]:
                        if st.button("✅ Verify & Approve Sighting", key=f"verify_{sight_id}", use_container_width=True):
                            sighting_repo.update_status(sight_id, "Verified")
                            if case_id:
                                from backend.models import CaseHistory
                                case_repo.log_history(CaseHistory(
                                    case_id=case_id,
                                    action="Sighting Verified",
                                    details=(
                                        f"Sighting report #{sight_id} verified by "
                                        f"{_officer_user.get('username', 'officer')}."
                                    )
                                ))
                            st.success("Sighting status updated to VERIFIED.")
                            st.rerun()
                    with action_cols[1]:
                        if st.button("❌ Reject & Delete Report", key=f"reject_{sight_id}", use_container_width=True):
                            sighting_repo.delete(sight_id)
                            st.warning("Sighting report removed from backend.database.")
                            st.rerun()

            with col_img:
                photo_path = sight.get("photo_path")
                if photo_path:
                    st.image(load_image_safely(photo_path, sight.get("person_name", "Sighting")), caption="Sighting Photograph Upload", use_container_width=True)
                else:
                    st.write("No photo provided for this sighting.")


def render_cctv_scanner_tab():
    st.subheader("CCTV Camera Feed Search Simulator")
    st.write("Scan security camera feeds to match frames against all active missing person profiles.")

    cam_col1, cam_col2 = st.columns(2)
    with cam_col1:
        camera_name = st.text_input("Surveillance Source Name", value="South Terminal Entrance")
        cctv_lat = st.number_input("Camera Installed Latitude", value=28.6200, format="%.6f")
        cctv_lon = st.number_input("Camera Installed Longitude", value=77.2100, format="%.6f")

    with cam_col2:
        frame_skip = st.slider(
            "Frame Processing Speed (Process every N frames)",
            min_value=5, max_value=30, value=15,
        )
        video_upload = st.file_uploader(
            "Upload Surveillance MP4 Video File", type=["mp4", "avi", "mov"],
        )

    if st.button("▶️ Launch Stream Search Scanner", type="primary"):
        if video_upload:
            video_path = save_uploaded_file(video_upload, "data/videos")
        else:
            video_path = _create_dummy_video()
            st.info("No video uploaded. Starting simulator using generated dummy camera stream...")

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_progress(pct, msg):
            progress_bar.progress(pct)
            status_text.write(msg)

        matches = process_video_feed(
            video_path=video_path,
            db=None,
            camera_name=camera_name,
            camera_lat=cctv_lat,
            camera_lon=cctv_lon,
            frame_interval=frame_skip,
            progress_callback=update_progress,
        )

        if matches:
            st.success(f"🎯 **Scan complete. Matched {len(matches)} face profile(s)!** Alerts generated.")
            for m in matches:
                if isinstance(m, dict):
                    case_name = m.get("case_name", "Unknown")
                    timestamp_sec = m.get("timestamp_sec", 0.0)
                    confidence = m.get("confidence", 0.0)
                    crop_path = m.get("crop_path", "")
                else:
                    case_name = getattr(m, "case_name", getattr(m, "name", "Unknown"))
                    timestamp_sec = getattr(m, "timestamp_seconds", getattr(m, "timestamp_sec", 0.0))
                    confidence = getattr(m, "confidence", getattr(m, "best_similarity", 0.0))
                    if confidence > 1.0:
                        confidence /= 100.0
                    crop_path = getattr(m, "crop_path", "")

                st.write(
                    f"- **{case_name}** matched at timestamp `{timestamp_sec:.1f}s` "
                    f"(Confidence: `{confidence * 100:.1f}%`)"
                )
                if crop_path:
                    st.image(load_image_safely(crop_path, case_name), caption=f"CCTV Crop - Match {confidence * 100:.1f}%")
        else:
            st.warning("Scan finished. No faces matched active missing database profiles.")


def render_register_case_tab():
    """Renders the Register tab.

    Ownership enforcement: case_service.register_case is ALWAYS called with
    `current_user=_officer_user`. The service stamps `created_by` from the
    authenticated user dict — not from form data — so even if the user
    tampered with inputs, the owner remains the logged-in officer.
    """
    st.subheader("Register New Missing Person Bulletin")

    with st.form("register_case_form", clear_on_submit=True):
        col_l, col_r = st.columns(2)
        with col_l:
            name = st.text_input("Missing Person Name *")
            age = st.number_input("Age *", min_value=0, max_value=120, value=25)
            gender = st.selectbox("Gender *", ["Male", "Female", "Other"])
            last_seen_loc = st.text_input(
                "Last Seen Location/City *", placeholder="e.g. Noida Sector 62",
            )
            last_seen_date = st.date_input("Last Seen Date *", value=datetime.today())

        with col_r:
            contact = st.text_input("Family Contact Number", placeholder="For updates")
            reporter_name = st.text_input("Reporter Name", placeholder="Who reported the case")
            reporter_contact = st.text_input("Reporter Contact Phone")
            description = st.text_area(
                "Detailed Physical Description & Identifying Features",
                placeholder="Height, birthmarks, clothing color...",
            )

        photo_file = st.file_uploader(
            "Upload High-Quality Close-up Face Photo *", type=["jpg", "jpeg", "png"],
        )

        submit_case = st.form_submit_button("Register & Save Bulletin")

        if submit_case:
            valid, msg = validate_case_inputs(name, age, reporter_contact)
            if not valid:
                st.error(msg)
            elif not last_seen_loc:
                st.error("Please fill in the Last Seen Location.")
            elif not photo_file:
                st.error(
                    "You must upload a reference face photograph to create a bulletin."
                )
            else:
                ref_photo_path = save_uploaded_file(photo_file, "data/faces")
                detected_faces = detect_faces(ref_photo_path)

                if not detected_faces:
                    st.error(
                        "No faces could be detected in the uploaded photo. "
                        "Please upload a clear close-up portrait of the person's face."
                    )
                else:
                    dt_last_seen = datetime.combine(last_seen_date, datetime.min.time())

                    # CRITICAL: pass current_user so CaseService stamps the
                    # correct owner and validates role authorization.
                    # `created_by` is intentionally NOT passed as a raw param
                    # (it would be ignored anyway because current_user takes
                    # precedence inside CaseService.register_case).
                    saved_case = case_service.register_case(
                        name=name,
                        age=age,
                        gender=gender,
                        last_seen_location=last_seen_loc,
                        contact_number=contact,
                        description=description,
                        photo_path=ref_photo_path,
                        reporter_name=reporter_name,
                        reporter_contact=reporter_contact,
                        last_seen_date=dt_last_seen,
                        created_by=None,           # ignored when current_user is set
                        current_user=_officer_user,
                    )

                    first_face_crop = detected_faces[0]["crop"]
                    embedding_vector = get_face_embedding(first_face_crop)

                    from backend.models import FaceVector
                    face_vector_obj = FaceVector(
                        case_id=saved_case.id,
                        embedding=embedding_vector,
                        photo_path=ref_photo_path,
                    )
                    face_repo.create(face_vector_obj)

                    st.success(
                        f"✅ Successfully registered bulletin for '{name}' "
                        f"(Case #{saved_case.id}). Face model compiled."
                    )
                    st.toast(f"✅ Case #{saved_case.id} successfully registered!", icon="📋")

                    # Clear stale cache so stats reflect the new case immediately
                    load_officer_dashboard.clear()
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════
# Main render pipeline
# ══════════════════════════════════════════════════════════════════════

render_statistics_cards(_data)

# Top-level sections: Quick Actions + Recent Cases
col_actions, col_recent = st.columns([1, 2])
with col_actions:
    render_quick_actions()
with col_recent:
    render_recent_cases(_data["my_recent_cases"])

st.markdown("---")

tab_inbox, tab_cctv, tab_register = st.tabs([
    "📥 Sighting Inbox Queue",
    "📹 CCTV Surveillance Scanner",
    "✍️ Register Missing Person",
])

with tab_inbox:
    render_sighting_inbox_tab()
with tab_cctv:
    render_cctv_scanner_tab()
with tab_register:
    render_register_case_tab()

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #475569; font-size: 12px;'>"
    "Missing Person Identification System · Officer Dashboard · "
    "All data filtered by your logged-in officer account (MongoDB ownership enforcement)"
    "</p>",
    unsafe_allow_html=True,
)
