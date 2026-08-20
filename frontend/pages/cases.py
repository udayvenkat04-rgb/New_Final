import streamlit as st
from datetime import datetime
from backend.database import check_connection
from backend.auth.permissions import require_role, ROLE_ADMIN, ROLE_OFFICER
from backend.utils.helpers import inject_custom_css, load_image_safely
from backend.utils.validators import (
    validate_registration_payload,
    validate_image_upload,
    validate_email,
    validate_phone,
    validate_age,
    validate_required,
    MAX_IMAGE_BYTES,
)
from backend.repositories import CaseRepository, SightingRepository
from backend.services import CaseService

# ── Page setup + authorization guard ─────────────────────────────────
st.set_page_config(page_title="Case Registry", page_icon="📁", layout="wide")
inject_custom_css()
require_role([ROLE_OFFICER, ROLE_ADMIN])

st.markdown("<h2 style='color: #10b981;'>📁 Missing Person Registry & Bulletin Board</h2>", unsafe_allow_html=True)
st.markdown(
    "<p style='color: #94a3b8;'>File new missing person bulletins (Register tab) or browse and filter the existing directory.</p>",
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

case_repo = CaseRepository()
sighting_repo = SightingRepository()
case_service = CaseService(case_repo)

current_user = st.session_state.get("user") or {}
if not current_user:
    st.error("⚠️ No authenticated user in session. Please log in again.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════
# Configuration: Indian State/City reference
# ══════════════════════════════════════════════════════════════════════

COMMON_INDIAN_STATES = [
    "",
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal",
    "Andaman and Nicobar", "Chandigarh", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry",
]


# ══════════════════════════════════════════════════════════════════════
# UI Section 1 — Registration Form
# ══════════════════════════════════════════════════════════════════════

def render_register_tab():
    """Renders the Register Missing Person form.

    All 12 required form fields are collected here. Validation runs in two
    layers:
      1. UI-layer: runs field-level validators inline so users get instant
         feedback *before* submit.
      2. Service-layer: register_missing_person() re-runs the same
         validate_registration_payload + performs photo save + creates
         the MongoDB doc.
    The two-layer approach prevents anyone from tampering with submitted
    form data via devtools to bypass client-side validation.
    """
    st.markdown("### ✍️ Register a New Missing Person Bulletin")
    st.caption(
        "All fields are mandatory. The uploaded photograph will be stored with a "
        "safe, server-generated filename — never the uploader-provided file name."
    )

    # Session-state banner: keeps success/error visible across reruns
    reg_state = st.session_state.setdefault("reg_banner", {"type": None, "msg": "", "case_number": None})

    with st.form("register_missing_person_form", clear_on_submit=False):
        st.markdown("#### 1. Personal Details")
        col_left, col_right = st.columns(2)
        with col_left:
            f_name = st.text_input("Full Name *", placeholder="e.g. Aarav Sharma", key="reg_name")
            f_age = st.number_input("Age *", min_value=0, max_value=120, step=1, value=0, key="reg_age")
            f_gender = st.selectbox("Gender *", ["", "Male", "Female", "Other"], key="reg_gender")
        with col_right:
            f_state = st.selectbox(
                "State *",
                COMMON_INDIAN_STATES,
                help="Pick a state or type a custom value below.",
                key="reg_state",
            )
            # Override: allow free-text if user clicks 'other'
            f_state_other = st.text_input(
                "State (custom, if above is blank)",
                placeholder="Leave blank if you selected a state above",
                key="reg_state_other",
            )
            effective_state = (f_state_other or "").strip() or f_state
            f_city = st.text_input("City *", placeholder="e.g. Bengaluru", key="reg_city")

        st.markdown("#### 2. Case Details")
        f_description = st.text_area(
            "Description & Identifiers *",
            placeholder=(
                "Describe height, clothing, identifying marks, language spoken, "
                "behaviour, medical conditions..."
            ),
            height=110,
            key="reg_description",
        )
        loc1, loc2 = st.columns([2, 1])
        with loc1:
            f_last_seen_loc = st.text_input(
                "Last Seen Location *",
                placeholder="Address / landmark / area",
                key="reg_location",
            )
        with loc2:
            f_last_seen_date = st.date_input("Last Seen Date *", value=None, key="reg_date")

        st.markdown("#### 3. Contact Person")
        c1, c2, c3 = st.columns(3)
        with c1:
            f_contact_name = st.text_input(
                "Contact Person Name *", placeholder="e.g. Rajesh Kumar", key="reg_cname",
            )
        with c2:
            f_contact_email = st.text_input(
                "Contact Email *", placeholder="family@example.com", key="reg_cemail",
            )
        with c3:
            f_contact_phone = st.text_input(
                "Contact Phone *", placeholder="+91 98XXX XXXXX", key="reg_cphone",
            )

        st.markdown("#### 4. Photograph")
        photo_help = (
            f"Upload a clear close-up portrait of the missing person. "
            f"Allowed: PNG, JPG, JPEG, WEBP. Max size: {MAX_IMAGE_BYTES // 1024 // 1024} MB."
        )
        f_photo = st.file_uploader(
            "Photograph of the Missing Person *",
            type=["png", "jpg", "jpeg", "webp"],
            help=photo_help,
            key="reg_photo",
        )
        if f_photo is not None:
            image_bytes = f_photo.read()
            st.image(image_bytes, width=200, caption="Photo preview")
            # Reset pointer after read so downstream can still access buffer
            f_photo.seek(0)

        submitted = st.form_submit_button(
            "🔒 Register Bulletin",
            use_container_width=True,
            type="primary",
            help="Submit to create a case record. A unique case number will be generated.",
        )

    if submitted:
        # Clear any stale banner from previous submit
        reg_state["type"] = None
        reg_state["msg"] = ""
        reg_state["case_number"] = None

        # UI-level validation (defense in depth — service re-validates)
        payload_preview = {
            "name": f_name,
            "age": int(f_age) if f_age is not None else 0,
            "gender": f_gender,
            "description": f_description,
            "last_seen_date": f_last_seen_date,
            "last_seen_location": f_last_seen_loc,
            "state": effective_state,
            "city": f_city,
            "contact_name": f_contact_name,
            "contact_email": f_contact_email,
            "contact_phone": f_contact_phone,
            "photo_file": f_photo,
        }
        ok, errors = validate_registration_payload(payload_preview)

        # Extra guard: service-layer photo validation is a separate codepath
        if f_photo is None:
            ok = False
            errors.append("A photograph upload is required.")
        else:
            p_ok, p_msg = validate_image_upload(f_photo)
            if not p_ok:
                ok = False
                errors.append(p_msg)

        if not ok:
            reg_state["type"] = "error"
            reg_state["msg"] = "\n".join(f"• {e}" for e in errors)
            st.rerun()

        # Ready to create the record via CaseService
        try:
            with st.spinner("Creating case bulletin and saving photograph to secure storage..."):
                if f_photo is not None:
                    f_photo.seek(0)
                    photo_bytes_saved = f_photo.read()
                else:
                    photo_bytes_saved = b""

                saved_case = case_service.register_missing_person(
                    name=f_name.strip(),
                    age=int(f_age),
                    gender=f_gender,
                    description=f_description.strip(),
                    last_seen_date=datetime.combine(f_last_seen_date, datetime.min.time())
                    if f_last_seen_date else None,
                    last_seen_location=f_last_seen_loc.strip(),
                    state=(effective_state or "").strip(),
                    city=f_city.strip(),
                    contact_name=f_contact_name.strip(),
                    contact_email=f_contact_email.strip(),
                    contact_phone=f_contact_phone.strip(),
                    photo_bytes=photo_bytes_saved,
                    photo_filename=getattr(f_photo, "name", ""),
                    current_user=current_user,
                )
            reg_state["type"] = "success"
            reg_state["msg"] = f"Missing person bulletin for **{saved_case.name}** has been filed."
            reg_state["case_number"] = saved_case.case_number
        except PermissionError as exc:
            reg_state["type"] = "error"
            reg_state["msg"] = f"🔒 Permission denied: {exc}"
        except ValueError as exc:
            reg_state["type"] = "error"
            reg_state["msg"] = f"⚠️ Validation failed: {exc}"
        except RuntimeError as exc:
            reg_state["type"] = "error"
            reg_state["msg"] = f"⚠️ Registration failed: {exc}"
        except Exception as exc:  # noqa: BLE001 — show all unexpected errors to user
            reg_state["type"] = "error"
            reg_state["msg"] = f"⚠️ Unexpected error: {exc}"
        st.rerun()

    # Display persisted banner (survives the form-validation rerun)
    if reg_state.get("type") == "success":
        case_num = reg_state.get("case_number")
        st.success(
            f"✅ **Bulletin registered successfully!**\n\n"
            f"{reg_state.get('msg', '')}\n\n"
            f"📄 **Case Number:** `{case_num}`"
        )
        st.info(
            "Remember to note the unique case number above — it's the official "
            "identifier for this missing person bulletin across the system."
        )
        if st.button("📝 Register Another Bulletin", type="secondary"):
            # Reset banner + rerun so form appears fresh (no stale data)
            reg_state["type"] = None
            reg_state["msg"] = ""
            reg_state["case_number"] = None
            st.rerun()
    elif reg_state.get("type") == "error":
        st.error(reg_state.get("msg", "Unknown registration error."))


# ══════════════════════════════════════════════════════════════════════
# UI Section 2 — Directory / Detail View (existing, kept intact)
# ══════════════════════════════════════════════════════════════════════

def render_directory_tab():
    """Existing case directory + detail + filter + status update (kept)."""
    # Horizontal Directory Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        search_name = st.text_input("🔍 Search Name", key="dir_search")
    with fcol2:
        status_filter = st.selectbox("Status", ["All", "Missing", "Found", "ACTIVE"], key="dir_status")
    with fcol3:
        gender_filter = st.selectbox("Gender", ["All", "Male", "Female", "Other"], key="dir_gender")

    # Build MongoDB query filter
    query_filter = {}
    if status_filter != "All":
        query_filter["status"] = status_filter
    if gender_filter != "All":
        query_filter["gender"] = gender_filter
    if search_name:
        query_filter["name"] = {"$regex": search_name, "$options": "i"}

    cases = [c.to_dict() for c in case_repo.get_all(query_filter)]

    # 2. Main Section
    if not cases:
        st.info("No cases match the selected filters.")
        return

    # Columns layout for the directory
    col_list, col_detail = st.columns([1, 1])

    with col_list:
        st.subheader(f"Results ({len(cases)})")
        for case in cases:
            badge_class = (
                "badge-missing"
                if case.get("status") in ("Missing", "ACTIVE")
                else "badge-found"
            )
            case_id = case.get("id")
            case_name = case.get("name")
            case_num = case.get("case_number") or "—"

            st.markdown(f"""
            <div class="glass-card" style="cursor: pointer;">
                <div style="display: flex; gap: 15px; align-items: center;">
                    <div style="flex: 1;">
                        <h4 style="margin: 0; color: #f1f5f9;">{case_name}</h4>
                        <div style="margin-top: 4px;">
                            <span class="badge {badge_class}">{case.get("status")}</span>
                            <span style="margin-left: 10px; font-size: 12px; color: #94a3b8;">
                                {case_num} · Age {case.get("age")} · {case.get("gender")}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            c_cols = st.columns([3, 1])
            with c_cols[0]:
                st.image(load_image_safely(case.get("photo_path"), case_name), width=75)
            with c_cols[1]:
                if st.button("👁️ View", key=f"sel_{case_id}"):
                    st.session_state.selected_case_id = case_id
            st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'/>", unsafe_allow_html=True)

    with col_detail:
        selected_id = st.session_state.get(
            "selected_case_id", (cases[0].get("id") if cases else None)
        )
        if selected_id is None:
            st.write("Select a bulletin to see its full details.")
            return

        case_obj = case_repo.get_by_id(selected_id)
        if not case_obj:
            st.warning("Selected case not found in the database.")
            return
        case = case_obj.to_dict()
        case_name = case.get("name")
        case_id = case.get("id")
        case_status = case.get("status", "Missing")
        case_number = case.get("case_number") or "Unassigned"

        st.subheader(f"Bulletin: {case_name}")
        st.caption(f"Case Number: {case_number} · Internal ID: #{case_id}")

        det_col1, det_col2 = st.columns([1, 1])
        with det_col1:
            st.image(load_image_safely(case.get("photo_path"), case_name), use_container_width=True)
        with det_col2:
            badge_class = (
                "badge-missing"
                if case_status in ("Missing", "ACTIVE")
                else "badge-found"
            )

            last_seen_date_val = case.get("last_seen_date")
            if isinstance(last_seen_date_val, datetime):
                last_seen_str = last_seen_date_val.strftime("%Y-%m-%d")
            else:
                last_seen_str = str(last_seen_date_val)[:10] if last_seen_date_val else "N/A"

            st.markdown(f"""
            <span class="badge {badge_class}" style="font-size: 14px; padding: 6px 16px;">
                {case_status}
            </span>
            <p style="margin-top: 15px;"><b>Age:</b> {case.get("age")}</p>
            <p><b>Gender:</b> {case.get("gender")}</p>
            <p><b>State / City:</b> {case.get("last_seen_state") or "—"} / {case.get("last_seen_city") or "—"}</p>
            <p><b>Last Seen Location:</b> {case.get("last_seen_location") or "—"}</p>
            <p><b>Last Seen Date:</b> {last_seen_str}</p>
            <p><b>Contact Person:</b> {case.get("contact_name") or case.get("reporter_name") or "N/A"}</p>
            <p><b>Contact Email:</b> {case.get("contact_email") or "—"}</p>
            <p><b>Contact Phone:</b> {case.get("contact_phone") or case.get("reporter_contact") or "N/A"}</p>
            <p><b>Registered By (user id):</b> {case.get("created_by") or "—"}</p>
            """, unsafe_allow_html=True)

            allowed_statuses = ["Missing", "Found", "ACTIVE"]
            try:
                idx = allowed_statuses.index(case_status)
            except ValueError:
                idx = 0
            new_status = st.selectbox(
                "Update Status",
                allowed_statuses,
                index=idx,
                key=f"status_sel_{case_id}",
            )
            if new_status != case_status:
                curr_user = st.session_state.get("user", {})
                username_str = curr_user.get("username", "system")
                case_service.update_case_status(
                    case_id, new_status, updated_by=username_str, current_user=curr_user,
                )
                st.success(f"Status updated to '{new_status}'.")
                st.rerun()

        st.markdown("##### 📝 Description")
        st.write(case.get("description") or "*No physical descriptors added.*")

        st.markdown("---")
        st.markdown("##### ⏱️ Verified Sighting Timeline")
        sightings_list = sighting_repo.get_all({"case_id": case_id, "status": "Verified"})
        if not sightings_list:
            st.write("No verified sightings logged for this person yet.")
        else:
            for idx, sight_obj in enumerate(sightings_list):
                sight = sight_obj.to_dict()
                sight_time_val = sight.get("sighting_time")
                if isinstance(sight_time_val, datetime):
                    sight_time_str = sight_time_val.strftime("%Y-%m-%d %H:%M")
                else:
                    sight_time_str = str(sight_time_val)[:16] if sight_time_val else "N/A"
                st.info(
                    f"📍 **{sight.get('address')}**\n\n"
                    f"📅 **Date:** {sight_time_str}\n\n"
                    f"🕵️ **Reporter:** {sight.get('reporter_name')} | "
                    f"**Details:** *\"{sight.get('details')}\"*"
                )
                if sight.get("photo_path"):
                    st.image(
                        load_image_safely(sight.get("photo_path"), f"Sighting #{idx + 1}"),
                        caption=f"Sighting photo #{idx + 1}",
                        width=200,
                    )


# ══════════════════════════════════════════════════════════════════════
# Tabs bootstrap
# ══════════════════════════════════════════════════════════════════════

tab_register, tab_directory = st.tabs(["✍️ Register Missing Person", "📂 Case Directory"])
with tab_register:
    render_register_tab()
with tab_directory:
    render_directory_tab()
