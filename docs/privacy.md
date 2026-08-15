# Privacy Policy & Data Protection Overview — Missing Person Identification System

**System Name:** Missing Person Identification & Verification System  
**Document Version:** 1.0  
**Effective Date:** August 2026  

---

## 1. Overview & Purpose

The Missing Person Identification System handles sensitive personal data, photographs, biometric face embeddings, surveillance video feeds, and complainant contact details to assist law enforcement officers and administrators in identifying missing persons.

This document outlines data collection practices, access controls, biometric vector protections, retention rules, and public privacy guarantees implemented across the platform.

---

## 2. Categories of Data Processed

| Data Category | Data Elements | Classification | Access Level |
|---|---|---|---|
| **Missing Person Details** | Full Name, Age, Gender, Height, Identifying Marks, Description | Sensitive Personal Data | Public (basic overview), Officer (full bulletin), Admin (full bulletin) |
| **Last Seen Information** | Date, Time, City, State, Location Description, Coordinates | Location Data | Public (aggregated map data only), Officer, Admin |
| **Complainant Contact Info** | Reporter Name, Relationship, Email Address, Phone Number | Confidential Personal Data | Admin & Officer Only (Never exposed publicly) |
| **Biometric Data** | 1,404-Dimensional MediaPipe Face Vectors | Sensitive Biometric Data | System / KNN Engine Only (Never displayed in UI/API) |
| **Media Assets** | Missing Person Photographs, Uploaded Video Feeds | Sensitive Media Assets | Admin, Officer, System Processing |
| **Audit & Event Logs** | Event Type, Actor Username, Role, Timestamp, Action Notes | System Audit Data | Admin Only |

---

## 3. Biometric Data Protection (Face Vectors)

1. **Storage & Purpose:** 1,404-dimensional facial landmark vectors are generated via MediaPipe Face Landmarker and stored in MongoDB (`db.face_vectors`). Vectors are used exclusively for k-Nearest Neighbors (KNN) biometric similarity calculation.
2. **Non-Exposure Guarantee:** Face vectors are strictly excluded from Streamlit user interfaces, public status lookups, REST/map responses, log outputs, and email notifications.
3. **No Automated Identification:** AI KNN similarity match candidates (`POTENTIAL_MATCH`) NEVER automatically update official case status or confirm identity. Identity confirmation is strictly restricted to an authorized human Administrator (`MATCH_CONFIRMED`).

---

## 4. Public Portal Privacy Protections

1. **Unauthenticated Portal (`/public_portal`)**: Citizens can file missing person reports without logging in.
2. **Pending Verification Status**: Public reports enter `PENDING_VERIFICATION` in `db.public_submissions` and do NOT appear in public missing person directories until reviewed and approved by an authorized Admin.
3. **Sanitized Status Lookups**: Citizens querying their report status by reference code (`MP-SUB-2026-XXXXXX`) receive strictly sanitized status responses containing ONLY the reference code, status string, submission date, and a general status message. Complainant emails, phone numbers, private review notes, victim descriptions, and internal DB IDs are completely withheld.

---

## 5. Data Retention & Cleanup Policies

- **Temporary Processing Media:** Temporary video uploads and extracted frame files in `data/videos/` are automatically deleted upon processing completion.
- **Audit Retention:** Case lifecycle events (`db.case_events`), public submission audit trails (`db.public_submission_audits`), and match review decisions (`db.match_reviews`) are retained permanently for legal auditability.
- **Soft Deletion:** Deleting a missing person case marks `is_deleted = True` (`soft_delete`). Case records are excluded from normal application views, but audit history and event logs are preserved.

---

## 6. Access Control & Authorization Matrix

| User Role | View Public Reports | Register Cases | View Own Cases | View All Cases | Review Match Candidates | Confirm Match / Lifecycle Changes |
|---|---|---|---|---|---|---|
| **Public User** | ❌ (Status Lookup Only) | ✅ (Public Submission) | ❌ | ❌ | ❌ | ❌ |
| **Officer** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Administrator** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 7. Educational Project Notice

*This document is prepared for educational and project demonstration purposes for the Missing Person Identification System.*
