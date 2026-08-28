"""
Admin Match Review & Confirmation Queue — Phase 19

Only authenticated ADMIN users can access this page.

Workflow:
1. Displays Human-in-the-Loop review queue & status metrics
2. Filters queue by Review Status & Source Type (Image / Video)
3. Displays side-by-side visual evidence comparison
4. Collects Admin review decision (Confirm, Reject, Needs Further Review) & review notes
5. Enforces deliberate confirmation check and duplicate decision guards
6. Displays full immutable audit trail history for each candidate
"""

from __future__ import annotations

import os
from datetime import datetime
import streamlit as st

from backend.auth.permissions import require_role, ROLE_ADMIN
from backend.models.match_review import MatchReview, MatchReviewAudit
from backend.repositories.case_repository import CaseRepository
from backend.repositories.sighting_repository import SightingRepository
from backend.services.match_review import (
    DECISION_CONFIRMED,
    DECISION_FURTHER_REVIEW,
    DECISION_PENDING,
    DECISION_REJECTED,
    MatchReviewService,
)
from backend.services.notification_service import NotificationService
from backend.utils.file_utils import load_image_safely
from backend.utils.helpers import inject_custom_css


def mask_email(email: str) -> str:
    """Safely masks recipient email address for UI display."""
    if not email or "@" not in email:
        return "c***@example.com"
    parts = email.split("@")
    name = parts[0]
    domain = parts[1]
    masked_name = name[0] + "***" if len(name) > 1 else "***"
    return f"{masked_name}@{domain}"

# ── Page setup & Admin auth guard ────────────────────────────────────
st.set_page_config(
    page_title="Match Review Queue",
    page_icon="🔍",
    layout="wide",
)
inject_custom_css()

# Enforce Admin Authorization Guard
try:
    require_role([ROLE_ADMIN])
except PermissionError as perm_err:
    st.error(f"🔒 **Access Denied**: {perm_err}")
    st.warning("Only authenticated System Administrators have permission to perform match reviews and confirm identities.")
    st.stop()

st.markdown(
    "<h2 style='color: #10b981;'>🔍 Admin Match Review & Confirmation Queue</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color: #94a3b8;'>Human-in-the-Loop Verification Portal: Inspect biometric candidate evidence, compare images side-by-side, submit auditable decisions, and manage case resolution.</p>",
    unsafe_allow_html=True,
)

# ── Mandatory Human Review Disclaimer Banner ──────────────────────────
st.warning(
    "⚠️ **Important Security & Protocol Notice**: Biometric similarity scores and Euclidean distances "
    "are AI-generated candidate suggestions for human review. **AI/KNN NEVER automatically confirms identity.** "
    "Final identity resolution requires deliberate review and confirmation by an authorized human Administrator."
)
st.markdown("---")

# ── Services Initialization ──────────────────────────────────────────
review_service = MatchReviewService()
notification_service = NotificationService()
case_repo = CaseRepository()
sighting_repo = SightingRepository()
current_user = st.session_state.get("user")

# ── Section 1: Summary Metrics ───────────────────────────────────────
counts = review_service.get_review_counts(user=current_user)

