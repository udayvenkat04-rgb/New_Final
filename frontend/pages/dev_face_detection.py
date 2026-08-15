"""
Face Detection — Development Test Page (Phase 12).

**THIS IS A DEVELOPMENT-ONLY PAGE.** It is not part of the Admin or Officer
dashboard and is not used for case management. It exists purely to exercise
the MediaPipe face detection service end-to-end from the Streamlit runtime.

Flow:
  1. Upload / pick a sample image
  2. Preview
  3. Run Face Landmarker
  4. Display number of detected faces
  5. Display structured result JSON
  6. Display landmark / bounding-box visualization

Auth guard: the page is accessible to any authenticated ADMIN user (because the
service needs no DB write). It does not modify any case / user data.
"""
from __future__ import annotations

import io
import json
from datetime import datetime

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
from backend.utils.face_visualization import (
    draw_face_detection_overlay,
    summarise_detection,
)
from backend.utils.helpers import inject_custom_css
from backend.utils.validators import (
    validate_image_upload,
    MAX_IMAGE_BYTES,
)
from backend.config import settings


# ── Page setup + auth guard ──────────────────────────────────────────
st.set_page_config(
    page_title="Face Detection Dev Test",
    page_icon="🔬",
    layout="wide",
)
inject_custom_css()
require_role([ROLE_ADMIN])

st.markdown(
    "<h2 style='color: #10b981;'>🔬 Face Detection — Phase 12 Dev Test</h2>",
    unsafe_allow_html=True,
)
st.caption(
    "Development-only page that exercises the MediaPipe Face Landmarker "
    "service end-to-end. No case-management / DB changes are performed."
)
st.markdown("---", unsafe_allow_html=True)


# ── Environment / version banner ─────────────────────────────────────
info = get_mediapipe_info()

info_col1, info_col2, info_col3, info_col4 = st.columns(4)
with info_col1:
    st.metric(
        "MediaPipe",
        "Available" if info["mediapipe_available"] else "UNAVAILABLE",
        delta=info.get("mediapipe_version") or "—",
    )
with info_col2:
    st.metric(
        "Landmarks / face",
        info["expected_landmarks_per_face"],
    )
with info_col3:
    st.metric(
        "Max image dim",
        f"{info['max_image_dimension']}px",
    )
with info_col4:
    mp_model_path = getattr(settings, "MEDIAPIPE_MODEL_PATH", "—")
    st.metric(
        "Model file",
        "✅ Found" if (mp_model_path and __import__("os").path.isfile(mp_model_path)) else "❌ Missing",
        delta=str(mp_model_path),
        delta_color="off",
    )

if not info["mediapipe_available"]:
    st.error(
        f"MediaPipe is not importable on this system. Import error: "
        f"`{info.get('mediapipe_import_error')}`. Install with "
        f"`pip install mediapipe` and re-run."
    )
    st.stop()

# Init progress bar / status
init_placeholder = st.empty()
with init_placeholder.status("Initialising Face Landmarker (one-time load)…", expanded=False):
    landmarker, init_err = initialize_face_landmarker()
