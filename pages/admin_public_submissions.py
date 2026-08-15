"""
Admin Public Submissions Review Queue (Phase 22).

Allows authorized Administrators to inspect submitted public missing person reports,
view photographs, examine complainant contact details, check duplicate warnings,
approve reports (creating official cases), or reject reports with audit trail logging.
"""

import os
import streamlit as st
from PIL import Image
from backend.database import check_connection
from backend.auth.permissions import require_role, ROLE_ADMIN
from backend.utils.helpers import inject_custom_css
from backend.services.public_submission_review_service import PublicSubmissionReviewService

# Page Setup & Auth Guard (Admin Only)
st.set_page_config(page_title="Public Submissions Review", page_icon="📥", layout="wide")
inject_custom_css()
require_role([ROLE_ADMIN])

st.markdown("<h2 style='color: #10b981; margin-bottom: 0;'>📥 Public Submissions Review Queue</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Review, verify, and approve public missing person reports into official system cases.</p>", unsafe_allow_html=True)
st.markdown("---", unsafe_allow_html=True)

# Database Connection Check
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning("Please ensure MongoDB is running and configured correctly in `.env`.")
    st.stop()

review_service = PublicSubmissionReviewService()
current_user = st.session_state.get("user")

# ── Summary Metrics ──────────────────────────────────────────────────
try:
    counts = review_service.get_submission_counts(current_user)
except PermissionError as exc:
    st.error(f"🔒 {exc}")
    st.stop()

