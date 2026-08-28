"""
Admin Face Matching Dashboard — Phase 16.

Integrates existing AI services (Phase 12 Face Detection, Phase 13 Vector Generation,
Phase 15 KNN Face Matching) into an Admin-only image matching workflow.

Access Control:
- ADMIN role ONLY. Officers and unauthenticated users are blocked.
- Enforced strictly via `require_role([ROLE_ADMIN])`.

Workflow:
Upload Query Image → Face Detection → Select Face → 1,404-D Vector → KNN Match → Ranked Candidates
"""
import io
import hashlib
import numpy as np
import streamlit as st
from PIL import Image as PILImage

from backend.database import check_connection
from backend.auth.permissions import require_role, ROLE_ADMIN
from backend.config.settings import KNN_N_NEIGHBORS, FACE_MATCH_THRESHOLD
from backend.services.face_detection import detect_faces, FaceDetectionResult, DetectedFace
from backend.services.face_embedding import (
    generate_face_vector_by_index,
    FaceEmbeddingError,
)
from backend.services.face_matching import (
    KNNFaceMatchingEngine,
    validate_query_vector,
    InvalidQueryVectorError,
)
from backend.services.case_service import CaseService
from backend.utils.helpers import inject_custom_css, load_image_safely

# Maximum allowed file upload size (100 MB)
MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def _extract_face_crop(rgb_img: np.ndarray, face: DetectedFace) -> np.ndarray:
    """Extract a cropped sub-image for a detected face bounding box/landmarks."""
    if rgb_img is None or rgb_img.size == 0:
        return np.zeros((100, 100, 3), dtype=np.uint8)

    h, w = rgb_img.shape[:2]
    if face.bounding_box_pixels:
        px, py, pw, ph = face.bounding_box_pixels
        pad_w = int(pw * 0.15)
        pad_h = int(ph * 0.15)
        x1 = max(0, px - pad_w)
        y1 = max(0, py - pad_h)
        x2 = min(w, px + pw + pad_w)
        y2 = min(h, py + ph + pad_h)
        crop = rgb_img[y1:y2, x1:x2]
        if crop.size > 0:
            return crop

    if face.landmarks:
        xs = [lm.x * w for lm in face.landmarks]
        ys = [lm.y * h for lm in face.landmarks]
        x1 = max(0, int(min(xs) - 10))
        y1 = max(0, int(min(ys) - 10))
        x2 = min(w, int(max(xs) + 10))
        y2 = min(h, int(max(ys) + 10))
        crop = rgb_img[y1:y2, x1:x2]
        if crop.size > 0:
            return crop

    return rgb_img


def _validate_uploaded_image(file) -> tuple[bool, str, PILImage.Image | None]:
    """Validate uploaded file type, size, and image readability."""
    if file is None:
        return False, "No file uploaded.", None

    filename = getattr(file, "name", "").lower()
    ext = filename.split(".")[-1] if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file format '.{ext}'. Allowed: JPG, JPEG, PNG, WEBP.", None

    bytes_data = file.getvalue()
    if not bytes_data or len(bytes_data) == 0:
        return False, "Uploaded file is empty (0 bytes).", None

    if len(bytes_data) > MAX_UPLOAD_SIZE_BYTES:
        size_mb = len(bytes_data) / (1024 * 1024)
        return False, f"File size ({size_mb:.1f} MB) exceeds maximum allowed 100 MB limit.", None

    try:
        pil_img = PILImage.open(io.BytesIO(bytes_data))
        pil_img.verify()
        # Re-open after verify() as verify() modifies image state
        pil_img = PILImage.open(io.BytesIO(bytes_data)).convert("RGB")
        return True, "Valid image", pil_img
    except Exception as exc:
        return False, f"Failed to read image data: {exc}", None


