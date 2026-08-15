"""
Video Sightings — AI Face Recognition & Matching Page (Phase 18).

Only authenticated ADMIN users can access this page.

Workflow:
1. Upload surveillance video (.mp4, .avi, .mov, .mkv)
2. Preview video & validate metadata
3. Configure sampling interval, temporal grouping gap & match threshold
4. Run Video AI Analysis (MediaPipe Detection -> 1,404D Vector -> KNN Engine -> Temporal Aggregation)
5. Display detailed processing statistics
6. Display aggregated candidate missing person sightings with representative frames
"""

from __future__ import annotations

import os
import time
import streamlit as st

from backend.auth.permissions import require_role, ROLE_ADMIN
from backend.config import settings
from backend.services.video_ai_service import (
    AggregatedVideoSighting,
    VideoAIScanResult,
    VideoAIService,
)
from backend.services.video_processing import (
    ExtractionResult,
    SampledFrame,
    VideoMetadata,
    VideoValidationResult,
    save_temporary_video,
    sample_frames,
    validate_video,
)
from backend.utils.helpers import inject_custom_css

# ── Page setup & Admin auth guard ────────────────────────────────────
st.set_page_config(
    page_title="Video Sightings AI",
    page_icon="📹",
    layout="wide",
)
inject_custom_css()

# Enforce Admin Authorization Guard
try:
    require_role([ROLE_ADMIN])
except PermissionError as perm_err:
    st.error(f"🔒 **Access Denied**: {perm_err}")
    st.warning("Only authenticated System Administrators have permission to run AI Video Matching.")
    st.stop()

