"""
Face Embedding — Development Test Page (Phase 13).

**THIS IS A DEVELOPMENT-ONLY PAGE.** Not part of Admin or Officer dashboards.

Flow:
  1. Upload / pick a sample image
  2. Run Phase 12 Face Landmarker → detect faces + landmarks
  3. Show detected face count
  4. If multiple faces exist → allow user to select which face to vectorize
  5. Run Phase 13 generate_face_vector → produce the 1,404-D NumPy vector
  6. Display:
        Face index
        Landmark count
        Vector dimensions
        Vector shape
        Vector dtype
        Validation result (pass/fail)
     + Debug preview: first 10 vector values (NOT all 1,404).
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import numpy as np
import streamlit as st
from PIL import Image as PILImage

from backend.auth.permissions import require_role, ROLE_ADMIN
from backend.services.face_detection import (
    FaceDetectionResult,
    detect_faces,
    get_mediapipe_info,
    initialize_face_landmarker,
    _clear_landmarker_cache,
)
from backend.services.face_embedding import (
    DEFAULT_VECTOR_DIM,
    FaceEmbeddingError,
    VectorValidationReport,
    generate_face_vector_by_index,
    generate_vectors_for_all_faces,
    get_embedding_config,
    validate_face_vector,
)
from backend.utils.face_visualization import draw_face_detection_overlay
from backend.utils.helpers import inject_custom_css
from backend.utils.validators import validate_image_upload, MAX_IMAGE_BYTES
from backend.config import settings


# ── Page setup + auth guard ──────────────────────────────────────────
st.set_page_config(
    page_title="Face Embedding Dev Test",
    page_icon="🧬",
    layout="wide",
)
inject_custom_css()
require_role([ROLE_ADMIN])

st.markdown(
    "<h2 style='color: #8b5cf6;'>🧬 Face Vector Generation — Phase 13 Dev Test</h2>",
    unsafe_allow_html=True,
)
st.caption(
    "Development-only page that runs Phase 12 face detection and then Phase 13 "
    "vector generation end-to-end. Produces a deterministic 1,404-dimensional "
    "float32 vector per detected face. No database writes are performed."
)
st.markdown("---", unsafe_allow_html=True)


# ── Environment / version banner ─────────────────────────────────────
mp_info = get_mediapipe_info()
emb_cfg = get_embedding_config()

info_cols = st.columns(5)
with info_cols[0]:
    st.metric(
        "MediaPipe",
        "Available" if mp_info["mediapipe_available"] else "UNAVAILABLE",
        delta=mp_info.get("mediapipe_version") or "—",
    )
with info_cols[1]:
    st.metric("Landmarks / face", emb_cfg["default_landmarks_per_face"])
with info_cols[2]:
    st.metric("Vector dimensions", f"{emb_cfg['default_vector_dim']}D")
with info_cols[3]:
    st.metric("Vector dtype", emb_cfg["default_vector_dtype"])
with info_cols[4]:
    mp_model_path = getattr(settings, "MEDIAPIPE_MODEL_PATH", "—")
    model_ok = mp_model_path and __import__("os").path.isfile(mp_model_path)
    st.metric(
        "Model file",
        "✅ Found" if model_ok else "❌ Missing",
        delta=str(mp_model_path),
        delta_color="off",
    )

if not mp_info["mediapipe_available"]:
    st.error(
        f"MediaPipe is not importable. Import error: `{mp_info.get('mediapipe_import_error')}`. "
        f"Install with `pip install mediapipe` and re-run."
    )
    st.stop()

with st.sidebar:
    st.markdown("### 🔬 Detection + Embedding Parameters")
    p_num_faces = st.slider(
        "Max faces to detect",
        min_value=1, max_value=10,
        value=getattr(settings, "MEDIAPIPE_NUM_FACES", 5),
    )
    p_det_conf = st.slider(
        "Min detection confidence",
        min_value=0.01, max_value=0.99, value=0.5, step=0.01, format="%.2f",
    )
    p_pres_conf = st.slider(
        "Min face-presence confidence",
        min_value=0.01, max_value=0.99, value=0.5, step=0.01, format="%.2f",
    )
    st.divider()
    st.markdown("### 🎨 Visualization")
    v_box = st.checkbox("Draw bounding box", value=True)
    v_landmarks = st.checkbox("Draw landmark dots", value=True)
    v_radius = st.slider("Landmark dot radius (px)", min_value=1, max_value=4, value=1)
    st.divider()
    if st.button("🔄 Re-initialise landmarker", type="secondary"):
        _clear_landmarker_cache()
        st.success("Cleared cached landmarker instance.")


# ── Init landmarker (one-time) ───────────────────────────────────────
init_placeholder = st.empty()
with init_placeholder.status("Initialising Face Landmarker (one-time load)…", expanded=False):
    landmarker, init_err = initialize_face_landmarker()
if init_err is not None:
    init_placeholder.empty()
    st.warning(f"⚠️ Face landmarker not ready: {init_err}")
    st.info(
        "Place `face_landmarker.task` at the path shown above, or set "
        "`MEDIAPIPE_MODEL_PATH` in `.env`. Download: "
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    )


# ── Step 1: Upload image ─────────────────────────────────────────────
st.markdown("#### 1️⃣ Upload an image")
uploaded = st.file_uploader(
    "Choose an image file (JPG / JPEG / PNG / WEBP). Group shots exercise multi-face selection.",
    type=["jpg", "jpeg", "png", "webp"],
    help=f"Max size: {MAX_IMAGE_BYTES // 1024 // 1024} MB.",
)

if uploaded is None:
    st.info("☝️ Upload a photograph to begin. Try a group photo to test multi-face vectorization.")
    with st.expander("📘 Normalization method (Phase 13)", expanded=False):
        st.markdown(
            "The 1,404-D vector is produced by:\n\n"
            "1. **Mean-centre** every 3-D landmark (translation invariant).\n"
            "2. **Divide X, Y, Z** by the Euclidean distance from the mean centre\n"
            "   to the single farthest landmark in the XY image plane\n"
            "   (scale invariant — the face always fits inside a unit radius).\n"
            "3. **Flatten** in landmark-major order:\n"
            "   `X0, Y0, Z0,  X1, Y1, Z1,  … ,  X467, Y467, Z467`.\n\n"
            "This exact same normalisation is used for *both* registered\n"
            "missing-person images *and* sighting/query images in Phase 14+."
        )
    st.stop()

ok, msg = validate_image_upload(uploaded)
if not ok:
    st.error(f"❌ Upload validation failed: {msg}")
    st.stop()

uploaded.seek(0)
raw_bytes = uploaded.read()
pil_img = PILImage.open(io.BytesIO(raw_bytes)).convert("RGB")
np_img = np.asarray(pil_img, dtype=np.uint8)

prev_col, meta_col = st.columns([1, 1])
with prev_col:
    st.markdown("**Image Preview**")
    st.image(pil_img, use_container_width=True)
with meta_col:
    st.markdown("**Image Metadata**")
    w, h = pil_img.size
    size_kb = len(raw_bytes) / 1024.0
    st.write(f"- **Dimensions:** {w}×{h} px")
    st.write(f"- **File size:** {size_kb:,.1f} KB")
    st.write(f"- **Mode:** {pil_img.mode}")
    st.write(f"- **Filename:** `{uploaded.name}`")


# ── Step 2: Detect faces (Phase 12) ──────────────────────────────────
st.markdown("#### 2️⃣ Detect Faces & Generate Vectors")
run_col, _ = st.columns([1, 3])
with run_col:
    run = st.button("🚀 Detect + Vectorize", type="primary", use_container_width=True)

if not run:
    st.stop()

with st.spinner("Running Phase 12 detection, then Phase 13 vector generation…"):
    start_ts = datetime.now()
    try:
        result: FaceDetectionResult = detect_faces(
            np_img,
            num_faces=p_num_faces,
            min_face_detection_confidence=p_det_conf,
            min_face_presence_confidence=p_pres_conf,
        )
    except Exception as exc:  # noqa: BLE001
        result = FaceDetectionResult(
            success=False,
            error_message=f"Unexpected error from face-detection service: {exc}",
        )
    detect_ms = int((datetime.now() - start_ts).total_seconds() * 1000)


# ── Step 3: Detection summary ────────────────────────────────────────
st.markdown("#### 3️⃣ Detection Summary")
if not result.success:
    st.error(f"❌ Detection did not complete:\n\n{result.error_message}")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Faces detected", result.num_faces)
total_landmarks = sum(result.landmarks_per_face())
k2.metric("Total landmarks", total_landmarks)
k3.metric("Image processed", f"{result.image_width}×{result.image_height}")
k4.metric("Detection time", f"{detect_ms} ms")


# ── Visualization overlay ────────────────────────────────────────────
viz_pil = draw_face_detection_overlay(
    result,
    draw_bounding_box=v_box,
    draw_landmarks=v_landmarks,
    landmark_radius=v_radius,
    draw_face_index_label=True,
)
if viz_pil is not None:
    st.image(
        viz_pil,
        use_container_width=True,
        caption="Face-detection overlay. Each face has an index label — "
                "use the selector below to pick which face to vectorize.",
    )

if result.num_faces == 0:
    st.info("No faces were detected. Try a different photograph, a closer crop, "
            "or lower the detection-confidence sliders in the sidebar.")
    st.stop()


# ── Step 4: Select face (multi-face only) ────────────────────────────
st.markdown("#### 4️⃣ Select a face to vectorize")
if result.num_faces == 1:
    selected_face_index = 0
    st.info("Exactly 1 face detected — using `face_index = 0`.")
else:
    options = [f"Face {i}  (landmarks: {result.faces[i].landmark_count}, "
               f"score: {result.faces[i].presence_score:.3f})"
               for i in range(result.num_faces)]
    sel_label = st.selectbox(
        "Multiple faces detected — pick one. Each face gets its *own* independent "
        f"{DEFAULT_VECTOR_DIM}-D vector; we never combine multiple faces into one.",
        options,
        index=0,
    )
    selected_face_index = options.index(sel_label)


# ── Step 5: Generate the 1,404-D vector ──────────────────────────────
st.markdown("#### 5️⃣ Face Vector Generation")
embed_start = datetime.now()
vectors: list[np.ndarray] = []
try:
    vectors = generate_vectors_for_all_faces(result)
except FaceEmbeddingError as exc:
    st.error(f"❌ Vector generation failed for one or more faces: {exc}")
    st.stop()
embed_ms = int((datetime.now() - embed_start).total_seconds() * 1000)

vector = vectors[selected_face_index]
report: VectorValidationReport = validate_face_vector(vector)

# KPI cards for the selected vector
vc1, vc2, vc3, vc4 = st.columns(4)
vc1.metric("Face index", selected_face_index, delta=f"of {result.num_faces}")
vc2.metric(
    "Landmark count",
    result.faces[selected_face_index].landmark_count,
    delta=f"→ {DEFAULT_VECTOR_DIM}D",
)
vc3.metric(
    "Vector shape",
    f"({vector.shape[0]},)" if vector.ndim == 1 else str(vector.shape),
    delta="1-D",
)
status_ok = report.is_valid
vc4.metric(
    "Validation",
    "✅ VALID" if status_ok else "❌ INVALID",
    delta=f"{vector.dtype}",
    delta_color="normal" if status_ok else "inverse",
)

st.metric("Vector generation time", f"{embed_ms} ms total for {result.num_faces} face(s)")

if not status_ok:
    st.error(
        "Generated vector **failed** numerical validation:\n\n"
        + "\n".join(f"- {e}" for e in report.errors)
    )


# ── Step 6: Detailed per-face info + validation ─────────────────────
st.markdown("#### 6️⃣ Detailed Per-Face Vector Reports")
face_tabs = st.tabs([f"Face {i} — Vector Report" for i in range(result.num_faces)])
for idx in range(result.num_faces):
    with face_tabs[idx]:
        v = vectors[idx]
        r = validate_face_vector(v)

        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("Face index", idx)
        cc2.metric("Landmarks", result.faces[idx].landmark_count)
        cc3.metric("Vector dimensions", v.shape[0])
        cc4.metric(
            "Validation",
            "✅ PASS" if r.is_valid else "❌ FAIL",
            delta=str(v.dtype),
        )

        with st.expander("Full validation report", expanded=(idx == selected_face_index)):
            st.write(f"- **Shape:** `{r.shape}`  (expected `{r.expected_shape}`)")
            st.write(f"- **Dtype:** `{r.dtype}`  (matches canonical `float32`: {r.expected_dtype_match})")
            st.write(f"- **Has NaN:** {r.has_nan}")
            st.write(f"- **Has Inf:** {r.has_inf}")
            st.write(f"- **All finite:** {r.all_finite}")
            if r.errors:
                st.error("Errors:\n\n" + "\n".join(f"- {e}" for e in r.errors))
            else:
                st.success("No validation errors.")

        with st.expander("🔬 Debug preview — first 10 vector values", expanded=(idx == selected_face_index)):
            preview_n = 10
            first = v[:preview_n]
            rows = []
            for i in range(preview_n):
                lm_idx = i // 3
                coord = ["X", "Y", "Z"][i % 3]
                rows.append({
                    "pos": i,
                    "landmark": lm_idx,
                    "coord": coord,
                    "value": f"{first[i]:+.8f}",
                })
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption(
                f"Showing values 0…{preview_n - 1} of {v.size} total. "
                "Landmark-major layout confirmed (X0,Y0,Z0,X1,Y1,Z1,…). "
                "Remaining 1,394 values are hidden in the UI by design."
            )

        with st.expander("Numerical stats (full 1,404 values)", expanded=False):
            stats = {
                "min": f"{float(v.min()):+.6f}",
                "max": f"{float(v.max()):+.6f}",
                "mean": f"{float(v.mean()):+.6f}",
                "std": f"{float(v.std()):.6f}",
                "L2 norm": f"{float(np.linalg.norm(v)):.6f}",
                "sum(abs)": f"{float(np.sum(np.abs(v))):.6f}",
            }
            st.write(stats)


# ── Step 7: Determinism sanity check ─────────────────────────────────
st.markdown("#### 7️⃣ Determinism Check")
with st.spinner("Regenerating the same vectors and comparing…"):
    try:
        vectors_again = generate_vectors_for_all_faces(result)
    except FaceEmbeddingError as exc:
        st.error(f"Second pass failed: {exc}")
        st.stop()

all_deterministic = True
for idx in range(result.num_faces):
    identical = np.array_equal(vectors[idx], vectors_again[idx])
    if not identical:
        all_deterministic = False
        break

if all_deterministic:
    st.success(
        f"✅ **Deterministic:** Re-running the pipeline on the same detection "
        f"produced byte-identical vectors for all {result.num_faces} face(s). "
        "This guarantees reproducible embeddings for matching."
    )
else:
    st.warning(
        "⚠️ Non-determinism detected — a second pass on the same detection "
        "produced different values. This should not happen and indicates a bug."
    )
