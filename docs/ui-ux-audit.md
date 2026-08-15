# UI/UX Audit Report — Missing Person Identification System (Phase 26)

**Audit Date**: 14 August 2026  
**Auditor**: UI/UX Engineering Team  
**Scope**: All Streamlit Application Pages (`app.py` & `pages/*.py`)  

---

## Executive Summary

An exhaustive UI/UX audit was conducted across all 17 Streamlit application pages of the Missing Person Identification System. While the core functional architecture (Authentication, Case Management, MediaPipe Face Landmarking, 1,404-D Face Embeddings, KNN Vector Search, Video Processing, Map Density Visualization, Public Submission Portal, and Case Lifecycle Services) is 100% complete and fully verified by automated tests, the user interface currently exhibits visual inconsistencies, ad-hoc styling scattering, inconsistent button hierarchies, variable spacing, and unstandardized loading/empty/error states.

This document details the findings across 17 audit dimensions and outlines the design system requirements for the Phase 26 UI/UX overhaul.

---

## 1. Page-by-Page Audit Findings

### 1.1 Home / Landing Portal (`app.py`)
- **Visual Consistency**: Scattered CSS definitions, mixed font sizes, inconsistent card padding.
- **Hierarchy**: Good hero section layout, but metric cards use custom inline styles with hardcoded hex colors (`#ef4444`, `#10b981`, `#f59e0b`, `#3b82f6`).
- **Sidebar & Navigation**: Navigation quicklinks use generic Streamlit buttons without icon cues or role badges.
- **Improvements Needed**: Centralize CSS styling, introduce reusable KPI cards, implement clean sidebar branding with role badges.

### 1.2 Authentication Login Page (`pages/login.py`)
- **Layout & Structure**: Centered Streamlit form with basic input fields.
- **Error & Validation States**: Basic error banner. Does not expose username existence, but error messages lack visual structure.
- **Card Presentation**: Form is unstyled standard Streamlit form container.
- **Improvements Needed**: Wrap login into an enterprise-grade card container, include logo/branding header, add explicit loading feedback, sanitize error messages cleanly.

### 1.3 Admin Dashboard (`pages/admin_dashboard.py`)
- **Dashboard Structure**: Displays metric cards and charts.
- **KPI Metrics**: Custom `_stat_card` HTML helper defined inline within page file.
- **Charts & Visuals**: Uses Plotly charts with default dark theme templates, but color palettes vary across charts.
- **Recent Activity**: Tables display raw dictionaries or unstyled text blocks.
- **Improvements Needed**: Standardize KPI card layout across 6 key metrics (Total Cases, Pending Verification, Active Investigations, Potential Matches, Confirmed Matches, Resolved Cases). Harmonize chart color palettes (Deep Navy, Soft Blue, Emerald Green).

### 1.4 Officer Dashboard (`pages/officer_dashboard.py`)
- **Dashboard Structure**: Displays officer case overview and assigned tasks.
- **Role Isolation**: Good IDOR protection, but UI structure differs visually from the Admin dashboard.
- **Improvements Needed**: Align Officer Dashboard with the global design system (My Cases, Active Cases, Pending Cases, Recently Updated Cases) while keeping Admin analytics hidden.

### 1.5 Case Management & Case Directory (`pages/case_management.py` & `pages/cases.py`)
- **Search & Filters**: Search fields and dropdowns are scattered across multiple columns without a cohesive filter bar container.
- **Case Listing**: Cards have inconsistent image aspect ratios (`200px` height container with variable object-fit rendering).
- **Case Detail View**: Detailed view lacks structured sections (Header -> Person Info -> Last Seen Info -> AI Candidate vs Human Confirmed -> Audit Timeline -> Action Buttons).
- **Improvements Needed**: Implement unified filter bar, standard case cards, structured Case Detail view with distinct AI Candidate warning tags vs Human Confirmed tags, and confirmation modals for state transitions.

