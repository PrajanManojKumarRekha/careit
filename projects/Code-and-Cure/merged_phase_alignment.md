# Merged-Phase Alignment Review (Step 12)

## Objective
Assess current merged implementation against the target Golden Path and identify integration gaps that must be closed before demo freeze.

## Snapshot by Domain

### Person 3 (`src/core_logic`) - Ready
- Implemented:
  - free-text triage
  - slot filtering
  - SOAP parsing
  - SOAP PDF generation
  - prescription safety gating
  - FHIR bundle generation
  - red-flag escalation helper
- Status: logic layer ready for API wiring.

### Person 4 (`src/database`) - Mostly Ready
- Implemented:
  - doctors/appointments/intake/soap/fhir/prescription tables
  - review metadata fields
  - SOAP/prescription PDF metadata fields
  - db client helpers for main flows
- Status: data layer present; needs full route-level use by API.

### Person 2 (`src/api`) - Partial
- Implemented:
  - auth routes
  - symptom route scaffold
  - doctors route scaffold
  - appointments route scaffold
- Gaps:
  - symptom route still mock map (not wired to core triage)
  - appointments booking still in-memory in current route file
  - SOAP/prescription/FHIR routers not enabled in `main.py`
- Status: primary integration bottleneck.

### Person 1 (`src/frontend`) - Partial
- Implemented:
  - basic protected dashboard shell
- Gaps:
  - dashboard currently hardcodes specialty
  - missing full consult/SOAP/PDF/prescription UX wiring
  - missing complete doctor/slot workflow wiring
- Status: UI integration pending API contract usage.

## Golden Path Parity Check

1. Patient free-text symptom input -> **Partially ready** (UI/API still mocked in places).
2. Dynamic triage recommendation -> **Logic ready**, API route still mock.
3. Doctor list with review signals -> **DB fields ready**, API/UI partial.
4. Slot booking saved to DB -> **DB helper ready**, current API route still in-memory.
5. Doctor dashboard shows booking -> **Partial**, depends on DB-backed appointment wiring.
6. SOAP generation -> **Logic ready**, API route enablement pending.
7. SOAP review PDF -> **Logic ready**, API/UI wiring pending.
8. SOAP-approved EMR export path -> **Design/contract ready**, API flow pending.
9. Optional policy-gated medicine prescription order -> **Logic ready**, API/UI flow pending.
10. FHIR bundle output -> **Logic ready**, API export route pending.

## Highest-Priority Fix Sequence

1. Wire API symptom route to `core_logic.map_symptom_to_specialty`.
2. Replace in-memory appointment booking with DB-backed booking.
3. Enable and wire SOAP route to parser + PDF generator.
4. Enforce SOAP approval gate before FHIR/HL7 export.
5. Wire optional medicine prescription order branch with policy gating.
6. Update frontend to consume live API responses (remove hardcoded specialty).

## Definition of Done for Integration Freeze

- No hardcoded triage outputs in frontend.
- No in-memory booking path in API.
- SOAP parse + SOAP PDF route operational end-to-end.
- SOAP approval required for FHIR/HL7 export.
- Medicine prescription order path optional and policy-gated.
- Golden Path demo runs cleanly from patient input to export response.
