import uuid as _uuid

from fastapi import APIRouter, HTTPException, Depends
from src.api.models import BookingRequest, RescheduleRequest, AppointmentMeetingLinkUpdate
from src.api.config import ALLOW_DEMO_MODE
from src.api.dependencies import require_role, get_current_user
from src.database.db_client import (
    insert_appointment,
    get_appointment,
    get_all_appointments,
    get_appointments_for_patient,
    get_or_create_any_doctor,
    get_or_create_doctor_profile,
    update_appointment_status,
    update_appointment_meeting_link,
    reschedule_appointment,
    patient_owns_appointment,
    doctor_owns_appointment,
)

router = APIRouter()


def _is_valid_uuid(val: str) -> bool:
    try:
        _uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False


@router.post("/", dependencies=[Depends(require_role("patient"))])
async def create_appointment(request: BookingRequest, current_user: dict = Depends(get_current_user)):
    """
    Patient books a persisted time slot. patient_id is sourced from JWT.
    """
    patient_id = current_user["user_id"]

    if not _is_valid_uuid(request.doctor_id):
        if not ALLOW_DEMO_MODE:
            raise HTTPException(
                status_code=400,
                detail="Doctor booking is only supported for persisted provider records.",
            )
        fallback_doctor = get_or_create_any_doctor()
        if not fallback_doctor or not fallback_doctor.get("id"):
            raise HTTPException(status_code=500, detail="No demo doctor profile available for booking.")
        doctor_id = fallback_doctor["id"]
    else:
        doctor_id = request.doctor_id

    row = insert_appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        scheduled_at=request.scheduled_at,
    )

    if not row or not row.get("id"):
        raise HTTPException(status_code=500, detail="Failed to create appointment.")

    return {
        "appointment_id": row["id"],
        "status": row.get("status", "pending"),
        "message": "Appointment booked successfully",
        "booking": row,
    }


@router.get("/")
async def get_appointments(current_user: dict = Depends(get_current_user)):
    """
    Returns appointments scoped to the authenticated user's role.
    Patient sees own bookings; doctor sees their schedule.
    """
    user_id = current_user["user_id"]
    role = current_user["role"]

    if role == "patient":
        return get_appointments_for_patient(patient_id=user_id)

    if role == "doctor":
        if ALLOW_DEMO_MODE:
            return get_all_appointments()
        doctor = get_or_create_doctor_profile(user_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found for current user.")
        return get_all_appointments()

    raise HTTPException(
        status_code=403,
        detail=f"Role '{role}' is not permitted to access appointments.",
    )


@router.get("/{appointment_id}")
async def get_appointment_detail(appointment_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_valid_uuid(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found.")

    appointment = get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    role = current_user["role"]
    user_id = current_user["user_id"]
    if role == "patient" and appointment.get("patient_id") != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own appointments.")
    if role == "doctor":
        doctor = get_or_create_doctor_profile(user_id)
        if not doctor:
            raise HTTPException(status_code=403, detail="You can only view your own appointments.")
        if not ALLOW_DEMO_MODE and not doctor_owns_appointment(doctor["id"], appointment_id):
            raise HTTPException(status_code=403, detail="You can only view your own appointments.")
    if role not in {"patient", "doctor"}:
        raise HTTPException(status_code=403, detail="Role is not permitted to access appointments.")

    return appointment


@router.patch("/{appointment_id}/meeting-link", dependencies=[Depends(require_role("doctor"))])
async def update_meeting_link(
    appointment_id: str,
    body: AppointmentMeetingLinkUpdate,
    current_user: dict = Depends(get_current_user),
):
    if not _is_valid_uuid(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found.")

    doctor = get_or_create_doctor_profile(current_user["user_id"])
    if not doctor:
        raise HTTPException(status_code=403, detail="You can only edit meeting links for your own appointments.")
    if not ALLOW_DEMO_MODE and not doctor_owns_appointment(doctor["id"], appointment_id):
        raise HTTPException(status_code=403, detail="You can only edit meeting links for your own appointments.")

    row = update_appointment_meeting_link(appointment_id, body.meeting_link)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to update meeting link.")

    return {
        "appointment_id": appointment_id,
        "meeting_link": row.get("meeting_link"),
        "message": "Meeting link updated.",
        "booking": row,
    }


@router.patch("/{appointment_id}/cancel", dependencies=[Depends(require_role("patient"))])
async def cancel_appointment(appointment_id: str, current_user: dict = Depends(get_current_user)):
    """Patient cancels one of their own appointments."""
    patient_id = current_user["user_id"]

    if not _is_valid_uuid(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if not patient_owns_appointment(patient_id, appointment_id):
        raise HTTPException(status_code=403, detail="You can only cancel your own appointments.")

    row = update_appointment_status(appointment_id, "cancelled")
    return {"appointment_id": appointment_id, "status": "cancelled", "message": "Appointment cancelled.", "booking": row}


@router.patch("/{appointment_id}/reschedule", dependencies=[Depends(require_role("patient"))])
async def reschedule_appointment_route(
    appointment_id: str,
    body: RescheduleRequest,
    current_user: dict = Depends(get_current_user),
):
    """Patient reschedules one of their own appointments to a new time."""
    patient_id = current_user["user_id"]

    if not _is_valid_uuid(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if not patient_owns_appointment(patient_id, appointment_id):
        raise HTTPException(status_code=403, detail="You can only reschedule your own appointments.")

    row = reschedule_appointment(appointment_id, body.new_scheduled_at)
    return {
        "appointment_id": appointment_id,
        "scheduled_at": body.new_scheduled_at,
        "status": row.get("status", "confirmed"),
        "message": "Appointment rescheduled successfully.",
        "booking": row,
    }