st.markdown(
    "<h2 style='color: #10b981;'>📹 Video Sightings — Biometric AI Matching</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color: #94a3b8;'>Upload video surveillance feeds to detect human faces, extract 1,404-D biometric vectors, query the KNN matching engine, and generate cross-frame aggregated sightings of missing persons.</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Initialize Session State ─────────────────────────────────────────
if "video_extraction_result" not in st.session_state:
    st.session_state.video_extraction_result = None
if "video_ai_result" not in st.session_state:
    st.session_state.video_ai_result = None
if "active_video_temp_path" not in st.session_state:
    st.session_state.active_video_temp_path = None
if "video_meta" not in st.session_state:
    st.session_state.video_meta = None
if "page_number" not in st.session_state:
    st.session_state.page_number = 1

# ── Section 1: Video File Upload ─────────────────────────────────────
st.subheader("1. Upload Surveillance Video")

max_size_mb = getattr(settings, "MAX_VIDEO_SIZE_MB", 100)
allowed_exts = sorted(list(getattr(settings, "ALLOWED_VIDEO_EXTENSIONS", {".mp4", ".avi", ".mov", ".mkv"})))
allowed_exts_clean = [ext.lstrip(".") for ext in allowed_exts]

uploaded_file = st.file_uploader(
    f"Select video file ({', '.join(allowed_exts_clean).upper()}) — Max limit: {max_size_mb} MB",
    type=allowed_exts_clean,
    help="Upload a video recording of a sighting or location feed."
)

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    temp_path, cleanup_fn = save_temporary_video(file_bytes, filename=uploaded_file.name)

    val_res: VideoValidationResult = validate_video(temp_path, max_size_mb=max_size_mb)

    if not val_res.is_valid:
        st.error(f"❌ **Video Validation Failed**: {val_res.error_message}")
        cleanup_fn()
    else:
        st.success("✅ **Video Validated Successfully!**")
        st.session_state.video_meta = val_res.metadata
        st.session_state.active_video_temp_path = temp_path

        col_left, col_right = st.columns([1, 1])

        # Video Preview
        with col_left:
            st.markdown("#### 📺 Video Preview")
            st.video(file_bytes)

        # Video Metadata Metrics Card
        with col_right:
            st.markdown("#### 📊 Video Metadata")
            meta: VideoMetadata = val_res.metadata
            file_size_mb = len(file_bytes) / (1024 * 1024)

            st.markdown(f"""
            <div class="glass-card" style="padding: 15px;">
                <p><b>Filename:</b> <code>{meta.filename}</code></p>
                <p><b>Resolution:</b> <code>{meta.width} x {meta.height}</code> pixels</p>
                <p><b>FPS (Frames/Sec):</b> <code>{meta.fps:.2f}</code></p>
                <p><b>Total Video Frames:</b> <code>{meta.total_frame_count}</code></p>
                <p><b>Duration:</b> <code>{meta.duration_seconds:.2f} s</code> ({int(meta.duration_seconds // 60)}m {int(meta.duration_seconds % 60)}s)</p>
                <p><b>Codec:</b> <code>{meta.codec}</code></p>
                <p><b>File Size:</b> <code>{file_size_mb:.2f} MB</code></p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Section 2: Pipeline Configuration ────────────────────────────
        st.subheader("2. Configure Video AI Analysis Pipeline")

        default_interval = float(getattr(settings, "VIDEO_SAMPLE_INTERVAL_SECONDS", 1.0))
        default_gap = float(getattr(settings, "VIDEO_SIGHTING_GAP_SECONDS", 5.0))
        default_thresh = float(getattr(settings, "FACE_MATCH_THRESHOLD", 0.60))
        max_frame_limit = int(getattr(settings, "MAX_VIDEO_FRAMES_TO_PROCESS", 500))

        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)

        with col_cfg1:
            sample_interval = st.slider(
                "Frame Sampling Interval (seconds)",
                min_value=0.1,
                max_value=5.0,
                value=default_interval,
                step=0.1,
                help="Sampling 1.0s extracts 1 frame every 1 second of video."
            )

        with col_cfg2:
            gap_seconds = st.slider(
                "Temporal Grouping Gap (seconds)",
                min_value=1.0,
                max_value=30.0,
                value=default_gap,
                step=1.0,
                help="Max gap between detections before creating a new temporal segment."
            )

        with col_cfg3:
            match_thresh = st.slider(
                "KNN Distance Threshold",
                min_value=0.30,
                max_value=0.90,
                value=default_thresh,
                step=0.05,
                help="Max Euclidean distance for a candidate to be considered a match."
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Section 3: Trigger Execution Buttons ──────────────────────────
        bcol1, bcol2 = st.columns(2)

        with bcol1:
            if st.button("🤖 Start Video AI Matching (Phase 18)", key="btn_run_ai"):
                st.session_state.video_extraction_result = None
                progress_bar = st.progress(0.0)
                status_text = st.empty()

                def ai_progress_callback(percent: float, text: str):
                    progress_bar.progress(percent)
                    status_text.markdown(f"⏳ **{text}**")

                ai_service = VideoAIService()
                start_t = time.time()
                ai_res: VideoAIScanResult = ai_service.process_video_ai(
                    temp_path,
                    sample_interval_seconds=sample_interval,
                    max_frames_to_process=max_frame_limit,
                    threshold=match_thresh,
                    gap_seconds=gap_seconds,
                    progress_callback=ai_progress_callback
                )
                elapsed = time.time() - start_t

                st.session_state.video_ai_result = ai_res
                st.session_state.ai_elapsed = elapsed
                status_text.markdown(f"✅ **Video AI Analysis Completed in {elapsed:.2f} seconds!**")

        with bcol2:
            if st.button("🎞️ Frame Extraction Only (Phase 17)", key="btn_extract_only"):
                st.session_state.video_ai_result = None
                progress_bar = st.progress(0.0)
                status_text = st.empty()

                def extract_progress_callback(percent: float, text: str):
                    progress_bar.progress(percent)
                    status_text.markdown(f"⏳ **{text}**")

                start_t = time.time()
                ext_res: ExtractionResult = sample_frames(
                    temp_path,
                    sample_interval_seconds=sample_interval,
                    max_frames_to_process=max_frame_limit,
                    progress_callback=extract_progress_callback
                )
                elapsed = time.time() - start_t

                st.session_state.video_extraction_result = ext_res
                st.session_state.extraction_elapsed = elapsed
                status_text.markdown(f"✅ **Frame Extraction Completed in {elapsed:.2f} seconds!**")

# ── Section 4: Render Video AI Results (Phase 18) ────────────────────
if st.session_state.video_ai_result is not None:
    res: VideoAIScanResult = st.session_state.video_ai_result
    stats = res.statistics

    st.markdown("---")
    st.subheader("3. Video AI Analysis Results")

    # Display Statistics Panel
    st.markdown("#### 📊 Processing Statistics")
    scol1, scol2, scol3, scol4, scol5 = st.columns(5)
    scol1.metric("Sampled Frames", f"{stats.get('sampled_frames', 0)} / {stats.get('total_video_frames', 0)}")
    scol2.metric("Faces Detected", f"{stats.get('total_faces_detected', 0)}")
    scol3.metric("KNN Queries", f"{stats.get('knn_queries_performed', 0)}")
    scol4.metric("Potential Matches", f"{stats.get('potential_matches', 0)}")
    scol5.metric("Unique Candidates", f"{stats.get('unique_candidate_cases', 0)}")

    # Handle Status Responses
    if res.status == "NO_REFERENCE_VECTORS":
        st.warning("⚠️ **No Reference Face Vectors**: No registered missing person face vectors exist in MongoDB.")
    elif res.status == "NO_FACES_DETECTED":
        st.info("ℹ️ **No Faces Detected**: No human faces were detected in any sampled frame.")
    elif res.status == "NO_POTENTIAL_MATCH":
        st.info("ℹ️ **No Potential Match**: Human faces were detected, but none passed the configured KNN threshold.")
    elif res.status == "SUCCESS":
        st.success(f"🎉 **{res.message}**")

        st.markdown("---")
        st.subheader("4. Aggregated Potential Candidate Sightings")

        for idx, cand in enumerate(res.unique_candidates):
            st.markdown(f"### Candidate #{idx + 1}: {cand.case_name} (`{cand.case_id}`)")

            ccol_left, ccol_right = st.columns([1, 1])

            with ccol_left:
                st.markdown(f"""
                <div class="glass-card" style="border-left: 4px solid #10b981; padding: 20px;">
                    <span class="badge badge-missing">POTENTIAL MATCH</span>
                    <h3 style="margin-top: 10px; color: #10b981;">{cand.case_name}</h3>
                    <p><b>Case ID:</b> <code>{cand.case_id}</code></p>
                    <p><b>First Seen:</b> <code>{cand.first_seen_timestamp:.2f} s</code> ({int(cand.first_seen_timestamp // 60)}m {int(cand.first_seen_timestamp % 60)}s)</p>
                    <p><b>Last Seen:</b> <code>{cand.last_seen_timestamp:.2f} s</code> ({int(cand.last_seen_timestamp // 60)}m {int(cand.last_seen_timestamp % 60)}s)</p>
                    <p><b>Total Frame Detections:</b> <code>{cand.detection_count}</code></p>
                    <p><b>Best Similarity Score:</b> <b style="color: #10b981; font-size: 18px;">{cand.best_similarity:.2f}%</b></p>
                    <p><b>Best Distance:</b> <code>{cand.best_distance:.4f}</code></p>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"📁 View Case Details for {cand.case_id}", key=f"btn_case_{cand.case_id}"):
                    st.switch_page("pages/cases.py")

            with ccol_right:
                st.markdown("#### 🖼️ Best Representative Frame")
                if cand.representative_frame is not None:
                    st.image(
                        cand.representative_frame,
                        caption=f"Best Representative Frame for {cand.case_name} (Similarity: {cand.best_similarity:.1f}%)",
                        use_container_width=True
                    )
                else:
                    st.info("No representative frame captured.")

            # Render Temporal Segments Breakdown
            if cand.segments:
                with st.expander(f"⏱️ View Temporal Sightings Timeline ({len(cand.segments)} segment(s))"):
                    for seg_i, seg in enumerate(cand.segments):
                        st.write(
                            f"- **Segment #{seg_i + 1}**: From **{seg.start_timestamp:.2f}s** to **{seg.end_timestamp:.2f}s** "
                            f"({seg.detection_count} detections | Peak Similarity: **{seg.best_similarity:.2f}%**)"
                        )

            st.markdown("---")

# ── Section 5: Render Frame Extraction Results (Phase 17) ────────────
if st.session_state.video_extraction_result is not None:
    ext_res: ExtractionResult = st.session_state.video_extraction_result
    st.markdown("---")
    st.subheader("3. Frame Extraction Previews (Phase 17)")

    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Sampled Frames", f"{ext_res.total_frames_sampled}")
    mcol2.metric("Total Video Frames", f"{ext_res.total_video_frames}")
    mcol3.metric("Duration", f"{ext_res.duration_seconds:.2f} s")

    if ext_res.frames:
        ITEMS_PER_PAGE = 12
        total_frames = len(ext_res.frames)
        total_pages = max(1, (total_frames + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        current_page = st.number_input(
            f"Page (1 of {total_pages})",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.page_number,
            key="page_input_p17"
        )
        st.session_state.page_number = current_page

        start_idx = (current_page - 1) * ITEMS_PER_PAGE
        end_idx = min(total_frames, start_idx + ITEMS_PER_PAGE)
        page_frames: list[SampledFrame] = ext_res.frames[start_idx:end_idx]

        cols = st.columns(4)
        for i, sampled in enumerate(page_frames):
            col = cols[i % 4]
            with col:
                st.image(
                    sampled.frame,
                    caption=f"Frame #{sampled.frame_index} | Time: {sampled.timestamp_seconds:.2f}s",
                    use_container_width=True
                )
