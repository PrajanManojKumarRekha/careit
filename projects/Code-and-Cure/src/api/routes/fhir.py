from fastapi import APIRouter, HTTPException, Depends
from src.api.models import EHRExportResponse
from src.api.dependencies import require_role
from datetime import datetime
import uuid

"""
COMPLIANCE REFERENCES:
- Responsibilities.md: Doctor-only route that fetches approved notes and returns FHIR.
- context.md: The final step of the Golden Path workflow (Export to Athenahealth).
- ai.md: SRP enforced. The route has zero formatting logic; it strictly delegates to Person 3/4 mocks.
"""

router = APIRouter()

# --- MOCK PERSON 3 & 4 SERVICES ---

def mock_fetch_approved_documents(appointment_id: str):
    """Mock Person 4 DB Call: Fetches the finalized SOAP note and Prescription."""
    # In a real app, this would query Supabase where status = 'APPROVED'
    return {
        "soap_note": {
            "subjective": "Patient reports worsening headaches over the past 3 days.",
            "objective": "Patient appears in mild distress. No visible physical trauma.",
            "assessment": "Tension headache, possible migraine.",
            "plan": "Prescribe ibuprofen 400mg PRN. Rest in dark room. Follow up in 1 week if no improvement."
        },
        "prescription": {
            "medications": [
                {"medication_name": "Ibuprofen", "dosage": "400mg", "frequency": "PRN", "duration": "7 days"}
            ]
        }
    }

def mock_build_fhir_bundle(soap_note: dict, prescription: dict) -> dict:
    """Mock Person 3 Core Logic: Packages data into FHIR R4 JSON standard."""
    # In reality, this imports from src.core_logic.fhir_builder
    return {
        "resourceType": "Bundle",
        "type": "document",
        "timestamp": datetime.now().isoformat(),
        "entry": [
            {
                "resource": {
                    "resourceType": "Composition",
                    "title": "Clinical Consultation Note",
                    "status": "final",
                    "section": [
                        {"title": "Subjective", "text": {"div": soap_note["subjective"]}},
                        {"title": "Assessment", "text": {"div": soap_note["assessment"]}}
                    ]
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "medicationCodeableConcept": {"text": prescription["medications"][0]["medication_name"]},
                    "status": "active"
                }
            }
        ]
    }

@router.get("/export/{appointment_id}", response_model=EHRExportResponse, dependencies=[Depends(require_role("doctor"))])
async def export_to_emr(appointment_id: str):
    """
    Doctor-only route.
    Fetches the finalized clinical documents and exports them as a FHIR Bundle.
    """
    # 1. DELEGATE TO DB LAYER (Person 4)
    # The API layer shouldn't know HOW to query the DB, just that it needs documents.
    documents = mock_fetch_approved_documents(appointment_id)
    if not documents:
        raise HTTPException(status_code=404, detail="Approved clinical documents not found for this appointment.")

    # 2. DELEGATE TO LOGIC LAYER (Person 3)
    # The API layer doesn't know how to format FHIR, it just passes data to the builder.
    fhir_bundle = mock_build_fhir_bundle(documents["soap_note"], documents["prescription"])

    # 3. Formulate the API Response
    return EHRExportResponse(
        export_id=f"export-{uuid.uuid4()}",
        status="success",
        fhir_bundle=fhir_bundle,
        submission_timestamp=datetime.now()
    )