### 1.6 Admin Face Matching & Image Matching (`pages/admin_face_matching.py` & `pages/matching.py`)
- **Upload Experience**: Standard `st.file_uploader` without custom drag-and-drop feedback banner.
- **Results Presentation**: Query image and candidate images are shown side-by-side, but the warning label distinguishing AI candidate ranking from human confirmation is subtle.
- **Confirmation Workflow**: Confirmation action is executed via direct button click without a explicit confirmation modal step.
- **Improvements Needed**: Add prominent warning banner (*"AI-generated candidate — human review required"*), side-by-side comparison cards with similarity gauges, and two-step confirmation dialogs.

### 1.7 Human Match Review UI (`pages/match_review.py`)
- **Layout**: Displays pending match review records with decision buttons.
- **Warning & Guidance**: Needs explicit high-visibility warning header indicating AI candidates must be human-verified.
- **Confirmation Action**: Requires a multi-step confirmation modal to prevent accidental identity confirmations.

### 1.8 Video Sightings & Video AI Processing (`pages/video_sightings.py`)
- **Processing Feedback**: Displays Streamlit spinner, but lacks step-by-step progress feedback during long video sampling runs.
- **Results View**: Frame extraction grid displays raw file paths in sub-captions.
- **Improvements Needed**: Implement step progress indicators, sanitize file paths (`os.path.basename` only), present extracted faces in a clean responsive grid, hide raw 1,404-D vectors under collapsible technical details.

### 1.9 Admin Public Submission Review (`pages/admin_public_submissions.py`)
- **Layout**: Grid layout of pending public reports.
- **Review Actions**: Direct "Approve" and "Reject" buttons.
- **Improvements Needed**: Add approval/rejection confirmation modals, present complainant details in a privacy-sanitized inspector view.

### 1.10 Public Submission Portal (`pages/public_portal.py`)
- **Form Design**: Large single form with multiple text fields.
- **Mobile Responsiveness**: Standard Streamlit layout, but multi-column field blocks squish on mobile viewports (<480px width).
- **Submission Confirmation**: Shows submission reference number, but needs clean receipt card presentation.
- **Public Lookup**: Clean lookup, needs consistent privacy masking for complainant contact details.
- **Improvements Needed**: Create multi-step or clearly sectioned form (Person Info -> Last Seen Info -> Contact Info -> Photo -> Consent), optimize mobile CSS, format reference number receipt cleanly.

### 1.11 India Case Density Map (`pages/admin_map.py` & `pages/map.py`)
- **Map Container**: Embeds Folium HTML, but container border and legend overlay vary by page.
- **Filter Controls**: Filter dropdowns placed above map without dedicated control panel styling.
- **Privacy Sanitization**: Map markers must remain aggregated or anonymized to prevent public privacy leaks.
- **Improvements Needed**: Wrap map in styled map container, add explicit density legend, harmonize color palette with Deep Navy theme.

---

## 2. Comprehensive Evaluation Across 17 UI Dimensions

