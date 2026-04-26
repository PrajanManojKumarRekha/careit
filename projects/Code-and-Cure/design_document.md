# CareIT Design Document (Technical + Operational)

## 1) Purpose

This document defines how CareIT operates end-to-end for the hackathon prototype, including:
- symptom triage,
- booking and consultation flow,
- SOAP/PDF artifact generation,
- prescription safety gating,
- interoperability packaging (FHIR with HL7 handoff path),
- EMR vendor handoff assumptions.

This is a workflow/documentation system and not a diagnostic tool.

## 2) System Architecture

### Domain Ownership
- `src/frontend/` (Person 1): user interfaces and workflow screens.
- `src/api/` (Person 2): routing, validation, and service orchestration.
- `src/core_logic/` (Person 3): pure deterministic business logic.
- `src/database/` (Person 4): schema, seed data, and persistence wrappers.

### Core Design Rule
Core logic remains side-effect free:
- no network calls,
- no file writes,
- no DB access,
- all external state injected as inputs.

## 3) End-to-End Technical Flow

1. **Patient enters free-text symptoms** in the triage chatbox.
2. API sends text to core logic triage (`map_symptom_to_specialty`).
3. Core logic returns recommendation:
   - specialty,
   - department,
   - rationale,
   - matched cues,
   - confidence.
4. API fetches doctor candidates and booked slots (DB), then calls `generate_available_slots`.
5. Patient books an available slot.
6. Consultation occurs (chat/video simulation for demo).
7. Transcript is parsed using `parse_transcript_to_soap`.
8. SOAP note is rendered to PDF bytes via `render_soap_note_pdf_bytes`.
9. Clinician review/sign checkpoint occurs before final export.
10. Doctor/clinician approves SOAP content.
11. FHIR bundle is built (`build_fhir_bundle`) for EMR/EHR export with:
    - `Consent`,
    - `Composition`,
    - optional `MedicationRequest` when prescription flow is used.
12. Integration layer maps/exports to vendor handoff target:
    - FHIR-native endpoint where possible,
    - HL7 representation pathway for legacy systems.
13. Prescription request is a separate branch evaluated by `check_prescription_safety`.
14. If policy allows, medicine prescription order PDF is produced with headstamp metadata.

## 3B) Arrow-by-Arrow Workflow (Simple View)

### A) Symptom to Booking
`Patient UI` -> `API /symptoms` -> `core_logic.map_symptom_to_specialty` -> `API response` -> `Patient UI shows specialty + rationale`

`Patient selects doctor` -> `API /appointments/slots` -> `DB booked slots + doctor shift` -> `core_logic.generate_available_slots` -> `UI shows open times`

`Patient clicks book` -> `API /appointments/book` -> `DB save appointment` -> `Doctor dashboard queue`

### B) Consultation to SOAP
`Doctor + Patient consultation` -> `transcript text` -> `API /soap/parse` -> `core_logic.parse_transcript_to_soap` -> `SOAP JSON (S/O/A/P)`

`SOAP JSON` -> `core_logic.render_soap_note_pdf_bytes` -> `SOAP PDF` -> `Reviewer/Signer screen`

### C) Review and Prescription Gate
`Reviewer/Doctor approves SOAP` -> `API marks SOAP approved` -> `EMR export path unlocked`

`optional prescription request` -> `API policy check` -> `core_logic.check_prescription_safety`

If **blocked**:
`policy result = blocked` -> `UI shows blocked reason` -> `no final medicine prescription order PDF issued`

If **approved**:
`policy result = approved` -> `medicine prescription order PDF with headstamp metadata` -> `ready for optional patient-facing prescription flow`

### D) Interoperability and Handoff
`approved SOAP` -> `core_logic.build_fhir_bundle` -> `FHIR Bundle (Consent + Composition + optional MedicationRequest)`

`FHIR Bundle` -> `integration adapter layer` -> `vendor target`
- FHIR-native vendors: direct FHIR route
- legacy vendors: HL7 transformation path before submission

### E) Final Status Loop
`vendor submit result` -> `API status update` -> `UI status badge`
- success
- review required
- retry needed

## 4) Operational Flow and Roles

- **Patient:** enters symptoms, books, attends consult.
- **Doctor:** reviews generated SOAP and treatment recommendation.
- **Signer/Clinical Reviewer:** validates SOAP details before finalization.
- **Legal/Compliance:** validates consent and policy readiness.
- **System Integrator/API:** handles transport and vendor-specific handoff.

## 5) Critical Checkpoints

### 5.1 Clinician-in-the-Loop
Before final export:
- clinician verifies SOAP sections,
- confirms diagnosis wording and laterality,
- signs off for downstream document generation.

### 5.2 Prescription Policy Gate
Controlled substances are blocked.
Final medicine prescription order requires:
- policy allow decision,
- provider credential readiness checks (NPI/DEA where required by path).
This gate is for medicine prescription order issuance and does not block SOAP-approved EMR/EHR export.

### 5.3 Coding Readiness
SOAP text and interoperability coding are not the same.
If robust code mapping is uncertain, mark as review-required rather than inferring final code.

## 6) Interoperability Strategy

### Canonical Internal Output
Core logic outputs:
- structured SOAP note,
- SOAP PDF bytes,
- policy-gated prescription decision,
- FHIR bundle resources.

### HL7/FHIR Handoff Model
- Prefer FHIR-native vendor ingestion.
- Use adapter layer for vendor-specific differences.
- Maintain an HL7 transformation pathway for legacy environments.

### Vendor Adapter Assumptions
- **Epic:** app onboarding/registration constraints may apply.
- **Athena:** REST/FHIR-oriented integration is common.
- **Legacy EMR:** may require HL7 feed via integration engine.

## 7) Data and Scale Strategy

- Use synthetic datasets for practitioner/headstamp scale testing.
- Synthea-derived data is preferred for non-production simulation.
- Clearly label synthetic records and avoid real PHI in demo assets.

## 8) Reliability and Failure Handling

- If triage has low confidence: return fallback + review guidance.
- If provider credentials missing: block final medicine prescription order issuance.
- If export adapter fails: persist artifact and return retryable status.
- If coding uncertain: set review-required state.

## 9) Non-Goals (Prototype Boundaries)

- Not a legal EPCS implementation.
- Not a certified diagnostic engine.
- Not full production interoperability certification.

## 10) Deliverable Outputs for Demo

- Triage recommendation payload.
- Available slots payload.
- Structured SOAP JSON.
- SOAP PDF.
- Prescription status (approved/blocked) and optional medicine prescription order PDF.
- FHIR bundle document output.
- Documented HL7 transformation path and vendor handoff architecture.
