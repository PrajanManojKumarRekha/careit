from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_current_user, require_role
from src.api.models import PrescriptionCreateRequest, PrescriptionResponse
from src.core_logic.models import PrescriptionRequest as CorePrescriptionRequest
from src.core_logic.prescription_safety import check_prescription_safety
from src.database.db_client import (
    doctor_owns_appointment,
    get_appointment,
    get_doctor_by_user_id,
    get_prescriptions_for_doctor,
    get_prescriptions_for_patient,
    insert_prescription_order,
)

router = APIRouter()


@router.get("/", response_model=list[PrescriptionResponse])
async def list_prescriptions(current_user: dict = Depends(get_current_user)):
    role = current_user["role"]
    if role == "patient":
        rows = get_prescriptions_for_patient(current_user["user_id"])
    elif role == "doctor":
        doctor = get_doctor_by_user_id(current_user["user_id"])
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found for current user.")
        rows = get_prescriptions_for_doctor(doctor["id"])
    else:
        raise HTTPException(status_code=403, detail="Role is not permitted to view prescriptions.")

    return [PrescriptionResponse(**row) for row in rows]


@router.post("/", response_model=PrescriptionResponse, dependencies=[Depends(require_role("doctor"))])
async def create_prescription(
    request: PrescriptionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    doctor = get_doctor_by_user_id(current_user["user_id"])
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found for current user.")
    if not doctor_owns_appointment(doctor["id"], request.appointment_id):
        raise HTTPException(status_code=403, detail="You can only prescribe for your own appointments.")

    appt = get_appointment(request.appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    safety = check_prescription_safety(CorePrescriptionRequest(medication_name=request.medication_name))
    status = "approved" if safety.is_allowed else "blocked"
    row = insert_prescription_order(
        appointment_id=request.appointment_id,
        patient_id=appt["patient_id"],
        doctor_id=doctor["id"],
        requested_medication=request.medication_name,
        approval_status=status,
        block_reason=None if safety.is_allowed else safety.reason,
    )
    if not row.get("id"):
        raise HTTPException(status_code=500, detail="Failed to create prescription order.")
    return PrescriptionResponse(**row)
