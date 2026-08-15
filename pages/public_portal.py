"""
Public Missing Person Submission Portal (Phase 22).

Mobile-first, responsive Streamlit page accessible without authentication.
Allows citizens to file missing person reports with photograph uploads and track status.
"""

import streamlit as st
from datetime import datetime
from backend.database import check_connection
from backend.utils.helpers import inject_custom_css
from backend.services.public_submission_service import PublicSubmissionService

# Page Configuration - No require_role guard!
st.set_page_config(page_title="Public Missing Person Portal", page_icon="🚨", layout="wide")
inject_custom_css()

st.markdown("<h1 style='text-align: center; color: #10b981; margin-bottom: 0px;'>🚨 Public Missing Person Portal</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 16px;'>File a missing person report or track submission status without logging in.</p>", unsafe_allow_html=True)
st.markdown("---", unsafe_allow_html=True)

# Database Connection Check
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning("Please ensure MongoDB is running on the server.")
    st.stop()

public_service = PublicSubmissionService()

tab_file, tab_track = st.tabs(["📝 File Missing Person Report", "🔍 Track Submission Status"])

# ══════════════════════════════════════════════════════════════════════
# TAB 1: File Missing Person Report
# ══════════════════════════════════════════════════════════════════════
with tab_file:
    st.markdown("### 📋 Missing Person Bulletin Form")
    st.info("ℹ️ All reports are reviewed by authorized law enforcement administrators before entering official databases.")

    with st.form("public_submission_form", clear_on_submit=False):
        # Section 1: Person Information
        st.markdown("#### 👤 1. Missing Person Details")
        c1, c2, c3 = st.columns(3)
        with c1:
            full_name = st.text_input("Full Name *", placeholder="e.g. Rahul Sharma")
        with c2:
            age = st.number_input("Age *", min_value=1, max_value=120, value=25, step=1)
        with c3:
            gender = st.selectbox("Gender *", options=["Male", "Female", "Other", "Prefer not to say"])

        c4, c5 = st.columns(2)
        with c4:
            height = st.text_input("Height (Optional)", placeholder="e.g. 5 ft 8 in / 172 cm")
        with c5:
            identifying_features = st.text_input("Identifying Marks / Features (Optional)", placeholder="e.g. Birthmark on left cheek, tattoo on arm")

        description = st.text_area("Detailed Description (Clothing, last seen appearance, etc.)", placeholder="Provide any additional helpful descriptors...")

        st.markdown("<br>", unsafe_allow_html=True)

        # Section 2: Last Seen Information
        st.markdown("#### 📍 2. Last Seen Information")
        l1, l2 = st.columns(2)
        with l1:
            last_seen_date = st.date_input("Last Seen Date *", value=datetime.utcnow().date())
        with l2:
            last_seen_time = st.text_input("Last Seen Time (Optional)", placeholder="e.g. 14:30 PM")

        l3, l4 = st.columns(2)
        with l3:
            last_seen_city = st.text_input("City *", placeholder="e.g. Pune / Mumbai / Bengaluru")
        with l4:
            last_seen_state = st.text_input("State *", placeholder="e.g. Maharashtra / Karnataka")

        last_seen_location = st.text_input("Specific Location / Landmark *", placeholder="e.g. Near Shivajinagar Railway Station")

        st.markdown("<br>", unsafe_allow_html=True)

        # Section 3: Complainant Information
        st.markdown("#### 📞 3. Complainant Contact Information")
        comp1, comp2 = st.columns(2)
        with comp1:
            complainant_name = st.text_input("Your Full Name (Complainant) *", placeholder="e.g. Sunita Sharma")
        with comp2:
            relationship = st.text_input("Relationship to Missing Person *", placeholder="e.g. Parent / Sibling / Spouse / Friend")

        comp3, comp4 = st.columns(2)
        with comp3:
            contact_email = st.text_input("Your Email Address *", placeholder="e.g. sunita@example.com")
        with comp4:
            contact_phone = st.text_input("Your Contact Phone Number *", placeholder="e.g. +91 9876543210")

        st.markdown("<br>", unsafe_allow_html=True)

        # Section 4: Photograph Upload
        st.markdown("#### 🖼️ 4. Missing Person Photograph Upload")
        uploaded_image = st.file_uploader(
            "Upload Clear Photograph (JPG, PNG - Max 5MB) *",
            type=["jpg", "jpeg", "png"],
            help="Please provide a clear front-facing photograph if available.",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Section 5: Consent Declaration
        st.markdown("#### 📜 5. Declaration & Authorization")
        consent = st.checkbox(
            "I confirm that the information provided is accurate to the best of my knowledge and that I am authorized to submit this missing person report. *"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        submit_btn = st.form_submit_button("📤 Submit Missing Person Report", use_container_width=True)

    if submit_btn:
        image_bytes = None
        filename = None
        if uploaded_image is not None:
            image_bytes = uploaded_image.getvalue()
            filename = uploaded_image.name

        form_payload = {
            "full_name": full_name,
            "age": age,
            "gender": gender,
            "height": height,
            "identifying_features": identifying_features,
            "description": description,
            "last_seen_date": datetime.combine(last_seen_date, datetime.min.time()),
            "last_seen_time": last_seen_time,
            "last_seen_city": last_seen_city,
            "last_seen_state": last_seen_state,
            "last_seen_location": last_seen_location,
            "complainant_name": complainant_name,
            "relationship": relationship,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "consent": consent,
        }

        success, result = public_service.create_public_submission(form_payload, image_bytes, filename)

        if success:
            st.toast("Report submitted successfully!", icon="✅")
            st.success("✅ **Your missing-person report has been submitted successfully!**")
            st.markdown(f"""
            <div class="glass-card" style="padding: 20px; border-left: 4px solid #10b981;">
                <h3 style="margin: 0 0 10px 0; color: #10b981;">Submission Confirmation</h3>
                <p><b>Submission Reference:</b> <code style="font-size: 20px; color: #3b82f6;">{result['submission_reference']}</code></p>
                <p><b>Status:</b> <span class="badge badge-pending">{result['submission_status']}</span></p>
                <p><b>Submitted At:</b> <code>{result['created_at']}</code></p>
                <p style="color: #94a3b8; font-size: 14px; margin-top: 10px;">
                    📌 Please save your <b>Submission Reference Code</b>. Your report will be reviewed by an authorized administrator before entering the official database.
                </p>
            </div>
            """, unsafe_allow_html=True)
            if result.get("is_possible_duplicate"):
                st.warning("ℹ️ Note: A similar case or report was noted. Our administrative team will review and verify details.")
        else:
            st.error(f"❌ **Submission Error**: {result.get('error', 'Failed to process submission.')}")


# ══════════════════════════════════════════════════════════════════════
# TAB 2: Track Submission Status
# ══════════════════════════════════════════════════════════════════════
with tab_track:
    st.markdown("### 🔍 Track Public Report Status")
    st.markdown("<p style='color: #94a3b8;'>Enter your Submission Reference Code to check the verification status of your report.</p>", unsafe_allow_html=True)

    tcol1, tcol2 = st.columns([3, 1])
    with tcol1:
        ref_input = st.text_input("Submission Reference Code", placeholder="e.g. MP-SUB-2026-000123", key="input_ref_track")
    with tcol2:
        st.write("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        track_btn = st.button("🔎 Track Status", use_container_width=True, key="btn_track")

    if track_btn:
        if not ref_input:
            st.warning("Please enter a valid Submission Reference Code.")
        else:
            ok, status_info = public_service.get_public_submission_status(ref_input)
            if ok:
                st.markdown(f"""
                <div class="glass-card" style="padding: 20px; border-left: 4px solid #3b82f6;">
                    <h4 style="margin: 0 0 10px 0; color: #3b82f6;">Report Status Result</h4>
                    <p><b>Reference Code:</b> <code>{status_info['submission_reference']}</code></p>
                    <p><b>Status:</b> <span class="badge badge-pending">{status_info['status']}</span></p>
                    <p><b>Submitted Date:</b> <code>{status_info['submitted_at']}</code></p>
                    <p style="margin-top: 10px; font-size: 14px; color: #cbd5e1;">ℹ️ {status_info['status_message']}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"❌ {status_info.get('error', 'Reference code not found.')}")