| UI Dimension | Current Status | Issues Identified | Target Resolution |
|---|---|---|---|
| **1. Visual Consistency** | ⚠️ Needs Improvement | Scattered inline CSS across 17 files; varying colors & padding. | Centralize CSS in `ui/styles.py` & `.streamlit/config.toml`. |
| **2. Color Palette** | ⚠️ Needs Improvement | Ad-hoc hex colors (`#10b981`, `#ef4444`, `#3b82f6`, `#f59e0b`). | Standardize to Deep Navy, Slate, Soft Blue, Emerald Green, Ruby Red. |
| **3. Typography** | ⚠️ Needs Improvement | Outfit font loaded via `@import` in `utils/helpers.py`, but font sizes unstandardized. | Implement strict 6-tier typography scale (`ui/theme.py`). |
| **4. Buttons & Hierarchy** | ⚠️ Needs Improvement | All primary buttons use green gradient; secondary buttons lack contrast. | Define primary, secondary, danger, and icon button styles. |
| **5. Forms & Inputs** | ⚠️ Needs Improvement | Inconsistent label spacing; optional vs required fields unlabeled. | Add required indicators (`*`), help tooltips, section headers. |
| **6. Cards & Containers** | ⚠️ Needs Improvement | Custom `glass-card` CSS with hover effects that jump on layout. | Clean flat enterprise cards with subtle borders & soft shadows. |
| **7. Tables & Data Grids** | ⚠️ Needs Improvement | Raw Pandas DataFrames / Streamlit tables with default styling. | Standardized tables with formatted headers, pagination, status badges. |
| **8. Status Badges** | ⚠️ Needs Improvement | 4 basic badge styles (`badge-missing`, `badge-found`, `badge-pending`, `badge-verified`). | Standardize badges for all 10 system statuses with icons & text. |
| **9. Navigation & Shell** | ⚠️ Needs Improvement | Sidebar contains raw page lists; user role badge unstyled. | Standardized sidebar shell with logo, user profile badge, logout button. |
| **10. Dashboards & KPIs** | ⚠️ Needs Improvement | Inconsistent KPI card markup; charts use default templates. | Reusable `render_kpi_card()` component; unified Plotly themes. |
| **11. AI Match vs Human Labels** | ⚠️ Needs Improvement | AI match score shown without prominent human-in-the-loop warning. | Prominent warning banner: *"AI-generated candidate — human review required"*. |
| **12. Loading Feedback** | ⚠️ Needs Improvement | Generic Streamlit spinners without step-by-step progress. | Reusable `render_loading_spinner()` with contextual progress messages. |
| **13. Empty States** | ⚠️ Needs Improvement | Empty tables/containers show blank white space or default text. | Reusable `render_empty_state(icon, title, message)` component. |
| **14. Error Handling** | ⚠️ Needs Improvement | Some pages expose raw Python exception strings on error. | User-friendly `render_error_state()` masking raw tracebacks. |
| **15. Confirmation Modals** | ⚠️ Needs Improvement | Match confirmation and case closing are one-click actions. | Multi-step confirmation dialogs for all high-impact state transitions. |
| **16. Mobile Responsiveness** | ⚠️ Needs Improvement | Multi-column forms overlap or squish on mobile viewports. | Responsive CSS breakpoints for public portal and key forms. |
| **17. Privacy & Sanitization** | ⚠️ Needs Improvement | Raw filesystem paths and raw vector arrays visible in dev pages. | Hide filesystem paths (`os.path.basename` only); collapse vector data. |

---

## 3. UI/UX Refactoring Action Plan

1. **Phase 26.1**: Establish `.streamlit/config.toml`, `ui/theme.py`, `ui/styles.py`, `ui/components.py`.
2. **Phase 26.2**: Refactor `app.py` & `pages/login.py` for standardized application shell & enterprise login.
3. **Phase 26.3**: Overhaul Admin & Officer Dashboards (`admin_dashboard.py`, `officer_dashboard.py`) with reusable KPI cards and harmonized charts.
4. **Phase 26.4**: Refactor Case Directory & Case Detail Views (`case_management.py`, `cases.py`) with clean filter bar, structured case detail layout, and status badges.
5. **Phase 26.5**: Overhaul Match Review & Image Face Matching (`matching.py`, `admin_face_matching.py`, `match_review.py`) with side-by-side comparisons, AI warning banners, and confirmation modals.
6. **Phase 26.6**: Refactor Video Processing UI (`video_sightings.py`) with progress feedback and sanitized path displays.
7. **Phase 26.7**: Polish Public Reporting Portal (`public_portal.py`) & Admin Review (`admin_public_submissions.py`) for mobile responsiveness and privacy.
8. **Phase 26.8**: Polish India Map View (`map.py`, `admin_map.py`) with map legends and clean filter containers.
9. **Phase 26.9**: Create `docs/ui-guidelines.md` and complete `docs/ui-ux-checklist.md`.
10. **Phase 26.10**: Execute full regression test suite (`pytest tests/` and `_verify_phase25.py`).

---

*UI/UX Audit Complete. All findings documented.*
