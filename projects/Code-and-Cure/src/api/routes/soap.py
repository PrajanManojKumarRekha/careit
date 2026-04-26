from fastapi import APIRouter, HTTPException, Depends
from src.api.models import ConsultationTranscript, SOAPNote, SOAPApprovalRequest
from src.api.dependencies import require_role, get_current_user
from src.core_logic.soap_parser import parse_transcript_to_soap
from src.database.db_client import (
    insert_soap_note,
    approve_soap_note,
    update_soap_note_content,
    get_soap_note_by_appointment,
    get_doctor_by_user_id,
)

router = APIRouter()


@router.post("/generate", response_model=SOAPNote, dependencies=[Depends(require_role("doctor"))])
async def generate_soap_note(request: ConsultationTranscript):
    """
    Doctor-only route.
    Parses raw transcript via Person 3 and returns draft SOAP note for review.
    """
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")

    parsed = parse_transcript_to_soap(request.transcript)

    return SOAPNote(
        subjective=parsed.subjective,
        objective=parsed.objective,
        assessment=parsed.assessment,
        plan=parsed.plan,
    )


@router.patch("/approve", dependencies=[Depends(require_role("doctor"))])
async def approve_soap_note_route(
    request: SOAPApprovalRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Doctor-only route.
    Persists the final edited SOAP note (insert if first save, update if draft exists),
    then marks it approved. Returns note_id for downstream FHIR export.
    """
    doctor_user_id = current_user["user_id"]
    note = request.edited_note

    # Resolve users.id -> doctors.id (JWT carries users.id; soap_notes references doctors.id)
    doctor = get_doctor_by_user_id(doctor_user_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found for current user.")
    doctor_id = doctor["id"]

    existing = get_soap_note_by_appointment(request.appointment_id)

    if existing:
        note_id = existing["id"]
        update_soap_note_content(
            note_id=note_id,
            subjective=note.subjective,
            objective=note.objective,
            assessment=note.assessment,
            plan=note.plan,
            raw_transcript=existing.get("raw_transcript", ""),
        )
    else:
        result = insert_soap_note(
            appointment_id=request.appointment_id,
            doctor_id=doctor_id,
            subjective=note.subjective,
            objective=note.objective,
            assessment=note.assessment,
            plan=note.plan,
            raw_transcript="",
        )
        note_id = result.get("id") if result else None
        if not note_id:
            raise HTTPException(status_code=500, detail="Failed to persist SOAP note.")

    approved = approve_soap_note(note_id)

    return {
        "status": "success",
        "message": f"SOAP note for appointment {request.appointment_id} has been approved.",
        "record_status": "APPROVED",
        "note_id": note_id,
        "approved_at": approved.get("approved_at"),
    }
