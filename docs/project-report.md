# FINAL ACADEMIC PROJECT REPORT

## MISSING PERSON IDENTIFICATION SYSTEM USING MEDIAPIPE FACE LANDMARKING AND KNN VECTOR MATCHING

---

**Project Title**: Missing Person Identification System  
**System Architecture**: Multi-Tier Web Application (Presentation, Service, Repository, Database, AI, Notification)  
**Primary Technologies**: Python, Streamlit, MongoDB, MediaPipe Tasks, OpenCV, NumPy, scikit-learn, Folium  
**Verification Status**: 464 / 464 Automated Tests Passed | 21/21 Master End-to-End Steps Passed  
**Report Version**: 1.0.0 (Final Academic Report)  
**Date**: August 2026  

---

## TABLE OF CONTENTS

1. [CHAPTER 1: INTRODUCTION](#chapter-1-introduction)
2. [CHAPTER 2: PROBLEM STATEMENT](#chapter-2-problem-statement)
3. [CHAPTER 3: OBJECTIVES](#chapter-3-objectives)
4. [CHAPTER 4: EXISTING SYSTEM](#chapter-4-existing-system)
5. [CHAPTER 5: PROPOSED SYSTEM](#chapter-5-proposed-system)
6. [CHAPTER 6: SYSTEM REQUIREMENTS](#chapter-6-system-requirements)
7. [CHAPTER 7: SYSTEM ARCHITECTURE](#chapter-7-system-architecture)
8. [CHAPTER 8: TECHNOLOGY STACK](#chapter-8-technology-stack)
9. [CHAPTER 9: DATABASE DESIGN](#chapter-9-database-design)
10. [CHAPTER 10: USER ROLES AND PERMISSIONS](#chapter-10-user-roles-and-permissions)
11. [CHAPTER 11: CASE MANAGEMENT & LIFECYCLE](#chapter-11-case-management--lifecycle)
12. [CHAPTER 12: FACE DETECTION PIPELINE](#chapter-12-face-detection-pipeline)
13. [CHAPTER 13: 1,404-DIMENSIONAL FACE EMBEDDING](#chapter-13-1404-dimensional-face-embedding)
14. [CHAPTER 14: KNN CANDIDATE MATCHING ENGINE](#chapter-14-knn-candidate-matching-engine)
15. [CHAPTER 15: VIDEO SIGHTING PROCESSING](#chapter-15-video-sighting-processing)
16. [CHAPTER 16: HUMAN MATCH REVIEW WORKFLOW](#chapter-16-human-match-review-workflow)
17. [CHAPTER 17: EMAIL NOTIFICATION SYSTEM](#chapter-17-email-notification-system)
18. [CHAPTER 18: INDIA CASE DENSITY MAP](#chapter-18-india-case-density-map)
19. [CHAPTER 19: PUBLIC SUBMISSION PORTAL](#chapter-19-public-submission-portal)
20. [CHAPTER 20: SECURITY HARDENING AND PRIVACY PROTECTION](#chapter-20-security-hardening-and-privacy-protection)
21. [CHAPTER 21: TESTING AND QUALITY ASSURANCE](#chapter-21-testing-and-quality-assurance)
22. [CHAPTER 22: SYSTEM RESULTS AND DEMONSTRATED CAPABILITIES](#chapter-22-system-results-and-demonstrated-capabilities)
23. [CHAPTER 23: ADVANTAGES OF THE PROPOSED SYSTEM](#chapter-23-advantages-of-the-proposed-system)
24. [CHAPTER 24: SYSTEM LIMITATIONS](#chapter-24-system-limitations)
25. [CHAPTER 25: FUTURE SCOPE](#chapter-25-future-scope)
26. [CHAPTER 26: CONCLUSION](#chapter-26-conclusion)
27. [REFERENCES](#references)
28. [APPENDIX](#appendix)

---

## CHAPTER 1: INTRODUCTION

### 1.1 Background
The disappearance of an individual represents a critical crisis for families, communities, and law enforcement agencies. Rapid case registration, centralized data sharing, and intelligent biometric candidate retrieval are paramount to locating missing individuals during early investigation windows. Traditional manual inspection of bulletin photographs across fragmented databases is time-consuming, prone to human fatigue, and inefficient when processing large volumes of public CCTV video recordings.

### 1.2 Overview of the System
The **Missing Person Identification System** is a secure, multi-role web platform designed to streamline missing-person case registration, automate face landmark extraction, compute 1,404-dimensional facial embeddings, perform fast K-Nearest Neighbors (KNN) candidate search, process video surveillance sightings, send automated email alerts upon identity confirmation, and visualize case geographic density across India.

### 1.3 Need for the System
- **Centralized Case Repository**: Eliminates fragmented paper and local desktop records across law enforcement jurisdictions.
- **Automated Candidate Retrieval**: Accelerates identity candidate discovery from reference databases containing hundreds of missing-person records.
- **Surveillance Video Analysis**: Enables automated frame extraction and face detection from public video uploads.
- **Human-in-the-Loop Safeguards**: Ensures AI predictions are strictly candidate recommendations that require explicit human verification by authorized Administrators.

### 1.4 Motivation
Combining modern computer vision (Google MediaPipe Face Landmarker), vector similarity search (scikit-learn KNN), robust database management (MongoDB local instance), and web user interface frameworks (Streamlit) provides an accessible, reproducible tool for law enforcement officers and public citizens.

### 1.5 Project Scope
The scope encompasses full case lifecycle management (`SUBMITTED`, `PENDING_VERIFICATION`, `VERIFIED`, `ACTIVE_INVESTIGATION`, `POTENTIAL_MATCH`, `UNDER_MATCH_REVIEW`, `MATCH_CONFIRMED`, `MATCH_REJECTED`, `RESOLVED`, `CLOSED`, `REOPENED`), public reporting with reference number tracking, role-based access control (Admin, Officer, Public), audit trail logging, security hardening, and geographic density mapping.

---

## CHAPTER 2: PROBLEM STATEMENT

Traditional missing-person identification and investigation workflows face significant operational challenges:

1. **Manual Visual Inspection**: Investigators must manually compare public sighting photos against physical paper files or desktop folders, leading to delays and missed matches.
2. **High-Volume Surveillance Video**: Analyzing hours of public CCTV video footage for potential sightings manually requires immense human effort.
3. **Lack of Centralized Tracking**: Fragmented systems prevent cross-jurisdictional visibility when a missing person travels across city or state lines.
4. **Uncontrolled Data Access & Privacy Concerns**: Storing sensitive missing-person photographs and complainant contact details in insecure formats exposes biometric and private personal data to unauthorized access.
5. **Delayed Stakeholder Notifications**: Notifying complainants and assigned investigating officers of potential matches via traditional manual channels delays verification.

---

## CHAPTER 3: OBJECTIVES

The primary objective is to design, implement, test, and document a secure, production-ready Missing Person Identification System fulfilling the following technical and operational goals:

1. **Automatic Face Detection**: Detect human faces in uploaded photographs and video frames using Google MediaPipe Face Landmarker.
2. **1,404-Dimensional Vector Generation**: Extract 468 3D facial landmarks (X, Y, Z coordinates) and compute scale- and translation-invariant normalized face embeddings.
3. **KNN Candidate Matching Engine**: Implement a K-Nearest Neighbors engine using Euclidean distance to retrieve top-k candidate matches from stored reference vectors in $< 20\text{ ms}$.
4. **Video Sightings Analysis**: Sample video frames at configurable intervals (1.0s), enforce safety caps (500 frames), extract faces, and aggregate candidate matches.
5. **Role-Based Access Control (RBAC)**: Enforce strict role isolation across `ADMIN`, `OFFICER`, and `PUBLIC` roles with IDOR protection for Officer-assigned cases.
6. **Human-in-the-Loop Review**: Provide a dedicated Admin match review UI with side-by-side face comparisons, similarity gauges, and explicit warning banners (*"AI-generated candidate — human review required"*).
7. **Automated Notification Dispatch**: Trigger SMTP email alerts to registered complainants upon Admin match confirmation with duplicate email prevention.
8. **Geographic Density Visualization**: Render interactive Folium density maps aggregating active missing-person bulletins by city and state across India.
9. **Public Submission Portal**: Provide a public-facing submission interface with safe reference numbers (`MP-SUB-2026-XXXX`) and sanitized status lookups.
10. **Immutable Audit Trail**: Record complete chronological case event histories for legal and operational accountability.
11. **Security & Privacy Hardening**: Implement path traversal protection, file size limits (5MB image / 100MB video), input validation, masked logging, and biometric data isolation.

---

## CHAPTER 4: EXISTING SYSTEM

Historically, missing-person identification relies on manual processes:

- **Paper Bulletins & Spreadsheets**: Case records are logged in physical police station registers or independent local spreadsheets.
- **Manual Photographic Comparison**: Officers visually inspect physical posters or digital image folders to find matching individuals.
- **Stationary Investigation**: Sighting information received from the public is recorded manually without automated cross-referencing against active case repositories.

### Limitations of the Existing System
- High human error and fatigue during visual comparison.
- Inability to search video footage at scale.
- No automated similarity ranking or biometric vector indexing.
- Lack of centralized audit trails and role-restricted data visibility.

---

## CHAPTER 5: PROPOSED SYSTEM

The proposed **Missing Person Identification System** replaces manual bottlenecks with an integrated software platform:

```
                  ┌─────────────────────────────────────────┐
                  │       Streamlit Application Shell       │
                  └────────────────────┬────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│   Public Portal  │          │  Officer Portal  │          │   Admin Portal   │
│ - Report Filing  │          │ - Assigned Cases │          │ - Full Control   │
│ - Public Lookup  │          │ - Case Updates   │          │ - Match Review   │
│ - Case Density   │          │ - Photo Uploads  │          │ - Approval Queue │
└────────┬─────────┘          └────────┬─────────┘          └────────┬─────────┘
         │                             │                             │
         └─────────────────────────────┼─────────────────────────────┘
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │            Service Layer                │
                  │ - CaseService                           │
                  │ - FaceEmbeddingService                  │
                  │ - KNNFaceMatchingEngine                 │
                  │ - MatchReviewService                    │
                  │ - PublicSubmissionService               │
                  │ - NotificationService                   │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │         Local MongoDB Instance          │
                  │   (missing_person_db - 9 Collections)   │
                  └─────────────────────────────────────────┘
```

---

## CHAPTER 6: SYSTEM REQUIREMENTS

### 6.1 Hardware Requirements
- **Processor**: Intel Core i5 / AMD Ryzen 5 or higher (Dual-Core 2.0 GHz minimum).
- **RAM**: 8 GB RAM minimum (16 GB recommended for high-frame video processing).
- **Disk Storage**: 500 MB free storage for application code and MediaPipe `.task` model file; additional storage for local MongoDB collections and uploaded media uploads directory.
- **Display**: Minimum $1366 \times 768$ resolution.

### 6.2 Software Requirements
- **Operating System**: Windows 10/11, Ubuntu Linux 20.04/22.04 LTS, or macOS 12+.
- **Runtime Environment**: Python 3.10+ (Python 3.11/3.13 verified).
- **Database**: Local MongoDB Server v5.0+ running on `mongodb://localhost:27017`.
- **Core Libraries**:
  - `streamlit>=1.30.0` (Web UI presentation framework)
  - `pymongo>=4.6.0` (MongoDB database driver)
  - `mediapipe>=0.10.0` (Face Landmarker model API)
  - `opencv-python>=4.8.0` (Image & video frame decoding)
  - `numpy>=1.24.0` (High-performance array operations)
  - `scikit-learn>=1.3.0` (NearestNeighbors KNN vector engine)
  - `folium>=0.15.0` & `streamlit-folium>=0.17.0` (Interactive GIS map rendering)
  - `pillow>=10.0.0` (Image validation and format decoding)
  - `bcrypt>=4.0.0` (Secure password hashing)
  - `python-dotenv>=1.0.0` (Environment variable management)
  - `pytest>=7.0.0` (Automated testing framework)

### 6.3 Functional Requirements
- Secure authentication (`bcrypt`) and RBAC authorization (`ADMIN`, `OFFICER`, `PUBLIC`).
- Official case registration with unique case number generation (`MP-2026-XXXXX`).
- Public report submission (`PENDING_VERIFICATION`) with reference tracking (`MP-SUB-2026-XXXX`).
- Automatic face landmark detection and 1,404-D vector extraction.
- KNN Euclidean vector matching returning candidate similarity rankings.
- Video frame extraction and multi-face candidate aggregation.
- Human-in-the-loop Admin review workflow for candidate confirmation or rejection.
- Automated email notification dispatch via SMTP upon match confirmation.
- Interactive India case density heatmap and marker visualization.
- Complete chronological case audit trail tracking.

### 6.4 Non-Functional Requirements
- **Performance**: Sub-second query response ($< 20\text{ ms}$ for KNN search across 500 vectors).
- **Security**: IDOR protection, path traversal sequence blocks, 5MB/100MB media size limits, masked settings logging.
- **Privacy**: Biometric vector isolation and public complainant detail sanitization.
- **Reliability**: Graceful error handling for missing models, unreadable images, and database disconnects.

---

## CHAPTER 7: SYSTEM ARCHITECTURE

The application enforces a clean **Layered Architecture**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       1. PRESENTATION LAYER                             │
│  app.py | pages/login.py | admin_dashboard.py | officer_dashboard.py    │
│  case_management.py | matching.py | match_review.py | public_portal.py    │
│  ui/ (theme.py, styles.py, components.py)                               │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                         2. SERVICE LAYER                                │
│  AuthService | CaseService | CaseLifecycleService                       │
│  FaceDetectionService | FaceEmbeddingService | KNNFaceMatchingEngine     │
│  MatchReviewService | NotificationService | PublicSubmissionService    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                        3. REPOSITORY LAYER                              │
│  UserRepository | CaseRepository | FaceRepository | MatchReviewRepo     │
│  PublicSubmissionRepo | NotificationRepo | CaseEventRepo                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                         4. DATABASE LAYER                               │
│  Local MongoDB Server (missing_person_db) — 9 Collections               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## CHAPTER 8: TECHNOLOGY STACK

- **Python (v3.10+)**: Core programming language powering services, data processing, and business logic.
- **Streamlit**: Production web presentation framework providing responsive layouts, form handling, and session state management.
- **MongoDB & PyMongo**: Local NoSQL document store delivering flexible document schemas for cases, embeddings, audit logs, and submission records.
- **Google MediaPipe Tasks (Face Landmarker)**: Deep machine learning pipeline estimating 468 3D facial landmark coordinates ($X, Y, Z$) from single images or video frames.
- **OpenCV (`opencv-python`)**: Industrial computer vision library for image loading, color space conversions ($BGR \to RGB$), and video frame sampling.
- **NumPy**: Vectorized linear algebra operations for mean-centering, maximum radius scaling, Euclidean norm calculation, and L2 normalization.
- **scikit-learn (`NearestNeighbors`)**: High-performance K-Nearest Neighbors vector indexing engine for Euclidean distance searches.
- **Folium & streamlit-folium**: GIS mapping framework rendering interactive India state/city case density maps.
- **Bcrypt**: Cryptographic password hashing library providing salted, slow hash verification for user authentication.

---

## CHAPTER 9: DATABASE DESIGN

The system uses **MongoDB** (`missing_person_db`) containing 9 dedicated collections:

```
                        ┌──────────────────┐
                        │      users       │
                        └────────┬─────────┘
                                 │
                         created_by / reporter
                                 │
                        ┌────────▼─────────┐
                        │      cases       │
                        └────────┬─────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌──────────────┐        ┌──────────────────┐    ┌──────────────────┐
│ face_vectors │        │  match_reviews   │    │   case_events    │
└──────────────┘        └────────┬─────────┘    └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  notifications   │
                        └──────────────────┘

┌─────────────────────┐                 ┌───────────────────────────┐
│ public_submissions  │ ── approved ──► │  public_submission_audits │
└─────────────────────┘                 └───────────────────────────┘
```

### 9.1 Collection Schemas

1. **`users`**: User account credentials and role assignments (`username`, `email`, `password_hash`, `role`, `is_active`, `created_at`).
2. **`cases`**: Official missing-person records (`case_number`, `name`, `age`, `gender`, `last_seen_location`, `last_seen_city`, `last_seen_state`, `last_seen_date`, `status`, `reporter_name`, `contact_email`, `contact_phone`, `photo_path`, `created_by`, `assigned_officer_id`).
3. **`public_submissions`**: Public missing-person reports (`submission_reference`, `full_name`, `age`, `gender`, `last_seen_city`, `last_seen_state`, `complainant_name`, `contact_email`, `contact_phone`, `status`, `photo_path`).
4. **`face_vectors`**: Biometric facial landmark embeddings (`case_id`, `vector` [1,404 floats], `source_image_path`, `landmark_count`, `vector_dim`, `created_at`).
5. **`match_reviews`**: Human match review records (`case_id`, `query_image_path`, `candidate_case_id`, `similarity_score`, `euclidean_distance`, `status`, `reviewed_by`, `reviewed_at`, `notes`).
6. **`notifications`**: Email notification logs (`case_id`, `recipient_email`, `notification_type`, `status`, `attempt_count`, `sent_at`, `error_message`).
7. **`case_events`**: Immutable case audit event timeline (`case_id`, `action`, `previous_status`, `new_status`, `performed_by`, `actor_role`, `notes`, `timestamp`).
8. **`sightings`**: Publicly reported sighting locations (`case_id`, `location_description`, `city`, `state`, `sighting_date`, `status`, `photo_path`).
9. **`public_submission_audits`**: Audit records for public report approvals/rejections (`submission_id`, `submission_reference`, `action`, `actor_username`, `previous_status`, `new_status`, `approved_case_id`, `timestamp`).

---

## CHAPTER 10: USER ROLES AND PERMISSIONS

The platform enforces a Role-Based Access Control (RBAC) matrix across `ADMIN`, `OFFICER`, and `PUBLIC` users:

| System Feature / Operation | Admin Role | Officer Role | Public User |
|---|---|---|---|
| Public Report Filing | N/A | N/A | ✅ Allowed |
| Public Report Status Lookup | ✅ Allowed | ✅ Allowed | ✅ Sanitized Only |
| Official Case Registration | ✅ Allowed | ✅ Allowed | ❌ Denied |
| View All Official Cases | ✅ Allowed | ❌ Restricted (Own Cases Only) | ❌ Denied |
| Upload Case Photo / Video | ✅ Allowed | ✅ Allowed | ❌ Denied |
| Trigger AI Face Matching | ✅ Allowed | ❌ Denied | ❌ Denied |
| Access Match Review Queue | ✅ Allowed | ❌ Denied | ❌ Denied |
| Confirm / Reject AI Match | ✅ Allowed | ❌ Denied | ❌ Denied |
| Approve Public Submission | ✅ Allowed | ❌ Denied | ❌ Denied |
| Update Case Lifecycle Status | ✅ Allowed | ✅ Limited (Assigned Cases) | ❌ Denied |
| Trigger Email Notifications | ✅ Automatic / Manual | ❌ Denied | ❌ Denied |
| View Full Audit Log Timeline | ✅ Allowed | ✅ Assigned Case Only | ❌ Denied |

---

## CHAPTER 11: CASE MANAGEMENT & LIFECYCLE

The system manages missing-person bulletins using a formal 11-state machine:

```
[ Public Submission ] ──► PENDING_VERIFICATION ──► REJECTED
                                 │
                             (Approve)
                                 ▼
                     ACTIVE_INVESTIGATION ◄──────┐
                                 │               │
                            (AI Match)           │ (Reject / Reopen)
                                 ▼               │
                          POTENTIAL_MATCH        │
                                 │               │
                             (Review)            │
                                 ▼               │
                        UNDER_MATCH_REVIEW ──────┘
                                 │
                             (Confirm)
                                 ▼
                          MATCH_CONFIRMED
                                 │
                            (Resolving)
                                 ▼
                              RESOLVED
                                 │
                             (Closing)
                                 ▼
                              CLOSED
                                 │
                             (Reopen)
                                 ▼
                              REOPENED ──► Resumes ACTIVE_INVESTIGATION
```

---

## CHAPTER 12: FACE DETECTION PIPELINE

### 12.1 Image Loading & Preprocessing
Input images are ingested via OpenCV, validated for size ($\le 5\text{ MB}$) and extension (`.jpg`, `.jpeg`, `.png`), and converted from BGR to RGB color space.

### 12.2 MediaPipe Face Landmarker
The MediaPipe Face Landmarker model (`data/models/face_landmarker.task`) processes the RGB image array, detecting face bounding boxes and predicting 468 3D landmark points per detected face.

```
Input Image (RGB) ──► MediaPipe Landmarker ──► Bounding Box + 468 3D Landmarks (X, Y, Z)
```

---

## CHAPTER 13: 1,404-DIMENSIONAL FACE EMBEDDING

### 13.1 Representation Architecture
Facial landmarks extracted by MediaPipe consist of 468 points, each having $X, Y, Z$ spatial coordinates:
$$\text{Total Dimension} = 468 \times 3 = 1,404\text{ floating-point values}$$

### 13.2 Normalization Pipeline
To achieve translation and scale invariance across varying camera angles and distance from lens:
1. **Spatial Centering (Translation Invariance)**:
   Subtract the 3D mean centroid $(\bar{x}, \bar{y}, \bar{z})$ from all 468 landmark coordinates:
   $$x'_i = x_i - \bar{x}, \quad y'_i = y_i - \bar{y}, \quad z'_i = z_i - \bar{z}$$
2. **Maximum Radius Scaling (Scale Invariance)**:
   Divide all coordinates by the maximum Euclidean distance $R_{\max}$ from the centroid to any landmark:
   $$R_{\max} = \max_i \sqrt{(x'_i)^2 + (y'_i)^2 + (z'_i)^2}$$
   $$x''_i = \frac{x'_i}{R_{\max}}, \quad y''_i = \frac{y'_i}{R_{\max}}, \quad z''_i = \frac{z'_i}{R_{\max}}$$
3. **L2 Unit Sphere Normalization**:
   Rescale the concatenated 1,404-D vector $\mathbf{v}$ to unit length:
   $$\mathbf{v}_{\text{norm}} = \frac{\mathbf{v}}{\|\mathbf{v}\|_2}$$

---

## CHAPTER 14: KNN CANDIDATE MATCHING ENGINE

### 14.1 Vector Matching Algorithm
The matching engine uses scikit-learn's `NearestNeighbors` configured with Euclidean distance ($L_2$ norm):
$$d(\mathbf{u}, \mathbf{v}) = \sqrt{\sum_{k=1}^{1404} (u_k - v_k)^2}$$

### 14.2 Similarity Score Conversion
Euclidean distance $d \ge 0$ on normalized 3D landmarks is converted into a $0.0\% - 100.0\%$ similarity ranking score:
$$\text{Similarity Score} = \max\left(0.0, 1.0 - \frac{d}{2.0}\right) \times 100.0\%$$

### 14.3 Human Verification Principle
> **CRITICAL RULE**: KNN distance matching provides candidate similarity ranking ONLY. Automated similarity scores do NOT prove identity. Final match confirmation requires authorized Admin human review.

---

## CHAPTER 15: VIDEO SIGHTING PROCESSING

1. **Video Ingestion & Validation**: Video files are validated for extension (`.mp4`, `.avi`, `.mov`, `.mkv`) and file size ($\le 100\text{ MB}$).
2. **Frame Extraction**: OpenCV samples frames at 1.0-second intervals up to a maximum safety cap of 500 frames.
3. **Face Detection & Vector Extraction**: MediaPipe extracts 1,404-D vectors for all faces detected across sampled frames.
4. **Candidate Aggregation**: Matches are aggregated across frames to identify unique missing-person candidates, filtering out duplicate hits.

---

## CHAPTER 16: HUMAN MATCH REVIEW WORKFLOW

When KNN identifies a candidate with similarity exceeding threshold ($0.60$), the system transitions the case to `POTENTIAL_MATCH`. An authorized Admin opens the Match Review interface:

1. **Prominent AI Warning Banner**: Displays *"AI-generated candidate — human review required"*.
2. **Side-by-Side Visual Comparison**: Displays reference photo vs query photo.
3. **Similarity Gauge**: Displays calculated similarity percentage.
4. **Confirmation Modal Step**: Admin clicks "Confirm Match" or "Reject Match", triggering a multi-step confirmation dialog to prevent accidental clicks.

---

## CHAPTER 17: EMAIL NOTIFICATION SYSTEM

1. **Trigger**: Match confirmation by an Admin triggers `NotificationService`.
2. **Recipient Retrieval**: Service fetches registered complainant email from `cases` record.
3. **Duplicate Prevention**: Service checks `notifications` collection to ensure duplicate emails are not sent for the same review event.
4. **SMTP Dispatch**: Email is formatted using a responsive HTML template and dispatched via SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`).
5. **Dev-Mode Fallback**: If `EMAIL_ENABLED=false`, notification logs are safely recorded in MongoDB without throwing connection errors.

---

## CHAPTER 18: INDIA CASE DENSITY MAP

- **GIS Integration**: Uses Folium and `streamlit-folium` to render an interactive map of India centered at Delhi ($28.6139^\circ\text{ N}, 77.2090^\circ\text{ E}$).
- **Spatial Aggregation**: Aggregates active missing-person bulletins by city and state.
- **Privacy Sanitization**: Map markers display city/state counts only, concealing private victim contact details.

---

## CHAPTER 19: PUBLIC SUBMISSION PORTAL

- **Public Interface**: Mobile-friendly submission page accessible without login.
- **Sectioned Reporting Form**: Person Information -> Last Seen Information -> Complainant Contact Information -> Photo Upload -> Consent Checkbox.
- **Safe Reference Tracking**: Returns an official tracking reference (`MP-SUB-2026-XXXX`).
- **Public Lookup**: Allows citizens to check report status (`PENDING_VERIFICATION`, `APPROVED`, `REJECTED`) with complainant phone and email strictly masked.

---

## CHAPTER 20: SECURITY HARDENING AND PRIVACY PROTECTION

- **Path Traversal Guards**: `utils/validators.py` rejects filenames containing `../` or `..\`. Media files are stored under random UUID names (`uuid.uuid4().hex`).
- **Resource Limits**: 5MB max image limit, 100MB max video limit, 500 max frame cap.
- **Service-Layer RBAC**: Direct service method invocations enforce role checks (`PermissionError` on unauthorized calls).
- **IDOR Protection**: Officers can only access their own registered cases.
- **Biometric & Complainant Privacy**: Face vectors are restricted to `db.face_vectors`. Public lookups strip victim names, complainant phone, email, and private notes.
- **Masked Logging**: `Settings.__repr__` masks SMTP passwords (`[MASKED]`). Raw face vectors are never printed to loggers.

---

## CHAPTER 21: TESTING AND QUALITY ASSURANCE

### 21.1 Test Suite Overview
The project contains 464 automated unit, integration, AI pipeline, security, and performance tests across 23 test files:

```
tests/
├── unit/test_unit_phase25.py          # Models, validators, hashing
├── integration/test_integration_...  # Repositories, services, RBAC
├── ai/test_ai_phase25.py              # MediaPipe landmarker, 1404-D vector validation
├── e2e/test_master_e2e_phase25.py     # 21-step Master E2E scenario
├── performance/test_performance_...   # KNN search performance benchmarks
├── test_security_phase24.py           # 30 security control scenarios
└── ... (17 additional test modules)
```

### 21.2 Test Execution Results
- **Automated Tests (`pytest`)**: **464 / 464 PASSED** ($100\%$ pass rate).
- **Master Verification (`_verify_phase25.py`)**: **21 / 21 STEPS PASSED**.

---

## CHAPTER 22: SYSTEM RESULTS AND DEMONSTRATED CAPABILITIES

- **Authentication & Authorization**: Multi-role login and permission enforcement verified.
- **Case Lifecycle Management**: Complete progression across all 11 lifecycle statuses verified.
- **AI Biometric Embedding**: 1,404-D face vector generation and L2 normalization verified.
- **KNN Candidate Matching**: Fast similarity search ($< 20\text{ ms}$) verified across dataset sizes.
- **Video Sighting Analysis**: Automated video frame extraction and candidate aggregation verified.
- **Human Match Review**: Side-by-side comparison and modal match confirmation verified.
- **Email Notifications**: Responsive HTML email alert generation and duplicate prevention verified.
- **Map Visualization**: Spatial aggregation and density map rendering verified.

---

## CHAPTER 23: ADVANTAGES OF THE PROPOSED SYSTEM

1. **Centralized Digital Repository**: Eliminates lost paper records and fragmented local spreadsheets.
2. **Automated Biometric Retrieval**: Reduces manual search time from hours to milliseconds.
3. **Video Surveillance Analysis**: Processes CCTV video sightings automatically.
4. **Human-in-the-Loop Safety**: Prevents automated false positive identity misattributions.
5. **Privacy Protection**: Isolates biometric vectors and sanitizes public lookups.
6. **Audit Accountability**: Tracks every administrative action in an immutable timeline.

---

## CHAPTER 24: SYSTEM LIMITATIONS

1. **Lighting & Pose Sensitivity**: Extreme facial pose angles ($> 45^\circ$) or pitch-black lighting degrade MediaPipe landmark accuracy.
2. **Facial Occlusion**: Heavy face masks, sunglasses, or object obstructions reduce landmark detection quality.
3. **Computational Resource Limits**: Processing high-resolution, high-framerate videos requires moderate CPU/GPU resources.
4. **Candidate Retrieval Scope**: KNN provides candidate similarity rankings only; identity confirmation strictly requires human review.

---

## CHAPTER 25: FUTURE SCOPE

1. **Deep Learning Face Embeddings**: Integrating deep neural network embeddings (e.g., ArcFace / Facenet) for ultra-high accuracy under severe lighting conditions.
2. **Cloud Vector Databases**: Migration to scalable cloud vector databases (e.g., Milvus, Qdrant, Pinecone) for multi-million vector search scaling.
3. **Distributed Video Processing**: Asynchronous worker queues (Celery / Redis) for parallel background video processing.
4. **Mobile Application**: Native Android/iOS mobile application for field officers.
5. **Multilingual Public Portal**: Multi-language support (Hindi, Regional Indian Languages) for broader public accessibility.

---

## CHAPTER 26: CONCLUSION

The **Missing Person Identification System** successfully demonstrates a modern, secure, and production-ready platform for law enforcement and public missing-person search. By combining Google MediaPipe 3D face landmarking, 1,404-dimensional vector embedding, scikit-learn KNN candidate search, OpenCV video frame extraction, Folium map visualization, and strict human-in-the-loop Admin match verification, the system resolves key inefficiencies of traditional manual searches while protecting biometric privacy and ensuring complete operational accountability.

---

## REFERENCES

1. Google MediaPipe Developers. *MediaPipe Face Landmarker Task Guide*. https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
2. OpenCV Development Team. *OpenCV Reference Manual & Video Processing API*. https://docs.opencv.org/
3. scikit-learn Developers. *NearestNeighbors Vector Search Documentation*. https://scikit-learn.org/stable/modules/neighbors.html
4. MongoDB Inc. *MongoDB Server Manual & Indexing Guide*. https://www.mongodb.com/docs/manual/
5. Streamlit Inc. *Streamlit Documentation & Session State Architecture*. https://docs.streamlit.io/
6. Folium Developers. *Folium Python GIS Visualization Library*. https://python-visualization.github.io/folium/
7. NumPy Developers. *NumPy Linear Algebra & Vector Operations Guide*. https://numpy.org/doc/

---

## APPENDIX

### A. Project Directory Structure
```
New_Final/
├── app.py
├── pages/
│   ├── login.py
│   ├── admin_dashboard.py
│   ├── officer_dashboard.py
│   ├── case_management.py
│   ├── cases.py
│   ├── matching.py
│   ├── admin_face_matching.py
│   ├── match_review.py
│   ├── video_sightings.py
│   ├── admin_public_submissions.py
│   ├── public_portal.py
│   ├── map.py
│   └── admin_map.py
├── ui/
│   ├── theme.py
│   ├── styles.py
│   └── components.py
├── services/
├── repositories/
├── models/
├── config/
├── utils/
├── tests/
└── docs/
```

### B. Environment Configuration (.env.example)
```ini
DATABASE_URL=mongodb://localhost:27017
DATABASE_NAME=missing_person_db
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
MAX_IMAGE_SIZE_MB=5
MAX_VIDEO_SIZE_MB=100
MAX_VIDEO_FRAMES_TO_PROCESS=500
MEDIAPIPE_MODEL_PATH=data/models/face_landmarker.task
```

---

*End of Academic Project Report.*
