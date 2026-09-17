# Bug Report & Quality Defect Tracking Log — Phase 25

**System:** Missing Person Identification & Verification System  
**Document Version:** 1.0  
**Date:** August 2026  

---

## 1. Summary of Bug Defect Status

During Phase 24 and Phase 25 testing, 3 quality bugs were identified, tracked, and remediated. No Critical or High severity open defects remain in the codebase.

---

## 2. Tracked Defect Register

### BUG-001: Missing Path Traversal Guard on Public Photo Uploads
- **Severity:** MEDIUM  
- **Module:** Public Submission Service (`services/public_submission_service.py`)  
- **Steps to Reproduce:** Submit a photo with filename `../../malicious_file.png`.  
- **Expected Result:** Filename sanitized securely to random UUID without directory traversal characters.  
- **Actual Result:** Original extension parsed without stripping leading path separators.  
- **Root Cause:** Direct call to `os.path.splitext(filename)` without calling `os.path.basename`.  
- **Fix Applied:** Wrapped filename parameter in `os.path.basename(str(filename))` and generated storage filename as `public_sub_{uuid.uuid4().hex}{ext}`.  
- **Status:** **RESOLVED** (Verified in `test_malicious_filename_sanitization` & `_verify_phase24.py`).

---

### BUG-002: Officer Authorization Restriction Check in End-to-End Test
- **Severity:** MEDIUM  
- **Module:** Case Lifecycle Service (`services/case_lifecycle_service.py` & `_verify_phase23.py`)  
- **Steps to Reproduce:** Call `transition_case_status(case_id, STATE_MATCH_CONFIRMED, user=officer_user)` when case is in `ACTIVE_INVESTIGATION`.  
- **Expected Result:** Role authorization check raises `PermissionError`.  
- **Actual Result:** Service returned transition state error (`Invalid transition`) before reaching the role check because `ACTIVE_INVESTIGATION` -> `MATCH_CONFIRMED` is not in `TRANSITION_MATRIX`.  
- **Root Cause:** Transition state order in verification script called state transition from invalid initial state.  
- **Fix Applied:** Ensured case is in valid transition initial state (`UNDER_MATCH_REVIEW` / `RESOLVED`) before asserting role authorization guard. Service correctly raised `PermissionError: Role 'OFFICER' is not authorized...`.  
- **Status:** **RESOLVED** (Verified in `_verify_phase23.py` & `test_officer_authorization_restriction`).

---

### BUG-003: Public Submission Form Validation Complainant Name Length Bounds
- **Severity:** LOW  
- **Module:** Public Submission Validation (`services/public_submission_service.py`)  
- **Steps to Reproduce:** Pass 1-character string (e.g. `"C"`) as `complainant_name` in synthetic unit test payload.  
- **Expected Result:** Image file size or consent validation error produced.  
- **Actual Result:** Validation stopped early with `INVALID_COMPLAINANT_NAME: Complainant name is required` because minimum length requirement is 2 characters.  
- **Root Cause:** Synthetic test payload passed single-character string.  
- **Fix Applied:** Updated test payload to pass realistic complainant name (`"Complainant Test Person"`).  
- **Status:** **RESOLVED** (Verified in `tests/test_security_phase24.py`).

---

## 3. Defect Metrics Summary

| Severity | Total Discovered | Total Resolved | Open Defect Count |
|---|---|---|---|
| **CRITICAL** | 0 | 0 | **0** |
| **HIGH** | 0 | 0 | **0** |
| **MEDIUM** | 2 | 2 | **0** |
| **LOW** | 1 | 1 | **0** |
| **TOTAL** | **3** | **3** | **0** |
