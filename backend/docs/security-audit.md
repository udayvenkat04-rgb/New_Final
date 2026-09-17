# Security Audit Report — Missing Person Identification System

**Date:** 14 August 2026  
**Auditor:** Automated Security Engineering Pipeline  
**Scope:** Authentication, Authorization, Input Validation, File Uploads, Biometric Privacy, MongoDB Connections, Secrets Management, Logging, Error Handling, Dependencies, Git Repository, and Public Submission Portal.

---

## Executive Summary

A comprehensive security audit of the Missing Person Identification System was conducted prior to Phase 24 hardening. The system processes sensitive personal data, biometric face embeddings (1,404-dimensional vectors), surveillance video feeds, complainant contact details, and administrative audit trails.

The audit identified **0 Critical**, **0 High**, **4 Medium**, and **3 Low** risk findings. All identified risks have been remediated or mitigated through service-layer authorization guards, strict input validation, filename sanitization, biometric privacy filters, and error message sanitization.

---

## Detailed Findings & Risk Analysis

| ID | Finding | Severity | Location | Risk Description | Recommended Fix | Status |
|---|---|---|---|---|---|---|
| SEC-01 | Potential Path Traversal in Filename Handling | **MEDIUM** | `services/case_service.py`, `services/public_submission_service.py`, `services/video_processing.py` | Malicious filename parameters (e.g. `../../etc/passwd`) could attempt path traversal if not stripped. | Enforce `os.path.basename` and UUID-based filename generation for all saved files. | **RESOLVED** |
| SEC-02 | Resource Exhaustion via Large Video Feeds | **MEDIUM** | `services/video_processing.py` | Oversized or indefinite video files could exhaust CPU/memory/disk during OpenCV frame sampling. | Enforce 100MB file size limit, 600s duration limit, and 500 frame sampling ceiling. | **RESOLVED** |
| SEC-03 | Biometric Data Privacy Exposure Risk | **MEDIUM** | `services/map_service.py`, `models/missing_person.py` | 1,404-D face vectors or complainant phone/email could be accidentally included in public map/lookup endpoints. | Enforce data privacy separation (`PUBLIC_MAP_DATA` vs `ADMIN_MAP_DATA`) and strip embeddings/contacts from public responses. | **RESOLVED** |
| SEC-04 | Raw Exception Stack Trace Information Disclosure | **MEDIUM** | `pages/`, `services/` | Uncaught Python exceptions or PyMongo errors could display raw stack traces or internal filesystem paths in Streamlit UI. | Wrap UI service calls in controlled try/except blocks displaying user-friendly sanitized messages. | **RESOLVED** |
| SEC-05 | Insecure Direct Object Reference (IDOR) on Case Records | **LOW** | `services/case_service.py` | Officers attempting to inspect or edit another officer's private case record by numeric ID. | Enforce `created_by` ownership filtering in `CaseRepository` queries for all Officer-level calls. | **RESOLVED** |
| SEC-06 | Credential Protection in Logging & Repr | **LOW** | `config/settings.py`, `services/` | Logging settings or user objects could inadvertently expose SMTP passwords or DB credentials. | Mask sensitive credentials (`[MASKED]`) in `Settings.__repr__` and logger strings. | **RESOLVED** |
| SEC-07 | Environment Configuration Placeholder Verification | **LOW** | `.env`, `.env.example`, `.gitignore` | Ensure `.env` is ignored by Git and `.env.example` contains safe placeholders only. | Verify `.env` in `.gitignore` and maintain clean `.env.example`. | **RESOLVED** |

---

## Assessment by Security Category

### 1. Authentication & Credentials
- **Password Hashing:** Uses `bcrypt` with auto-generated salts (`utils/security.py`). Read-only support retained for legacy SHA-256 hashes.
- **Login Safety:** Generic error message `"Invalid email or password. Please try again."` prevents username/email enumeration.

### 2. Authorization & RBAC
- **Service-Layer Enforcement:** Permissions are enforced inside services (`CaseLifecycleService`, `PublicSubmissionReviewService`, `MatchReviewService`, `CaseService`), independent of Streamlit UI controls.
- **Role Restrictions:** Admin role required for match review confirmation, public submission approval, case resolution, closure, reopening, and soft deletion. Officers can only view/manage their own cases.

### 3. File Upload & Media Hardening
- **Image Uploads:** Max size 5 MB, allowed extensions (`.jpg`, `.jpeg`, `.png`), Pillow `Image.verify()` readability check.
- **Video Uploads:** Max size 100 MB, allowed extensions (`.mp4`, `.avi`, `.mov`, `.mkv`), max 500 frames sampled, OpenCV decodability validation.
- **Filename Sanitization:** Filenames are never trusted; all uploads are saved under UUID-generated filenames (`uuid.uuid4().hex`).

### 4. Biometric Data Privacy
- **1,404-D Vectors:** Face embeddings are stored securely in MongoDB (`db.face_vectors`) and used exclusively for KNN matching. Vectors are never rendered in HTML, logged, or included in public status responses.

---

## Audit Conclusion

The application demonstrates a strong defense-in-depth architecture. With Phase 24 hardening applied, all service methods enforce strict role authorization, resource limits, path traversal protections, and sanitized output.
