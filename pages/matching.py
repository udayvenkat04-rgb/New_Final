import streamlit as st
import os
import json
from backend.database import check_connection
from backend.auth.permissions import require_role
from backend.services.face_detection import detect_faces
from backend.services.face_embedding import get_face_embedding
from backend.services.face_matching import match_face_embeddings
from backend.utils.helpers import inject_custom_css, save_uploaded_file, load_image_safely
from backend.repositories import CaseRepository, FaceRepository

# Page setup
st.set_page_config(page_title="Admin Face Matching", page_icon="🔬", layout="wide")
inject_custom_css()
require_role(["admin"])

# Redirect to official Admin Face Matching page
st.switch_page("pages/admin_face_matching.py")


st.markdown("<h2 style='color: #10b981;'>🔬 AI Face Matching Search Engine</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8;'>Upload an image of an unidentified person/suspect to run facial search checks against all active missing bulletins.</p>", unsafe_allow_html=True)
st.markdown("---", unsafe_allow_html=True)

# Verify MongoDB availability
connected, db_msg = check_connection()
if not connected:
    st.error(f"⚠️ **Database Connection Error**: {db_msg}")
    st.warning("Please ensure MongoDB is running and your `DATABASE_URL` is configured correctly in `.env`.")
    st.stop()

case_repo = CaseRepository()
face_repo = FaceRepository()

# Upload Section
uploaded_file = st.file_uploader("Upload Image containing Face(s)", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # Save file locally to extract faces
    temp_path = save_uploaded_file(uploaded_file, "data/uploads")
    
    # 1. Run detection
    faces = detect_faces(temp_path)
    
    if not faces:
        st.error("No faces could be detected in the uploaded image. Please try again with a clearer photograph.")
    else:
        st.success(f"Successfully detected {len(faces)} face(s) in the image!")
        
        # If multiple faces, let user select one
        selected_face_idx = 0
        if len(faces) > 1:
            st.write("Multiple faces detected. Select which face you wish to match:")
            
            # Render crops side-by-side for select options
            crop_cols = st.columns(min(len(faces), 5))
            for i, face in enumerate(faces):
                if i < 5:
                    with crop_cols[i]:
                        st.image(face["crop"], caption=f"Face #{i+1}", use_container_width=True)
            
            selected_face_idx = st.radio("Choose Face to Search:", range(len(faces)), format_func=lambda x: f"Face #{x+1}")
            
        selected_face = faces[selected_face_idx]
        
        # Display Selected Target Crop
        st.markdown("### Target Crop Profile")
        st.image(selected_face["crop"], width=150, caption="Selected target face")
        
        if st.button("🔍 Run Face Embedding Matching", type="primary"):
            # 2. Extract Embedding
            query_emb = get_face_embedding(selected_face["crop"])
            
            # 3. Load all registered database face embeddings via repository
            db_embeddings = [f.to_dict() for f in face_repo.get_all_registered()]
            
            if not db_embeddings:
                st.warning("No missing person face profiles registered in the database yet. Search aborted.")
            else:
                db_records = []
                for db_emb in db_embeddings:
                    try:
                        emb_val = db_emb.get("embedding")
                        emb_list = json.loads(emb_val) if isinstance(emb_val, str) else emb_val
                        
                        case_id = db_emb.get("case_id")
                        case_obj_ref = case_repo.get_by_id(case_id)
                        case_obj = case_obj_ref.to_dict() if case_obj_ref else None
                        
                        # Search only active missing persons
                        if case_obj and case_obj.get("status") == "Missing":
                            db_records.append((case_obj, emb_list))
                    except Exception as e:
                        print(f"Error parsing db embedding: {e}")
                        continue
                        
                if not db_records:
                    st.info("No active 'Missing' bulletins found with face embeddings registered.")
                else:
                    # 4. Perform comparison
                    results = match_face_embeddings(query_emb, db_records)
                    
                    st.markdown("### Match Results Summary")
                    
                    strong_matches = [r for r in results if r["confidence"] >= 0.60]
                    
                    if strong_matches:
                        st.toast(f"Match found! Found {len(strong_matches)} candidate(s).", icon="🎯")
                        st.success(f"Match found! Found {len(strong_matches)} high-confidence candidate(s) above threshold.")
                    else:
                        st.warning("No matches found above the similarity threshold. Showing closest candidates:")
                        
                    # Show top 3 matches side-by-side
                    top_k = min(len(results), 3)
                    cols = st.columns(top_k)
                    
                    for i in range(top_k):
                        res = results[i]
                        case_match = res["record"]
                        conf_score = res["confidence"]
                        
                        case_match_name = case_match.get("name")
                        case_match_id = case_match.get("id")
                        
                        with cols[i]:
                            is_match_badge = "badge-found" if conf_score >= 0.60 else "badge-pending"
                            border_color = "#10b981" if conf_score >= 0.60 else "#64748b"
                            
                            st.markdown(f"""
                            <div class="glass-card" style="border-top: 4px solid {border_color};">
                                <h4 style="margin: 0; color: #f1f5f9;">{case_match_name}</h4>
                                <span class="badge {is_match_badge}" style="margin-top: 5px;">Confidence: {conf_score*100:.1f}%</span>
                                <p style="margin: 10px 0 5px 0; font-size: 13px; color: #94a3b8;"><b>Age/Gender:</b> {case_match.get("age")} | {case_match.get("gender")}</p>
                                <p style="margin: 0 0 10px 0; font-size: 13px; color: #94a3b8;"><b>Last Seen:</b> {case_match.get("last_seen_location")}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Show images side-by-side
                            img_cols = st.columns(2)
                            with img_cols[0]:
                                st.image(selected_face["crop"], caption="Target Crop", use_container_width=True)
                            with img_cols[1]:
                                st.image(load_image_safely(case_match.get("photo_path"), case_match_name), caption="Database Photo", use_container_width=True)
                                
                            if st.button(f"📂 Open Bulletin #{case_match_id}", key=f"op_{case_match_id}", use_container_width=True):
                                st.session_state.selected_case_id = case_match_id
                                st.switch_page("pages/cases.py")