if init_err is not None:
    init_placeholder.empty()
    st.warning(f"⚠️ Face landmarker not ready yet: {init_err}")
    st.info(
        "Place the `face_landmarker.task` model at the path shown above, or configure "
        "`MEDIAPIPE_MODEL_PATH` in your `.env`. "
        "Download: https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    )

with st.sidebar:
    st.markdown("### 🔬 Detection Parameters")
    p_num_faces = st.slider(
        "Max faces to detect",
        min_value=1,
        max_value=10,
        value=getattr(settings, "MEDIAPIPE_NUM_FACES", 5),
        help="Upper cap on how many simultaneous faces the landmarker will return.",
    )
    p_det_conf = st.slider(
        "Min detection confidence",
        min_value=0.01, max_value=0.99, value=0.5, step=0.01,
        format="%.2f",
    )
    p_pres_conf = st.slider(
        "Min face-presence confidence",
        min_value=0.01, max_value=0.99, value=0.5, step=0.01,
        format="%.2f",
    )
    st.divider()
    st.markdown("### 🎨 Visualization")
    v_box = st.checkbox("Draw bounding box", value=True)
    v_landmarks = st.checkbox("Draw landmark dots", value=True)
    v_label = st.checkbox("Label face index / score", value=True)
    v_radius = st.slider(
        "Landmark dot radius (px)",
        min_value=1, max_value=4, value=1,
    )
    st.divider()
    if st.button("🔄 Re-initialise landmarker (force)", type="secondary"):
        _clear_landmarker_cache()
        st.success("Cleared cached landmarker instance. Next run will reload it.")


# ── Input: file uploader ────────────────────────────────────────────
st.markdown("#### 1️⃣ Upload an image")
uploaded = st.file_uploader(
    "Choose an image file (JPG / JPEG / PNG / WEBP)",
    type=["jpg", "jpeg", "png", "webp"],
    help=f"Max size: {MAX_IMAGE_BYTES // 1024 // 1024} MB. Your upload is "
         "validated before any MediaPipe processing is attempted.",
)

if uploaded is None:
    st.info("☝️ Upload a photograph to begin. Use group photos to test multi-face detection.")
    st.stop()

ok, msg = validate_image_upload(uploaded)
if not ok:
    st.error(f"❌ Upload validation failed: {msg}")
    st.stop()

# Read into PIL + numpy (we keep bytes around for the raw re-read)
uploaded.seek(0)
raw_bytes = uploaded.read()
pil_img = PILImage.open(io.BytesIO(raw_bytes)).convert("RGB")
np_img = np.asarray(pil_img, dtype=np.uint8)

preview_col, meta_col = st.columns([1, 1])
with preview_col:
    st.markdown("**Image Preview**")
    st.image(pil_img, use_container_width=True, caption="Uploaded preview (before detection)")
with meta_col:
    st.markdown("**Image Metadata**")
    w, h = pil_img.size
    size_kb = len(raw_bytes) / 1024.0
    st.write(f"- **Dimensions:** {w}×{h} px")
    st.write(f"- **File size:** {size_kb:,.1f} KB ({len(raw_bytes):,} bytes)")
    st.write(f"- **Mode:** {pil_img.mode}")
    st.write(f"- **Channels:** {np_img.shape[2] if np_img.ndim == 3 else 1}")
    st.write(f"- **Filename (sanitised):** `{uploaded.name}`")

# ── Run detection ───────────────────────────────────────────────────
st.markdown("#### 2️⃣ Run Face Detection")
run_col, status_col = st.columns([1, 3])
with run_col:
    run = st.button("🚀 Detect Faces & Landmarks", type="primary", use_container_width=True)

if not run:
    st.stop()

with st.spinner("Running MediaPipe Face Landmarker…"):
    start_ts = datetime.now()
    try:
        result: FaceDetectionResult = detect_faces(
            np_img,
            num_faces=p_num_faces,
            min_face_detection_confidence=p_det_conf,
            min_face_presence_confidence=p_pres_conf,
        )
    except Exception as exc:  # noqa: BLE001 — UI-level safety net
        result = FaceDetectionResult(
            success=False,
            error_message=f"Unexpected error from face-detection service: {exc}",
        )
    elapsed_ms = int((datetime.now() - start_ts).total_seconds() * 1000)

# ── Report high-level status ────────────────────────────────────────
st.markdown("#### 3️⃣ Detection Summary")
if not result.success:
    st.error(f"❌ Detection did not complete. Reason:\n\n{result.error_message}")
    st.stop()

kpi_face, kpi_land, kpi_dim, kpi_time = st.columns(4)
kpi_face.metric("Faces detected", result.num_faces)
total_landmarks = sum(result.landmarks_per_face())
kpi_land.metric("Total landmarks", total_landmarks)
kpi_dim.metric(
    "Image processed",
    f"{result.image_width}×{result.image_height}",
)
kpi_time.metric("Time", f"{elapsed_ms} ms")

st.success(summarise_detection(result))

# ── Per-face detail cards ───────────────────────────────────────────
st.markdown("#### 4️⃣ Per-Face Details")
if result.num_faces == 0:
    st.info("No faces were detected in this image. Try a different photograph, "
            "a closer crop, or lower the detection-confidence sliders.")
else:
    face_tabs = st.tabs([f"Face {i}" for i in range(result.num_faces)])
    for idx, face in enumerate(result.faces):
        with face_tabs[idx]:
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("Landmarks", face.landmark_count)
            cc2.metric(
                "Presence score",
                f"{face.presence_score:.3f}" if face.presence_score is not None else "—",
            )
            bbox = face.bounding_box_pixels
            if bbox is not None:
                x, y, bw, bh = bbox
                cc3.metric("BBox X,Y", f"{x}, {y}")
                cc4.metric("BBox W×H", f"{bw}×{bh}")
            else:
                cc3.metric("BBox", "n/a")
                cc4.metric("BBox", "n/a")

            with st.expander("First 12 landmark coordinates (X, Y, Z)", expanded=False):
                preview = []
                for lm in face.landmarks[:12]:
                    preview.append({
                        "index": lm.index,
                        "X (norm)": round(lm.x, 5),
                        "Y (norm)": round(lm.y, 5),
                        "Z (depth)": round(lm.z, 5),
                    })
                st.dataframe(preview, hide_index=True, use_container_width=True)
                st.caption(
                    "Ordering is stable and matches the MediaPipe face-mesh "
                    "topology 0..477. Phase 13 will flatten the full list into "
                    "a single 478×3 = 1,434-dimensional embedding vector."
                )

# ── Visualization ────────────────────────────────────────────────────
st.markdown("#### 5️⃣ Visualization")
viz_pil = draw_face_detection_overlay(
    result,
    draw_bounding_box=v_box,
    draw_landmarks=v_landmarks,
    landmark_radius=v_radius,
    draw_face_index_label=v_label,
)
if viz_pil is None:
    st.warning("Visualization returned a blank image — this happens when "
               "detection succeeded but no base image was retained.")
else:
    st.image(viz_pil, use_container_width=True,
             caption="Landmark overlay. Each face is colour-coded; landmark dot "
                     "radius and box/label toggles are available in the sidebar.")

# ── Raw result JSON (for debugging Phase 13 later) ─────────────────
with st.expander("Raw structured result JSON", expanded=False):
    serialisable = {
        "success": result.success,
        "num_faces": result.num_faces,
        "image_width": result.image_width,
        "image_height": result.image_height,
        "error_message": result.error_message,
        "faces": [
            {
                "face_index": f.face_index,
                "landmark_count": f.landmark_count,
                "presence_score": f.presence_score,
                "bounding_box_pixels": f.bounding_box_pixels,
                "first_landmark": (
                    {"index": f.landmarks[0].index, "x": f.landmarks[0].x,
                     "y": f.landmarks[0].y, "z": f.landmarks[0].z}
                    if f.landmarks else None
                ),
            }
            for f in result.faces
        ],
    }
    st.json(json.dumps(serialisable, indent=2, default=str))
