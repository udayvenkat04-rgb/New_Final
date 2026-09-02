"""
Case Management Page — Phase 11.

Full case lifecycle management with strict RBAC enforcement at the service layer.

ADMIN:  View / Search / Filter all cases, Edit any, Delete (soft) any, View history
OFFICER: View / Search / Filter own cases only, Edit own, Cannot delete

The service layer enforces ownership — the UI cannot leak data across officers
even if DOM manipulation is attempted, because CaseService merges the created_by
ownership filter into every query.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, time

from backend.database import check_connection
from backend.auth.permissions import require_role, ROLE_ADMIN, ROLE_OFFICER, is_admin
from backend.utils.helpers import inject_custom_css, load_image_safely
from backend.utils.validators import (
    validate_image_upload,
    validate_email,
    validate_phone,
    validate_age,
    validate_required,
    MAX_IMAGE_BYTES,
    STATUS_ACTIVE,
)
from backend.repositories.case_repository import CaseRepository
from backend.services.case_service import CaseService

# ── Page setup + authorization guard ─────────────────────────────────
st.set_page_config(page_title="Case Management", page_icon="🛡️", layout="wide")
inject_custom_css()
require_role([ROLE_OFFICER, ROLE_ADMIN])

cm_col1, cm_col2 = st.columns([3, 1], vertical_alignment="center")
with cm_col1:
    st.markdown(
        "<h2 style='color: #10b981; margin: 0;'>🛡️ Case Management Centre</h2>",
        unsafe_allow_html=True,
    )
    role_label = "Administrator" if is_admin() else "Officer"
    st.markdown(
        f"<p style='color: #94a3b8; margin: 0;'>"
        f"Role: <b style='color:#f1f5f9;'>{role_label}</b> — "
        f"{'Full access to all cases across officers.' if is_admin() else 'Access limited to cases you registered.'}"
        f"</p>",
        unsafe_allow_html=True,
    )
with cm_col2:
    st.page_link("pages/cases.py", label="✍️ Register New Case", icon="➕", use_container_width=True)
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

case_repo = CaseRepository()
case_service = CaseService(case_repo)

current_user = st.session_state.get("user") or {}
if not current_user:
    st.error("⚠️ No authenticated user in session. Please log in again.")
    st.stop()

current_username = current_user.get("username", "")
current_role = current_user.get("role", "")

# ── Session-state UI plumbing ────────────────────────────────────────
CM_UI = st.session_state.setdefault("cm_ui", {
    "view_case_id": None,
    "edit_case_id": None,
    "delete_confirm_id": None,
    "delete_case_number": "",
    "delete_name": "",
    "banner": None,  # {"type": "success|error|info", "msg": "..."}
})


def _clear_banner():
    CM_UI["banner"] = None


def _set_banner(type_, msg):
    CM_UI["banner"] = {"type": type_, "msg": msg}


def _status_badge(status: str) -> str:
    if status in ("Missing", STATUS_ACTIVE):
        cls = "badge-missing"
    elif status in ("Found",):
        cls = "badge-found"
    else:
        cls = "badge-pending"
    return f'<span class="badge {cls}">{status}</span>'


def _format_dt(val):
    if val is None:
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    return str(val)[:16]


# ══════════════════════════════════════════════════════════════════════
# Render: Persisted banner (survives reruns)
# ══════════════════════════════════════════════════════════════════════

def render_banner():
    banner = CM_UI.get("banner")
    if banner:
        t, m = banner.get("type"), banner.get("msg")
        if t == "success":
            st.success(m)
        elif t == "error":
            st.error(m)
        elif t == "info":
            st.info(m)


render_banner()

# ══════════════════════════════════════════════════════════════════════
# RENDER: View Case Details Modal (expander-style section)
# ══════════════════════════════════════════════════════════════════════

def render_view_case(case_id: int):
    """Full case detail view + case history timeline."""
    try:
        with st.spinner("Loading case details…"):
            case = case_service.get_case(case_id, current_user=current_user)
    except PermissionError as exc:
        _set_banner("error", f"🔒 Access denied: {exc}")
        CM_UI["view_case_id"] = None
        st.rerun()
        return

    if case is None:
        _set_banner("error", "Case not found (it may have been deleted).")
        CM_UI["view_case_id"] = None
        st.rerun()
        return

    back_col, title_col = st.columns([1, 10])
    with back_col:
        if st.button("← Back to list", key="cm_view_back"):
            CM_UI["view_case_id"] = None
            CM_UI["edit_case_id"] = None
            st.rerun()

    st.markdown(f"### 📄 Case: `{case.case_number or 'Unassigned'}` — {case.name}")

    can_edit = (
        (current_role == ROLE_ADMIN)
        or (current_role == ROLE_OFFICER and case.created_by == current_username)
    )
    can_delete = (current_role == ROLE_ADMIN)

    # Action row
    act1, act2, act3, *_ = st.columns([1, 1, 1, 5])
    with act1:
        if can_edit:
            if st.button("✏️ Edit Case", key="cm_goto_edit", type="secondary"):
                CM_UI["edit_case_id"] = case_id
                st.rerun()
    with act2:
        if can_delete:
            if st.button("🗑️ Delete Case", key="cm_goto_delete", type="secondary"):
                CM_UI["delete_confirm_id"] = case_id
                CM_UI["delete_case_number"] = case.case_number or ""
                CM_UI["delete_name"] = case.name
                CM_UI["view_case_id"] = None
                st.rerun()

    # ── Detail grid ──────────────────────────────────────────────────
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        st.markdown("#### Photograph")
        st.image(load_image_safely(case.photo_path, case.name), use_container_width=True)

    with d_col2:
        info_cols = st.columns(2)
        with info_cols[0]:
            st.markdown(
                f"**Status:** {_status_badge(case.status)}",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Full Name:** {case.name}")
            st.markdown(f"**Age:** {case.age}")
            st.markdown(f"**Gender:** {case.gender}")
            st.markdown(f"**Last Seen Date:** {_format_dt(case.last_seen_date)}")
            st.markdown(f"**Last Seen Location:** {case.last_seen_location or '—'}")

        with info_cols[1]:
            st.markdown(f"**City:** {case.last_seen_city or '—'}")
            st.markdown(f"**State:** {case.last_seen_state or '—'}")
            st.markdown(f"**Contact Person:** {case.contact_name or '—'}")
            st.markdown(f"**Contact Email:** {case.contact_email or '—'}")
            st.markdown(f"**Contact Phone:** {case.contact_phone or '—'}")
            st.markdown(f"**Registered By:** `{case.created_by or '—'}`")
            st.markdown(f"**Created:** {_format_dt(case.created_at)}")
            st.markdown(f"**Last Updated:** {_format_dt(case.updated_at)}")

    st.markdown("#### Description & Identifiers")
    st.write(case.description or "*No physical descriptors recorded.*")

    st.markdown("---")

    # ── Phase 23: Lifecycle State Machine Actions (Admin Only for State Changes) ──
    from backend.services.case_lifecycle_service import CaseLifecycleService
    lifecycle_svc = CaseLifecycleService()

    if current_user and current_user.get("role") == "admin":
        st.markdown("#### ⚙️ Administrative Lifecycle Actions")
        c_status = lifecycle_svc.normalize_status(case.status)

        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if c_status in ("ACTIVE_INVESTIGATION", "MATCH_CONFIRMED"):
                with st.popover("✅ Resolve Case"):
                    res_type = st.selectbox("Resolution Type", ["Found Safe", "Reunited with Family", "Located via Match", "Other"], key=f"res_type_{case_id}")
                    res_notes = st.text_area("Resolution Notes *", placeholder="Enter resolution details...", key=f"res_notes_{case_id}")
                    if st.button("Confirm Resolution", key=f"btn_confirm_res_{case_id}"):
                        if not res_notes.strip():
                            st.warning("Resolution notes are required.")
                        else:
                            ok_res, msg_res = lifecycle_svc.resolve_case(case_id, current_user, res_type, res_notes)
                            if ok_res:
                                _set_banner("success", msg_res)
                                st.rerun()
                            else:
                                st.error(msg_res)

        with ac2:
            if c_status == "RESOLVED":
                with st.popover("🔒 Close Case Bulletin"):
                    close_notes = st.text_area("Closing Notes", placeholder="Enter closing notes...", key=f"close_notes_{case_id}")
                    if st.button("Confirm Case Closure", key=f"btn_confirm_close_{case_id}"):
                        ok_cl, msg_cl = lifecycle_svc.close_case(case_id, current_user, notes=close_notes)
                        if ok_cl:
                            _set_banner("success", msg_cl)
                            st.rerun()
                        else:
                            st.error(msg_cl)

        with ac3:
            if c_status == "CLOSED":
                with st.popover("🔄 Reopen Case"):
                    reopen_reason = st.text_area("Reopening Reason *", placeholder="Reason to reopen case...", key=f"reopen_reason_{case_id}")
                    if st.button("Confirm Reopening", key=f"btn_confirm_reopen_{case_id}"):
                        if not reopen_reason.strip():
                            st.warning("Reopening reason is required.")
                        else:
                            ok_ro, msg_ro = lifecycle_svc.reopen_case(case_id, current_user, reopen_reason)
                            if ok_ro:
                                _set_banner("success", msg_ro)
                                st.rerun()
                            else:
                                st.error(msg_ro)

    st.markdown("---")
    # ── Case History Timeline ────────────────────────────────────────
    try:
        timeline_events = lifecycle_svc.get_case_timeline(case_id)
    except Exception as exc:
        st.warning(f"Failed to fetch timeline: {exc}")
        timeline_events = []

    st.markdown("#### 📜 Case History & Event Timeline")
    if not timeline_events:
        st.caption("No history or lifecycle events recorded yet for this case.")
    else:
        for entry in reversed(timeline_events):
            time_str = _format_dt(entry.get("timestamp"))
            action_label = entry.get("action", "Event")
            badge_map = {
                "CASE_CREATED": ("badge-found", "➕ Case Created"),
                "CASE_UPDATED": ("badge-pending", "📝 Case Updated"),
                "CASE_STATUS_CHANGED": ("badge-verified", "🔀 Status Changed"),
                "MATCH_CONFIRMED": ("badge-verified", "✅ Match Confirmed"),
                "MATCH_REJECTED": ("badge-missing", "❌ Match Rejected"),
                "CASE_RESOLVED": ("badge-found", "🎉 Case Resolved"),
                "CASE_CLOSED": ("badge-missing", "🔒 Case Closed"),
                "CASE_REOPENED": ("badge-pending", "🔄 Case Reopened"),
            }
            cls, disp = badge_map.get(action_label, ("badge-pending", action_label))
            status_line = ""
            if entry.get("previous_status") or entry.get("new_status"):
                prev = entry.get("previous_status") or "–"
                new = entry.get("new_status") or "–"
                status_line = f" [{prev} → {new}]"
            with st.expander(
                f'<span class="badge {cls}">{disp}</span>  '
                f'`{time_str}`  —  by **{entry.get("actor", "system")}**{status_line}',
                expanded=False,
            ):
                if entry.get("description"):
                    st.markdown(entry["description"])
                st.caption(
                    f"Case ID: {case_id} · "
                    f"Source: {entry.get('type', 'EVENT')}"
                )


# ══════════════════════════════════════════════════════════════════════
# RENDER: Edit Case Form
# ══════════════════════════════════════════════════════════════════════

def render_edit_case(case_id: int):
    """Editable case form (authorized users only)."""
    try:
        case = case_service.get_case(case_id, current_user=current_user)
    except PermissionError as exc:
        _set_banner("error", f"🔒 Edit denied: {exc}")
        CM_UI["edit_case_id"] = None
        CM_UI["view_case_id"] = case_id
        st.rerun()
        return

    if case is None:
        _set_banner("error", "Case not found (it may have been deleted).")
        CM_UI["edit_case_id"] = None
        st.rerun()
        return

    back_col, title_col = st.columns([1, 10])
    with back_col:
        if st.button("← Cancel", key="cm_edit_cancel"):
            CM_UI["edit_case_id"] = None
            CM_UI["view_case_id"] = case_id
            st.rerun()

    st.markdown(f"### ✏️ Edit Case — `{case.case_number or 'Unassigned'}`")
    st.caption(
        "Case number, creator, and creation timestamp are preserved and "
        "cannot be modified. All updates are logged to the case history."
    )
    st.info(
        f"**Immutable fields:**\n"
        f"- Case Number: `{case.case_number or '—'}`\n"
        f"- Registered By: `{case.created_by or '—'}`\n"
        f"- Created: {_format_dt(case.created_at)}"
    )

    # Pre-fill defaults for date widgets
    default_ls_date = case.last_seen_date.date() if isinstance(case.last_seen_date, datetime) else (
        case.last_seen_date if isinstance(case.last_seen_date, date) else date.today()
    )

    with st.form("cm_edit_form", clear_on_submit=False):
        st.markdown("#### Personal Details")
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            f_name = st.text_input("Full Name *", value=case.name or "", key="cm_e_name")
        with pc2:
            f_age = st.number_input(
                "Age *", min_value=0, max_value=120, step=1,
                value=int(case.age or 0), key="cm_e_age",
            )
        with pc3:
            gender_options = ["Male", "Female", "Other"]
            try:
                g_idx = gender_options.index(case.gender) if case.gender in gender_options else 0
            except ValueError:
                g_idx = 0
            f_gender = st.selectbox("Gender *", gender_options, index=g_idx, key="cm_e_gender")

        st.markdown("#### Last Seen")
        lc1, lc2 = st.columns([2, 1])
        with lc1:
            f_location = st.text_input(
                "Last Seen Location (Address / Landmark) *",
                value=case.last_seen_location or "", key="cm_e_loc",
            )
        with lc2:
            f_date = st.date_input("Last Seen Date *", value=default_ls_date, key="cm_e_date")

        sc1, sc2 = st.columns(2)
        with sc1:
            f_state = st.text_input("State *", value=case.last_seen_state or "", key="cm_e_state")
        with sc2:
            f_city = st.text_input("City *", value=case.last_seen_city or "", key="cm_e_city")

        f_description = st.text_area(
            "Description & Identifiers *",
            value=case.description or "", height=100, key="cm_e_desc",
        )

        st.markdown("#### Contact Person")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            f_cname = st.text_input("Contact Name *", value=case.contact_name or "", key="cm_e_cname")
        with cc2:
            f_cemail = st.text_input("Contact Email *", value=case.contact_email or "", key="cm_e_cemail")
        with cc3:
            f_cphone = st.text_input("Contact Phone *", value=case.contact_phone or "", key="cm_e_cphone")

        st.markdown("#### Status")
        status_options = [STATUS_ACTIVE, "Missing", "Found"]
        try:
            s_idx = status_options.index(case.status) if case.status in status_options else 0
        except ValueError:
            s_idx = 0
        f_status = st.selectbox("Current Status", status_options, index=s_idx, key="cm_e_status")

        st.markdown(
            "#### Photograph "
            f"<span style='color:#94a3b8; font-size: 0.85em;'>"
            f"(leave blank to keep current)</span>",
            unsafe_allow_html=True,
        )
        pcol1, pcol2 = st.columns([1, 3])
        with pcol1:
            st.caption("Current photo:")
            st.image(load_image_safely(case.photo_path, case.name), width=120)
        with pcol2:
            f_photo = st.file_uploader(
                "Upload new photograph (PNG/JPG/JPEG/WEBP)",
                type=["png", "jpg", "jpeg", "webp"],
                help=f"Max size: {MAX_IMAGE_BYTES // 1024 // 1024} MB. Leave blank to keep current.",
                key="cm_e_photo",
            )

        submitted = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)

    if submitted:
        errors = []
        ok, msg = validate_required(f_name, "Full Name", min_length=2)
        if not ok: errors.append(msg)
        ok, msg = validate_age(int(f_age) if f_age is not None else 0)
        if not ok: errors.append(msg)
        ok, msg = validate_required(f_location, "Last Seen Location", min_length=3)
        if not ok: errors.append(msg)
        ok, msg = validate_required(f_state, "State", min_length=2)
        if not ok: errors.append(msg)
        ok, msg = validate_required(f_city, "City", min_length=2)
        if not ok: errors.append(msg)
        ok, msg = validate_required(f_description, "Description", min_length=10)
        if not ok: errors.append(msg)
        ok, msg = validate_required(f_cname, "Contact Name", min_length=2)
        if not ok: errors.append(msg)
        ok, msg = validate_email(f_cemail)
        if not ok: errors.append(msg)
        ok, msg = validate_phone(f_cphone)
        if not ok: errors.append(msg)

        photo_bytes = None
        photo_filename = ""
        if f_photo is not None:
            p_ok, p_msg = validate_image_upload(f_photo)
            if not p_ok:
                errors.append(p_msg)
            else:
                f_photo.seek(0)
                photo_bytes = f_photo.read()
                photo_filename = getattr(f_photo, "name", "")

        if errors:
            _set_banner("error", "⚠️ Validation failed:\n\n" + "\n".join(f"• {e}" for e in errors))
            st.rerun()

        try:
            with st.spinner("Saving changes and recording case history…"):
                updated = case_service.edit_case(
                    case_id,
                    name=f_name.strip(),
                    age=int(f_age),
                    gender=f_gender,
                    description=f_description.strip(),
                    last_seen_date=datetime.combine(f_date, time.min),
                    last_seen_location=f_location.strip(),
                    state=f_state.strip(),
                    city=f_city.strip(),
                    contact_name=f_cname.strip(),
                    contact_email=f_cemail.strip(),
                    contact_phone=f_cphone.strip(),
                    status=f_status,
                    photo_bytes=photo_bytes,
                    photo_filename=photo_filename,
                    current_user=current_user,
                )
            if updated:
                _set_banner(
                    "success",
                    f"✅ Case `{updated.case_number or case_id}` updated successfully. "
                    f"All changes have been logged to the case history.",
                )
                CM_UI["edit_case_id"] = None
                CM_UI["view_case_id"] = case_id
                st.rerun()
            else:
                _set_banner("error", "⚠️ Update failed — case may no longer exist.")
                st.rerun()
        except PermissionError as exc:
            _set_banner("error", f"🔒 Permission denied: {exc}")
            CM_UI["edit_case_id"] = None
            st.rerun()
        except ValueError as exc:
            _set_banner("error", f"⚠️ Validation error: {exc}")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            _set_banner("error", f"⚠️ Unexpected error: {exc}")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
# RENDER: Delete Confirmation Dialog
# ══════════════════════════════════════════════════════════════════════

def render_delete_confirm():
    """Admin-only delete confirmation. Requires typed case number to proceed."""
    if current_role != ROLE_ADMIN:
        _set_banner("error", "🔒 Only administrators can delete cases.")
        CM_UI["delete_confirm_id"] = None
        st.rerun()
        return

    case_id = CM_UI.get("delete_confirm_id")
    case_number = CM_UI.get("delete_case_number", "") or f"#{case_id}"
    case_name = CM_UI.get("delete_name", "")

    back_col, title_col = st.columns([1, 10])
    with back_col:
        if st.button("← Cancel", key="cm_del_cancel"):
            CM_UI["delete_confirm_id"] = None
            CM_UI["delete_case_number"] = ""
            CM_UI["delete_name"] = ""
            st.rerun()

    st.markdown(f"### 🗑️ Confirm Case Deletion")
    st.error(
        "This action will **soft-delete** the case from the active directory. "
        "The case record and its photograph will be preserved for audit and history purposes. "
        "**This cannot be undone from the UI.**"
    )
    st.markdown(
        f"- **Case ID:** `{case_id}`\n"
        f"- **Case Number:** `{case_number}`\n"
        f"- **Missing Person:** **{case_name}**"
    )

    with st.form("cm_delete_form", clear_on_submit=False):
        typed = st.text_input(
            f"Type the case number `{case_number}` to confirm deletion *",
            placeholder="Paste or type the case number exactly",
            key="cm_del_typed",
        )
        reason = st.text_area(
            "Reason for deletion (recorded in audit log)",
            placeholder="e.g. duplicate entry, case withdrawn by family, …",
            key="cm_del_reason",
            height=80,
        )
        confirmed = st.form_submit_button("🗑️ Permanently Soft-Delete This Case", type="primary")

    if confirmed:
        if typed.strip() != case_number.strip():
            _set_banner(
                "error",
                f"⚠️ Confirmation mismatch. Expected `{case_number}`, got `{typed.strip() or '(empty)'}`.",
            )
            st.rerun()

        try:
            with st.spinner("Soft-deleting case and recording audit history…"):
                ok = case_service.delete_case(case_id, current_user=current_user)
            if ok:
                _set_banner(
                    "success",
                    f"✅ Case `{case_number}` has been soft-deleted. "
                    f"A record of this action is preserved in the system logs.",
                )
            else:
                _set_banner("error", "⚠️ Deletion failed — case may already be deleted.")
        except PermissionError as exc:
            _set_banner("error", f"🔒 Permission denied: {exc}")
        except Exception as exc:  # noqa: BLE001
            _set_banner("error", f"⚠️ Unexpected error: {exc}")
        finally:
            CM_UI["delete_confirm_id"] = None
            CM_UI["delete_case_number"] = ""
            CM_UI["delete_name"] = ""
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
# RENDER: Case List + Search + Filters (default view)
# ══════════════════════════════════════════════════════════════════════

def render_list_view():
    # ── Search bar (top) ────────────────────────────────────────────
    s_col, b_col = st.columns([5, 1])
    with s_col:
        search_term = st.text_input(
            "🔍 Search",
            placeholder="Search by Case Number, Person Name, City, or State…",
            key="cm_search",
        )
    with b_col:
        st.markdown("<div style='height: 44px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Reset", key="cm_reset_search", use_container_width=True):
            for k in ("cm_search", "cm_f_status", "cm_f_gender",
                      "cm_f_state", "cm_f_city", "cm_f_date_from", "cm_f_date_to"):
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # ── Sidebar filters ─────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔎 Filters")
        st.caption("Filters apply to the cases you are authorized to see.")

        # Status filter
        status_opts = ["", STATUS_ACTIVE, "Missing", "Found"]
        f_status = st.selectbox(
            "Status",
            options=status_opts,
            format_func=lambda v: "All Statuses" if v == "" else v,
            key="cm_f_status",
        )

        # Gender filter
        gender_opts = ["", "Male", "Female", "Other"]
        f_gender = st.selectbox(
            "Gender",
            options=gender_opts,
            format_func=lambda v: "All Genders" if v == "" else v,
            key="cm_f_gender",
        )

        # State filter (use distinct values from DB + freeform)
        db_states = case_service.get_available_states()
        state_options = [""] + db_states
        f_state = st.selectbox(
            "State",
            options=state_options,
            format_func=lambda v: "All States" if v == "" else v,
            key="cm_f_state",
        )
        f_state_free = st.text_input(
            "State (override, if blank above)",
            placeholder="Or type a custom state name",
            key="cm_f_state_free",
        )
        effective_state = (f_state_free.strip() if f_state_free.strip() else f_state) or None

        # City filter
        db_cities = case_service.get_available_cities(state=effective_state)
        city_options = [""] + db_cities
        f_city = st.selectbox(
            "City",
            options=city_options,
            format_func=lambda v: "All Cities" if v == "" else v,
            disabled=not effective_state,
            key="cm_f_city",
        )
        f_city_free = st.text_input(
            "City (override, if blank above)",
            placeholder="Or type a custom city name",
            key="cm_f_city_free",
        )
        effective_city = (f_city_free.strip() if f_city_free.strip() else f_city) or None

        # Date range (last_seen_date)
        st.markdown("#### 📅 Last Seen Date Range")
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            f_date_from = st.date_input("From", value=None, key="cm_f_date_from")
        with dcol2:
            f_date_to = st.date_input("To", value=None, key="cm_f_date_to")

    # ── Query via service (ownership enforced inside) ───────────────
    with st.spinner("Loading cases…"):
        try:
            cases = case_service.search_and_filter_cases(
                search_term=search_term,
                status=f_status or None,
                gender=f_gender or None,
                state=effective_state,
                city=effective_city,
                date_from=datetime.combine(f_date_from, time.min) if f_date_from else None,
                date_to=datetime.combine(f_date_to, time.max) if f_date_to else None,
                current_user=current_user,
            )
        except PermissionError as exc:
            _set_banner("error", f"🔒 Access denied: {exc}")
            cases = []

    total = len(cases)
    st.markdown(
        f"<p style='color:#94a3b8; margin-top: 8px;'>"
        f"Showing <b style='color:#f1f5f9;'>{total}</b> case{'' if total == 1 else 's'} "
        f"{'across all officers' if current_role == ROLE_ADMIN else f'registered by `{current_username}`'}."
        f"</p>",
        unsafe_allow_html=True,
    )

    if not cases:
        st.info("No cases match the current search / filters. Try broadening the criteria.")
        return

    # ── Build table rows ────────────────────────────────────────────
    records = []
    for case in cases:
        ls_date_val = case.last_seen_date
        if isinstance(ls_date_val, datetime):
            ls_date_str = ls_date_val.strftime("%Y-%m-%d")
        elif isinstance(ls_date_val, date):
            ls_date_str = ls_date_val.strftime("%Y-%m-%d")
        else:
            ls_date_str = str(ls_date_val or "—")[:10]

        created_val = case.created_at
        if isinstance(created_val, datetime):
            created_str = created_val.strftime("%Y-%m-%d %H:%M")
        else:
            created_str = str(created_val or "—")[:16]

        records.append({
            "id": case.id,
            "Case Number": case.case_number or f"#{case.id}",
            "Person Name": case.name,
            "Age": case.age,
            "Gender": case.gender,
            "City": case.last_seen_city or "—",
            "State": case.last_seen_state or "—",
            "Last Seen": ls_date_str,
            "Status": case.status,
            "Created By": case.created_by or "—",
            "Created": created_str,
        })

    df = pd.DataFrame(records)
    df_display = df.drop(columns=["id"])

    # ── Display styled table (non-interactive) ──────────────────────
    def _style_status(s):
        return [
            (
                "color: #ef4444; font-weight: 600"
                if v in ("Missing", STATUS_ACTIVE)
                else (
                    "color: #10b981; font-weight: 600"
                    if v == "Found"
                    else "color: #f59e0b; font-weight: 600"
                )
            )
            for v in s
        ]

    try:
        styled = df_display.style.apply(_style_status, subset=["Status"])
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            height=min(520, 80 + len(df_display) * 38),
        )
    except Exception:
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ── Action panel: pick a case by Case Number ────────────────────
    st.markdown("---")
    st.markdown("#### 🎯 Actions on a Case")
    pick_col1, pick_col2, pick_col3, pick_col4 = st.columns([2, 1, 1, 1])
    with pick_col1:
        label_options = [
            f"{r['Case Number']} — {r['Person Name']} (Age {r['Age']}, {r['City']})"
            for r in records
        ]
        mapping = {label: r["id"] for label, r in zip(label_options, records)}
        if "cm_pick_case" in st.session_state and st.session_state["cm_pick_case"] not in label_options:
            del st.session_state["cm_pick_case"]
        pick = st.selectbox(
            "Select a case",
            options=label_options,
            format_func=lambda v: v,
            key="cm_pick_case",
        )
    selected_id = mapping.get(pick) if pick else None

    if selected_id is not None:
        case_meta = next((r for r in records if r["id"] == selected_id), None)
        owner = case_meta.get("Created By") if case_meta else None
        can_edit_row = (
            (current_role == ROLE_ADMIN)
            or (current_role == ROLE_OFFICER and owner == current_username)
        )
        can_delete_row = (current_role == ROLE_ADMIN)

        with pick_col2:
            if st.button("👁️ View", key="cm_act_view", use_container_width=True):
                CM_UI["view_case_id"] = selected_id
                st.rerun()
        with pick_col3:
            if can_edit_row:
                if st.button("✏️ Edit", key="cm_act_edit", use_container_width=True):
                    CM_UI["edit_case_id"] = selected_id
                    st.rerun()
            else:
                st.button("🔒 Edit", disabled=True, key="cm_act_edit_lock", use_container_width=True)
        with pick_col4:
            if can_delete_row:
                if st.button("🗑️ Delete", key="cm_act_del", use_container_width=True):
                    CM_UI["delete_confirm_id"] = selected_id
                    CM_UI["delete_case_number"] = case_meta.get("Case Number", "") if case_meta else ""
                    CM_UI["delete_name"] = case_meta.get("Person Name", "") if case_meta else ""
                    st.rerun()
            else:
                st.button("🔒 Delete", disabled=True, key="cm_act_del_lock", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# Routing: dispatch to the right sub-view based on session state
# ══════════════════════════════════════════════════════════════════════

if CM_UI.get("delete_confirm_id"):
    render_delete_confirm()
elif CM_UI.get("edit_case_id"):
    render_edit_case(CM_UI["edit_case_id"])
elif CM_UI.get("view_case_id"):
    render_view_case(CM_UI["view_case_id"])
else:
    render_list_view()