def render_admin_face_matching_page():
    """Main rendering entrypoint for the Admin Face Matching Dashboard."""
    # ── 1. Page Config & Authorization Guard ─────────────────────────────
    st.set_page_config(page_title="Admin Face Matching", page_icon="🔬", layout="wide")
    inject_custom_css()

    # Enforce Admin-Only Access before executing any page logic
    require_role([ROLE_ADMIN])

    # ── 2. Database Connection Check ──────────────────────────────────────
    connected, db_msg = check_connection()
    if not connected:
        st.error(f"⚠️ **Database Connection Error**: {db_msg}")
        st.warning("Please ensure MongoDB is running and your `DATABASE_URL` is configured in `.env`.")
        st.stop()

    # ── 3. Header & Page Layout ───────────────────────────────────────────
    st.markdown("<h2 style='color: #10b981; margin-bottom: 0;'>🔬 Admin Face Matching Engine</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Centralized AI biometric search portal. Upload a query photograph to execute face detection, 1,404-D vector generation, and KNN similarity matching against registered missing person profiles.</p>", unsafe_allow_html=True)
    st.markdown("---", unsafe_allow_html=True)

    # Sidebar Configuration Controls
    with st.sidebar:
        st.markdown("### ⚙️ KNN Matching Options")
        st.info("Configure matching parameters for this search session.")
        top_k_input = st.number_input("Top Candidates (K)", min_value=1, max_value=20, value=int(KNN_N_NEIGHBORS), step=1)
        threshold_input = st.slider("Match Distance Threshold", min_value=0.05, max_value=1.50, value=float(FACE_MATCH_THRESHOLD), step=0.01, help="Candidates with Euclidean distance <= threshold are flagged as Potential Matches.")

    # ── 4. Step 1 & 2: Image Upload & Preview ────────────────────────────
    st.markdown("### Step 1: Upload Query Image")
    uploaded_file = st.file_uploader(
        "Choose a photograph (JPG, JPEG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"],
        help="Select a clear photograph of an unidentified person to query the system."
    )

    if not uploaded_file:
        st.info("👆 Please upload a query photograph above to start the face matching workflow.")
        st.stop()

    is_valid, validation_msg, pil_image = _validate_uploaded_image(uploaded_file)
    if not is_valid:
        st.error(f"❌ **Image Upload Error**: {validation_msg}")
        st.stop()

    # Compute file hash for session state caching key
    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 2: Image Preview
    img_width, img_height = pil_image.size
    st.markdown("### Step 2: Image Preview & Metadata")
    col_img, col_meta = st.columns([1, 2])

    with col_img:
        st.image(pil_image, caption="Uploaded Query Image", use_container_width=True)

    with col_meta:
        st.markdown(f"""
        <div class="glass-card" style="padding: 16px;">
            <h4 style="margin-top:0; color:#10b981;">📷 Query Image Attributes</h4>
            <p style="margin: 4px 0; color:#cbd5e1;"><b>Dimensions:</b> {img_width} × {img_height} pixels</p>
            <p style="margin: 4px 0; color:#cbd5e1;"><b>Format / Mode:</b> {uploaded_file.type or 'Image'} ({pil_image.mode})</p>
            <p style="margin: 4px 0; color:#cbd5e1;"><b>File Size:</b> {len(file_bytes) / 1024:.1f} KB</p>
            <p style="margin: 4px 0; color:#10b981;"><b>Validation Status:</b> Passed ✓</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---", unsafe_allow_html=True)

    # ── 5. Step 3: Face Detection (Phase 12 Service) ─────────────────────
    st.markdown("### Step 3: MediaPipe Face Detection")

    if "detection_file_hash" not in st.session_state or st.session_state.detection_file_hash != file_hash:
        with st.spinner("Detecting faces using MediaPipe Landmarker..."):
            try:
                rgb_arr = np.asarray(pil_image, dtype=np.uint8)
                det_result = detect_faces(rgb_arr)
                st.session_state.detection_result = det_result
                st.session_state.detection_file_hash = file_hash
                st.session_state.selected_face_index = 0
                st.session_state.match_result = None
            except Exception as exc:
                st.error(f"❌ **Face Detection Failed**: {exc}")
                st.stop()

    det_result: FaceDetectionResult = st.session_state.get("detection_result")

    if not det_result or not det_result.success:
        err_msg = det_result.error_message if det_result else "Unknown detection error."
        st.error(f"❌ **Face Detection Error**: {err_msg}")
        st.stop()

    if det_result.num_faces == 0:
        st.warning("⚠️ **No face detected in the uploaded image.**")
        st.info("Please upload a clearer front-facing photograph where facial features are distinctly visible.")
        st.stop()

    st.success(f"✅ Successfully detected **{det_result.num_faces}** face(s) in the uploaded image.")

    # ── 6. Step 4: Multiple Face Handling ──────────────────────────────────
    st.markdown("### Step 4: Face Selection")
    selected_face_idx = 0
    rgb_processed = det_result.processed_image_rgb if det_result.processed_image_rgb is not None else np.asarray(pil_image, dtype=np.uint8)

    if det_result.num_faces > 1:
        st.info(f"Multiple faces ({det_result.num_faces}) detected. Please select the specific face to generate a 1,404-D vector for matching.")
        
        crop_cols = st.columns(min(det_result.num_faces, 5))
        for idx, face in enumerate(det_result.faces[:5]):
            crop_img = _extract_face_crop(rgb_processed, face)
            with crop_cols[idx]:
                st.image(crop_img, caption=f"Face {idx + 1}", use_container_width=True)

        face_options = [f"Face {i + 1}" for i in range(det_result.num_faces)]
        selected_face_str = st.radio("Choose Target Face:", face_options, index=st.session_state.selected_face_index)
        selected_face_idx = face_options.index(selected_face_str)
        st.session_state.selected_face_index = selected_face_idx
    else:
        selected_face_idx = 0
        st.session_state.selected_face_index = 0

    selected_face: DetectedFace = det_result.faces[selected_face_idx]
    selected_crop = _extract_face_crop(rgb_processed, selected_face)

    col_target_img, col_target_info = st.columns([1, 3])
    with col_target_img:
        st.image(selected_crop, caption=f"Selected Face: Face {selected_face_idx + 1}", width=160)

    with col_target_info:
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid #10b981; border-radius: 8px; padding: 12px 16px; margin-top: 10px;">
            <h4 style="margin: 0; color: #10b981;">Selected Target Face: Face {selected_face_idx + 1}</h4>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px;">
                Landmarks Extracted: <b>{selected_face.landmark_count}</b> MediaPipe points | 
                Ready for 1,404-D vector normalization.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---", unsafe_allow_html=True)

    # ── 7. Step 5: 1,404-D Vector Generation (Phase 13 Service) ────────────
    st.markdown("### Step 5: 1,404-Dimensional Vector Generation")

    query_vector = None
    try:
        with st.spinner("Generating 1,404-D normalized landmark vector..."):
            query_vector = generate_face_vector_by_index(
                det_result,
                face_index=selected_face_idx,
                expected_landmarks=468
            )
            validated_q_vec = validate_query_vector(query_vector, expected_dim=1404)
    except FaceEmbeddingError as exc:
        st.error(f"❌ **Vector Generation Error**: {exc}")
        st.stop()
    except InvalidQueryVectorError as exc:
        st.error(f"❌ **Vector Validation Error**: {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"❌ **Unexpected Vector Error**: {exc}")
        st.stop()

    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        st.metric(label="Vector Generated", value="Yes ✓")
    with col_v2:
        st.metric(label="Vector Dimensions", value=f"{len(validated_q_vec)}")
    with col_v3:
        st.metric(label="Numerical Validation", value="Passed (Finite float32)")

    st.markdown("---", unsafe_allow_html=True)

    # ── 8. Step 6 & 7: KNN Matching & Ranked Candidates (Phase 15) ────────
    st.markdown("### Step 6 & 7: KNN Search & Potential Match Results")

    run_matching = st.button("🚀 Run KNN Face Vector Search", type="primary", use_container_width=True)

    if run_matching or "match_result" in st.session_state and st.session_state.match_result is not None:
        with st.spinner("Searching reference database, computing Euclidean distances, and ranking candidates..."):
            try:
                knn_engine = KNNFaceMatchingEngine()
                match_res = knn_engine.match_vector(
                    validated_q_vec,
                    top_k=top_k_input,
                    threshold=threshold_input
                )
                st.session_state.match_result = match_res
            except Exception as exc:
                st.error(f"❌ **KNN Search Error**: {exc}")
                st.stop()

    match_res = st.session_state.get("match_result")

    if match_res is not None:
        status_code = match_res.get("status")
        candidates = match_res.get("candidates", [])
        num_ref = match_res.get("num_reference_vectors", 0)

        if status_code == "NO_REFERENCE_VECTORS" or num_ref == 0:
            st.warning("⚠️ **No Reference Vectors Stored**: The database currently contains 0 registered missing person face profiles. Please register missing person cases with photos first.")
            st.stop()

        if status_code == "NO_POTENTIAL_MATCH" or not any(c.get("is_potential_match") for c in candidates):
            st.warning("ℹ️ **No Potential Matches Found**: No candidate in the database met the specified match threshold.")
            st.write(f"Displaying top **{len(candidates)}** closest reference candidates for review:")
        else:
            potential_count = sum(1 for c in candidates if c.get("is_potential_match"))
            st.success(f"🎉 **Potential Matches Identified**: Found **{potential_count}** candidate(s) meeting the match threshold!")

        case_service = CaseService()
        current_user = st.session_state.get("user")

        st.markdown("#### 📊 Ranked Candidates")

        for cand in candidates:
            rank = cand.get("rank")
            case_id = cand.get("case_id")
            distance = cand.get("distance")
            similarity = cand.get("similarity_score")
            is_potential = cand.get("is_potential_match")

            case_obj = None
            try:
                case_obj = case_service.get_case(case_id, current_user=current_user)
            except Exception:
                case_obj = None

            case_num = getattr(case_obj, "case_number", f"MP-{case_id}") if case_obj else f"Case #{case_id}"
            person_name = getattr(case_obj, "name", "Unknown Person") if case_obj else "Unknown"
            age = getattr(case_obj, "age", "N/A") if case_obj else "N/A"
            gender = getattr(case_obj, "gender", "N/A") if case_obj else "N/A"
            city = getattr(case_obj, "last_seen_city", "N/A") if case_obj else "N/A"
            state = getattr(case_obj, "last_seen_state", "N/A") if case_obj else "N/A"

            decision_label = "POTENTIAL MATCH" if is_potential else "NO POTENTIAL MATCH"
            border_color = "#10b981" if is_potential else "#475569"
            badge_bg = "rgba(16, 185, 129, 0.2)" if is_potential else "rgba(100, 116, 139, 0.2)"
            badge_color = "#10b981" if is_potential else "#94a3b8"

            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid {border_color}; padding: 18px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span style="background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 4px; font-weight: 700; color: #f1f5f9; font-size: 13px;">
                            RANK #{rank}
                        </span>
                        <span style="font-size: 18px; font-weight: 700; color: #f1f5f9; margin-left: 12px;">
                            {person_name}
                        </span>
                        <span style="font-size: 14px; color: #94a3b8; margin-left: 8px;">
                            ({case_num})
                        </span>
                    </div>
                    <div>
                        <span style="background: {badge_bg}; color: {badge_color}; padding: 6px 14px; border-radius: 12px; font-weight: 700; font-size: 13px;">
                            {decision_label}
                        </span>
                    </div>
                </div>
                <div style="display: flex; gap: 24px; margin-top: 12px; color: #cbd5e1; font-size: 14px; flex-wrap: wrap;">
                    <div><b>Age / Gender:</b> {age} | {gender}</div>
                    <div><b>Location:</b> {city}, {state}</div>
                    <div><b>Euclidean Distance:</b> {distance:.4f}</div>
                    <div><b>Similarity Score:</b> <span style="color: {border_color}; font-weight: 700;">{similarity:.1f}%</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"🔍 View Detailed Case Files — {person_name} ({case_num})"):
                if not case_obj:
                    st.warning("Case details could not be retrieved from repository.")
                else:
                    d_col1, d_col2 = st.columns([1, 2])
                    with d_col1:
                        photo_pil = load_image_safely(getattr(case_obj, "photo_path", None), person_name)
                        st.image(photo_pil, caption=f"Registered Photo: {person_name}", use_container_width=True)

                    with d_col2:
                        st.markdown(f"""
                        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid #f59e0b; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">
                            <b style="color: #f59e0b;">⚠️ Potential Match — Human Review Required</b>
                            <p style="margin: 2px 0 0 0; font-size: 12px; color: #cbd5e1;">This candidate match is a biometrical recommendation based on 1,404-D landmark KNN distance. Final confirmation requires manual verification by an authorized investigating officer.</p>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown(f"**Case Number:** `{case_obj.case_number}`")
                        st.markdown(f"**Full Name:** {case_obj.name}")
                        st.markdown(f"**Age / Gender:** {case_obj.age} years | {case_obj.gender}")
                        st.markdown(f"**Current Status:** `{case_obj.status}`")
                        st.markdown(f"**Last Seen Location:** {case_obj.last_seen_location or 'N/A'}")
                        st.markdown(f"**City / State:** {case_obj.last_seen_city or 'N/A'}, {case_obj.last_seen_state or 'N/A'}")
                        st.markdown(f"**Last Seen Date:** {case_obj.last_seen_date.strftime('%Y-%m-%d') if case_obj.last_seen_date else 'N/A'}")
                        st.markdown(f"**Description:** {case_obj.description or 'No additional description.'}")
                        st.markdown(f"**Calculated Distance:** `{distance:.4f}`")
                        st.markdown(f"**Calculated Similarity:** `{similarity:.1f}%`")

    # ── 9. Footer ───────────────────────────────────────────────────────
    st.markdown("---", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: #475569; font-size: 12px;'>"
        "Missing Person Identification System · Phase 16 Admin Face Matching Dashboard · "
        "MediaPipe Tasks & Scikit-Learn KNN Service Integration"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    render_admin_face_matching_page()