mcol1, mcol2, mcol3, mcol4 = st.columns(4)
mcol1.metric("⏳ Pending Review", f"{counts.get('PENDING_REVIEW', 0)}")
mcol2.metric("✅ Confirmed Matches", f"{counts.get('CONFIRMED', 0)}")
mcol3.metric("❌ Rejected Matches", f"{counts.get('REJECTED', 0)}")
mcol4.metric("🟡 Needs Further Review", f"{counts.get('NEEDS_FURTHER_REVIEW', 0)}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Section 2: Queue Filter Controls ─────────────────────────────────
st.subheader("1. Filter Candidate Queue")

fcol1, fcol2 = st.columns(2)

with fcol1:
    status_filter = st.selectbox(
        "Filter by Review Status",
        options=["PENDING_REVIEW", "ALL", "CONFIRMED", "REJECTED", "NEEDS_FURTHER_REVIEW"],
        index=0,
        help="Select status to filter candidate review records."
    )

with fcol2:
    source_filter = st.selectbox(
        "Filter by Source Type",
        options=["ALL", "IMAGE", "VIDEO"],
        index=0,
        help="Filter between image sightings vs video surveillance sightings."
    )

# Retrieve filtered review queue
reviews = review_service.get_review_queue(
    user=current_user,
    filter_status=status_filter,
    source_type=source_filter
)

# ── Section 3: Review Queue List / Table ─────────────────────────────
st.markdown(f"#### 📋 Candidate Queue ({len(reviews)} record(s) found)")

if not reviews:
    st.info("ℹ️ No candidate match records found matching the selected filter criteria.")
else:
    # Display queue cards or selectbox
    review_labels = []
    for r in reviews:
        c_obj = case_repo.get_by_id(r.case_id)
        c_name = c_obj.name if c_obj else f"Case {r.case_id}"
        badge_color = "#f59e0b" if r.review_status == "PENDING_REVIEW" else ("#10b981" if r.review_status == "CONFIRMED" else "#ef4444")
        review_labels.append(f"Review #{r.id} | Case {r.case_id} ({c_name}) | {r.source_type} | Similarity: {r.similarity_score:.1f}% | [{r.review_status}]")

    if "selected_review_idx" in st.session_state and st.session_state["selected_review_idx"] not in range(len(reviews)):
        del st.session_state["selected_review_idx"]
    selected_index = st.selectbox(
        "Select candidate record to inspect & review:",
        options=range(len(reviews)),
        format_func=lambda i: review_labels[i],
        key="selected_review_idx"
    )

    selected_review: MatchReview = reviews[selected_index]

    st.markdown("---")
    st.subheader(f"2. Inspect Candidate Review #{selected_review.id} — Case {selected_review.case_id}")

    c_obj = case_repo.get_by_id(selected_review.case_id)

    # ── Section 4: Detailed Evidence & Comparison ────────────────────
    col_case_info, col_match_info = st.columns(2)

    with col_case_info:
        st.markdown("#### 📁 Registered Case Information")
        if c_obj:
            st.markdown(f"""
            <div class="glass-card" style="padding: 15px;">
                <p><b>Case Number:</b> <code>{c_obj.case_number or c_obj.id}</code></p>
                <p><b>Full Name:</b> <b style="color: #10b981;">{c_obj.name}</b></p>
                <p><b>Age / Gender:</b> <code>{c_obj.age} yrs</code> | <code>{c_obj.gender}</code></p>
                <p><b>Last Seen Location:</b> {c_obj.last_seen_location}, {c_obj.city}, {c_obj.state}</p>
                <p><b>Current Case Status:</b> <span class="badge badge-missing">{c_obj.status}</span></p>
                <p><b>Description:</b> <i>{c_obj.description}</i></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"Case record #{selected_review.case_id} not found in database.")

    with col_match_info:
        st.markdown("#### 🔬 AI Biometric Match Metrics")
        badge_cls = "badge-pending" if selected_review.review_status == "PENDING_REVIEW" else ("badge-found" if selected_review.review_status == "CONFIRMED" else "badge-missing")

        st.markdown(f"""
        <div class="glass-card" style="padding: 15px; border-left: 4px solid #3b82f6;">
            <p><b>Source Type:</b> <code>{selected_review.source_type}</code></p>
            <p><b>Similarity Score:</b> <b style="color: #10b981; font-size: 20px;">{selected_review.similarity_score:.2f}%</b></p>
            <p><b>Euclidean Distance:</b> <code>{selected_review.distance:.4f}</code></p>
            <p><b>Review Status:</b> <span class="badge {badge_cls}">{selected_review.review_status}</span></p>
            <p><b>Match Date:</b> <code>{selected_review.created_at}</code></p>
        </div>
        """, unsafe_allow_html=True)

        if selected_review.source_type == "VIDEO":
            st.info(
                f"📹 **Video Sightings Data**: First Seen: `{selected_review.first_seen_timestamp or 0:.2f}s` | "
                f"Last Seen: `{selected_review.last_seen_timestamp or 0:.2f}s` | "
                f"Detections Count: `{selected_review.detection_count or 1}` frames"
            )

        # Phase 20 Notification Status Card
        notifs = notification_service.get_notifications_for_review(selected_review.id, user=current_user)
        if notifs:
            last_notif = notifs[0]
            masked_recip = mask_email(last_notif.recipient_email)
            if last_notif.status == "SENT":
                st.success(f"✓ **Notification Email Sent** to `{masked_recip}`")
            elif last_notif.status == "FAILED":
                st.error(f"⚠️ **Match Confirmed, but Email Notification Failed**: `{last_notif.error_message}`")
                if st.button("🔄 Retry Notification Email", key=f"retry_btn_{selected_review.id}"):
                    retry_res = notification_service.retry_failed_notification(last_notif.id, user=current_user)
                    if retry_res.get("status") == "SENT":
                        st.success("✅ **Retry Successful!** Notification email delivered.")
                        st.rerun()
                    else:
                        st.error(f"❌ Retry failed: {retry_res.get('message')}")
            else:
                st.info(f"ℹ️ **Notification Record**: Status: `{last_notif.status}` | Recipient: `{masked_recip}`")

    st.markdown("#### 🖼️ Side-by-Side Visual Comparison")
    img_col1, img_col2 = st.columns(2)

    # Resolve Sighting / Candidate Image
    sighting_photo_path = None
    if selected_review.sighting_id:
        s_obj = sighting_repo.get_by_id(selected_review.sighting_id)
        if s_obj:
            sighting_photo_path = s_obj.photo_path

    if not sighting_photo_path and selected_review.source_reference:
        sighting_photo_path = selected_review.source_reference

    with img_col1:
        st.markdown("##### 📍 Candidate Sighting Image")
        if sighting_photo_path and os.path.exists(sighting_photo_path):
            img_candidate = load_image_safely(sighting_photo_path)
            st.image(img_candidate, caption="AI Candidate Sighting Photo", use_container_width=True)
        else:
            st.info("Candidate sighting image placeholder (no local image file path).")

    with img_col2:
        st.markdown("##### 📁 Registered Missing Person Photo")
        if c_obj and c_obj.photo_path and os.path.exists(c_obj.photo_path):
            img_registered = load_image_safely(c_obj.photo_path)
            st.image(img_registered, caption=f"Official Photo: {c_obj.name}", use_container_width=True)
        else:
            st.info("No registered photo file found for this case.")

    st.markdown("---")

    # ── Section 5: Review Action Form ────────────────────────────────
    st.subheader("3. Submit Human Review Decision")

    with st.form(key=f"form_review_{selected_review.id}"):
        st.markdown("Select review decision for this candidate match:")

        decision_choice = st.radio(
            "Review Decision",
            options=["CONFIRMED", "REJECTED", "NEEDS_FURTHER_REVIEW"],
            format_func=lambda d: {
                "CONFIRMED": "🟢 CONFIRM MATCH — Visual features match registered missing person",
                "REJECTED": "🔴 REJECT MATCH — Mark as false positive candidate",
                "NEEDS_FURTHER_REVIEW": "🟡 NEEDS FURTHER REVIEW — Requires additional investigation/evidence"
            }[d],
            index=0
        )

        review_notes = st.text_area(
            "Review Notes & Rationale",
            placeholder="Enter rationale, visual feature observations, or comments...",
            help="Notes will be saved into the permanent immutable audit log."
        )

        confirm_check = st.checkbox(
            "I verify that I have deliberately reviewed the evidence and want to submit this auditable decision."
        )

        btn_submit = st.form_submit_button("💾 Submit Review Decision")

        if btn_submit:
            if not confirm_check:
                st.error("⚠️ Please check the confirmation checkbox to verify your decision.")
            else:
                try:
                    success = review_service.review_match(
                        match_id=selected_review.id,
                        status=decision_choice,
                        current_user=current_user,
                        review_notes=review_notes
                    )
                    if success:
                        st.success(f"✅ **Review Submitted Successfully!** Record status updated to **{decision_choice}**.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to update review decision. Record not found.")
                except ValueError as val_err:
                    st.error(f"⚠️ **Validation Error**: {val_err}")
                except PermissionError as perm_err:
                    st.error(f"🔒 **Authorization Error**: {perm_err}")
                except Exception as exc:
                    st.error(f"⚠️ **Error**: {exc}")

    # ── Section 6: Audit History Trail ────────────────────────────────
    st.markdown("---")
    st.subheader("4. Immutable Audit Trail History")

    audit_history: list[MatchReviewAudit] = review_service.get_audit_trail(selected_review.id, current_user=current_user)

    if not audit_history:
        st.info("No decision audit entries recorded for this match review yet.")
    else:
        for a in audit_history:
            st.markdown(f"""
            <div style="background: rgba(15, 23, 42, 0.6); padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #10b981;">
                <p><b>Timestamp:</b> <code>{a.timestamp}</code> | <b>Reviewer:</b> <code>{a.reviewer_id}</code> (Role: <code>{a.reviewer_role}</code>)</p>
                <p><b>Status Transition:</b> <code>{a.previous_status}</code> ➔ <b style="color: #10b981;">{a.new_status}</b></p>
                <p><b>Notes:</b> <i>{a.review_notes or "No notes provided."}</i></p>
            </div>
            """, unsafe_allow_html=True)
