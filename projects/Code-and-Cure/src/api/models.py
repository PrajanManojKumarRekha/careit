from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

# --- Auth Models ---
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # 'patient' or 'doctor'

class UserLogin(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    role: str  # 'patient' or 'doctor'

# --- Symptom & Triage Models ---
class SymptomRequest(BaseModel):
    symptoms: str                          # Free-text input
    red_flag_context: Optional[str] = None # Additional escalation context

class TriageResponse(BaseModel):
    recommended_specialty: str
    department: str
    rationale: str
    extracted_symptom_cues: List[str]
    confidence: Optional[float] = None

# --- Doctor & Appointment Models ---
class Doctor(BaseModel):
    id: str
    name: str       # mapped from DB full_name
    specialty: str
    location: str   # mapped from DB address
    rating: float
    review_count: int

class AppointmentSlot(BaseModel):
    id: str
    doctor_id: str
    start_time: datetime
    is_available: bool

class BookingRequest(BaseModel):
    doctor_id: str              # doctors.id (DB primary key from /doctors list)
    scheduled_at: str           # ISO-8601 datetime string (from slot start_time)
    slot_id: Optional[str] = None  # UI context only; not persisted to DB

# --- Intake Models ---
# Field names align with DB schema (intake_forms table)
class IntakeForm(BaseModel):
    appointment_id: str
    symptoms: str                        # DB: symptoms (was: chief_complaint)
    medical_history: Optional[str] = None
    medications: Optional[str] = None   # DB: medications (was: current_medications)
    allergies: Optional[str] = None
    patient_id: Optional[str] = None    # Populated on GET from DB; ignored from client on POST

# --- Consultation & SOAP Models ---
class ConsultationTranscript(BaseModel):
    appointment_id: str
    transcript: str

class SOAPNote(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str

class SOAPApprovalRequest(BaseModel):
    appointment_id: str
    edited_note: SOAPNote

class FHIRRecord(BaseModel):
    resourceType: str = "Bundle"
    entry: List[Dict]

# --- Digital Prescription Models (MedicationRequest) ---
class PrescriptionItem(BaseModel):
    medication_name: str
    dosage: str
    frequency: str
    duration: str

class DigitalPrescription(BaseModel):
    appointment_id: str
    patient_id: str
    doctor_id: str
    medications: List[PrescriptionItem]
    notes: Optional[str] = None
    prescribed_at: datetime = Field(default_factory=datetime.now)

# --- EHR Export Models (FHIR R4 Alignment) ---
class EHRExportRequest(BaseModel):
    appointment_id: str
    target_emr: str = "Athenahealth"

class EHRExportResponse(BaseModel):
    export_id: str
    status: str  # "success" or "pending"
    fhir_bundle: Dict  # Raw FHIR R4 JSON
    submission_timestamp: datetime