mcol1, mcol2, mcol3, mcol4 = st.columns(4)
mcol1.metric("⏳ Pending Verification", f"{counts.get('PENDING_VERIFICATION', 0)}")
mcol2.metric("✅ Approved Reports", f"{counts.get('APPROVED', 0)}")
mcol3.metric("❌ Rejected Reports", f"{counts.get('REJECTED', 0)}")
mcol4.metric("⚠️ Possible Duplicates", f"{counts.get('DUPLICATE_POSSIBLE', 0)}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Queue Filters ─────────────────────────────────────────────────────
fcol1, fcol2 = st.columns([3, 1])
with fcol1:
    status_filter = st.selectbox(
        "Filter Submissions by Status",
        options=["PENDING_VERIFICATION", "APPROVED", "REJECTED", "All"],
        index=0,
        key="filter_admin_sub_status",
    )
with fcol2:
    st.write("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Queue", use_container_width=True, key="btn_refresh_sub_queue"):
        st.rerun()

submissions = review_service.get_all_submissions(current_user, status=status_filter)

if not submissions:
    st.info(f"No public submissions found matching filter status '{status_filter}'.")
else:
    st.markdown(f"#### 📋 Submissions Queue ({len(submissions)} items)")

    # Select submission to inspect
    sub_options = {
        f"{s.submission_reference} - {s.full_name} ({s.last_seen_city or 'Unknown City'}, {s.status})": s.id
        for s in submissions
    }
    selected_label = st.selectbox("Select Submission to Inspect & Review", options=list(sub_options.keys()))
    selected_id = sub_options[selected_label]

    selected_sub, audit_trail = review_service.get_submission_details(selected_id, current_user)

    if selected_sub:
        st.markdown("---")
        st.markdown(f"### 🔍 Inspecting Submission `{selected_sub.submission_reference}`")

        if selected_sub.is_possible_duplicate:
            st.warning("⚠️ **DUPLICATE CANDIDATE WARNING**: This submission matches an existing case or pending report by name, age, or location.")

        scol1, scol2 = st.columns([1, 2])

        with scol1:
            st.markdown("#### 🖼️ Submitted Photograph")
            if selected_sub.photo_path and os.path.exists(selected_sub.photo_path):
                try:
                    img = Image.open(selected_sub.photo_path)
                    st.image(img, use_container_width=True, caption=f"Photo for {selected_sub.full_name}")
                except Exception:
                    st.error("Failed to load photograph image file.")
            else:
                st.info("📷 No photo attached or photo file missing.")

        with scol2:
            st.markdown("#### 👤 Person & Last Seen Metadata")
            badge_cls = "badge-pending" if selected_sub.status == "PENDING_VERIFICATION" else ("badge-found" if selected_sub.status == "APPROVED" else "badge-missing")

            created_date_str = selected_sub.created_at.strftime("%d %b %Y, %H:%M UTC") if selected_sub.created_at else "N/A"
            last_seen_dt_str = selected_sub.last_seen_date.strftime("%d %b %Y") if selected_sub.last_seen_date else "N/A"

            st.markdown(f"""
            <div class="glass-card" style="padding: 16px;">
                <p><b>Full Name:</b> <b style="font-size: 18px; color: #f1f5f9;">{selected_sub.full_name}</b></p>
                <p><b>Age / Gender:</b> <code>{selected_sub.age} yrs</code> · <code>{selected_sub.gender}</code></p>
                <p><b>Height / Features:</b> {selected_sub.height or 'N/A'} · {selected_sub.identifying_features or 'N/A'}</p>
                <p><b>Last Seen Location:</b> 📍 {selected_sub.last_seen_location or 'N/A'} ({selected_sub.last_seen_city or 'N/A'}, {selected_sub.last_seen_state or 'N/A'})</p>
                <p><b>Last Seen Date / Time:</b> 🕐 {last_seen_dt_str} ({selected_sub.last_seen_time or 'N/A'})</p>
                <p><b>Description:</b> <i>"{selected_sub.description or 'No description'}"</i></p>
                <p><b>Current Status:</b> <span class="badge {badge_cls}">{selected_sub.status}</span></p>
                <p><b>Submitted At:</b> <code>{created_date_str}</code></p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("#### 📞 Complainant Contact Info")
            st.markdown(f"""
            <div class="glass-card" style="padding: 16px; border-left: 4px solid #3b82f6;">
                <p><b>Complainant Name:</b> {selected_sub.complainant_name}</p>
                <p><b>Relationship:</b> {selected_sub.relationship or 'N/A'}</p>
                <p><b>Email Address:</b> <code>{selected_sub.contact_email}</code></p>
                <p><b>Phone Number:</b> <code>{selected_sub.contact_phone}</code></p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Decision & Review Action Form ────────────────────────────────────
        st.markdown("### ⚖️ Administrative Decision Form")

        if selected_sub.status == "APPROVED":
            st.success(f"✅ **This report has already been APPROVED.** Official Case ID: `#{selected_sub.approved_case_id}`")
        elif selected_sub.status == "REJECTED":
            st.error(f"❌ **This report has already been REJECTED.** Reviewer Notes: `{selected_sub.review_notes}`")

        review_notes = st.text_area(
            "Administrative Review Notes / Rejection Reason",
            value=selected_sub.review_notes or "",
            placeholder="Add internal review notes or mandatory rejection reasons here...",
            key="input_admin_review_notes",
        )

        dcol1, dcol2 = st.columns(2)

        with dcol1:
            if st.button("✅ Approve Report (Create Official Case)", use_container_width=True, key="btn_approve_sub"):
                ok, case_id, msg = review_service.approve_submission(selected_sub.id, current_user, notes=review_notes)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        with dcol2:
            if st.button("❌ Reject Report", use_container_width=True, key="btn_reject_sub"):
                if not review_notes.strip():
                    st.warning("Please provide a rejection reason in the notes field before rejecting.")
                else:
                    ok, msg = review_service.reject_submission(selected_sub.id, current_user, reason=review_notes)
                    if ok:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        # ── Audit Trail Expander ─────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📜 View Audit Trail History"):
            if not audit_trail:
                st.info("No audit history recorded yet.")
            else:
                for a in audit_trail:
                    created_at_str = a.created_at.strftime("%Y-%m-%d %H:%M UTC") if a.created_at else "N/A"
                    st.markdown(f"""
                    - **Action:** `{a.action}` | **Actor:** `{a.actor_username}` (`{a.actor_role}`) | **Time:** `{created_at_str}`
                      - Status: `{a.previous_status}` ➔ `{a.new_status}`
                      - Notes: *"{a.notes or 'None'}"*
                    """)
