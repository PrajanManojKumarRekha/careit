from fastapi import APIRouter, HTTPException, Depends
from src.api.models import BookingRequest
from src.api.dependencies import require_role, get_current_user
from typing import List
from datetime import datetime
import uuid

router = APIRouter()

# --- MOCK PERSON 3 & 4 SERVICES ---
BOOKED_APPOINTMENTS = []

def mock_slot_conflict_checker(slot_id: str) -> bool:
    """Mock Person 3 core logic: checks if slot is taken."""
    for booking in BOOKED_APPOINTMENTS:
        if booking["slot_id"] == slot_id:
            return True
    return False

@router.post("/", dependencies=[Depends(require_role("patient"))])
async def create_appointment(request: BookingRequest, current_user: dict = Depends(get_current_user)):
    """
    POST /api/v1/appointments
    Patient books a time slot. We use their user_id from the secure JWT token.
    """
    # 1. DELEGATE TO LOGIC LAYER: Check for conflicts
    is_conflict = mock_slot_conflict_checker(request.slot_id)
    if is_conflict:
        raise HTTPException(status_code=409, detail="This slot is already booked")

    # 2. DELEGATE TO DB LAYER: Save the booking (simulated)
    appointment_id = str(uuid.uuid4())
    booking_record = {
        "id": appointment_id,
        "slot_id": request.slot_id,
        "patient_id": current_user["user_id"],
        "booked_at": datetime.now().isoformat(),
        "status": "confirmed"
    }
    BOOKED_APPOINTMENTS.append(booking_record)

    return {
        "appointment_id": appointment_id,
        "status": "confirmed",
        "message": "Appointment booked successfully",
        "booking": booking_record
    }

@router.get("/")
async def get_appointments(current_user: dict = Depends(get_current_user)):
    """
    GET /api/v1/appointments
    Returns appointments based on the user's role.
    """
    user_id = current_user["user_id"]
    role = current_user["role"]

    # Mock Person 4 DB queries
    if role == "patient":
        return [b for b in BOOKED_APPOINTMENTS if b["patient_id"] == user_id]
    elif role == "doctor":
        return [b for b in BOOKED_APPOINTMENTS if user_id in b["slot_id"]]
    
    return []
