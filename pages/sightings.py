import streamlit as st
from datetime import datetime
from backend.database import check_connection
from backend.auth.permissions import require_role
from backend.utils.helpers import inject_custom_css, load_image_safely
from backend.repositories import CaseRepository, SightingRepository

# Page setup
st.set_page_config(page_title="Sightings Log", page_icon="📍", layout="wide")
inject_custom_css()
require_role(["officer", "admin"])

st.markdown("<h2 style='color: #10b981;'>📍 Sightings Log & Auditing</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Review, edit, audit, and coordinate search operations for all verified or pending sighting logs.</p>", unsafe_allow_html=True)
st.markdown("---", unsafe_allow_html=True)

# Verify MongoDB availability
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning("Please ensure MongoDB is running and your `DATABASE_URL` is configured correctly in `.env`.")
    st.stop()

case_repo = CaseRepository()
sighting_repo = SightingRepository()

# Sighting Filters (rendered horizontally)
fcol1, _ = st.columns([2, 8])
with fcol1:
    status_filter = st.selectbox("Verification Status", ["All", "Pending", "Verified", "Rejected"])

# Query sightings from MongoDB via SightingRepository
query_filter = {}
if status_filter != "All":
    query_filter["status"] = status_filter
    
sightings = [s.to_dict() for s in sighting_repo.get_all(query_filter)]

if not sightings:
    st.info("No sightings logged match the filter criteria.")
else:
    # Display sightings table / cards
    for sight in sightings:
        sight_id = sight.get("id")
        case_id = sight.get("case_id")
        status = sight.get("status")
        
        # Find related case via CaseRepository
        related_case_obj = case_repo.get_by_id(case_id) if case_id else None
        case_name = related_case_obj.name if related_case_obj else "Unidentified (Pending manual link)"
        
        # Badge styles
        badge_class = (
            "badge-verified" if status == "Verified" else 
            ("badge-pending" if status == "Pending" else "badge-missing")
        )
        
        with st.container():
            st.markdown(f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #f1f5f9;">Report #{sight_id} — Target: {case_name}</h4>
                    <span class="badge {badge_class}">{status}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_left, col_right = st.columns([2, 1])
            with col_left:
                sight_time_val = sight.get("sighting_time")
                sight_time_str = sight_time_val.strftime('%Y-%m-%d %H:%M:%S') if isinstance(sight_time_val, datetime) else str(sight_time_val)
                
                st.markdown(f"""
                - 📍 **Address:** {sight.get('address')}
                - 🌐 **Coordinates:** Latitude: `{sight.get('latitude')}`, Longitude: `{sight.get('longitude')}`
                - 📅 **Sighting Time:** {sight_time_str}
                - 👥 **Reporter Info:** {sight.get('reporter_name')} | Contact: {sight.get('reporter_contact')}
                - 📝 **Details/Observation:** *\"{sight.get('details')}\"*
                """)
                
                # Manual Case Linking if Sighting is Unidentified
                if not case_id:
                    st.write("🔧 **Link Sighting to Case:**")
                    all_cases = [c.to_dict() for c in case_repo.get_all({"status": "Missing"})]
                    case_options = {c.get("id"): c.get("name") for c in all_cases}
                    
                    if case_options:
                        link_case_id = st.selectbox(
                            "Select Case", 
                            options=list(case_options.keys()), 
                            format_func=lambda x: case_options[x],
                            key=f"link_sel_{sight_id}"
                        )
                        
                        if st.button("Link & Verify Sighting", key=f"link_btn_{sight_id}"):
                            sighting_repo.link_case(sight_id, link_case_id)
                            # Log history
                            from backend.models import CaseHistory
                            case_repo.log_history(CaseHistory(
                                case_id=link_case_id,
                                action="Sighting Verified",
                                details=f"Sighting #{sight_id} was manually linked and verified."
                            ))
                            st.success("Sighting linked to case and verified successfully!")
                            st.rerun()
                    else:
                        st.write("*No active missing case bulletins found to link.*")
                else:
                    # Actions for linked sightings
                    action_cols = st.columns(3)
                    with action_cols[0]:
                        if status != "Verified":
                            if st.button("✅ Verify", key=f"v_ok_{sight_id}"):
                                sighting_repo.update_status(sight_id, "Verified")
                                st.success("Sighting approved.")
                                st.rerun()
                    with action_cols[1]:
                        if status != "Rejected":
                            if st.button("❌ Reject", key=f"v_rj_{sight_id}"):
                                sighting_repo.update_status(sight_id, "Rejected")
                                st.warning("Sighting rejected.")
                                st.rerun()
                    with action_cols[2]:
                        if st.button("🗑️ Delete Sighting Log", key=f"v_del_{sight_id}", type="primary"):
                            sighting_repo.delete(sight_id)
                            st.error("Sighting deleted.")
                            st.rerun()
                            
            with col_right:
                photo_path = sight.get("photo_path")
                if photo_path:
                    st.image(load_image_safely(photo_path, "Sighting Attachment"), caption="Sighting attachment", use_container_width=True)
                else:
                    st.write("No photo attached to this sighting.")
                    
            st.markdown("<hr style='margin: 15px 0; opacity: 0.1;'/>", unsafe_allow_html=True)
