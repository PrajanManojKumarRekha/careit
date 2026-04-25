import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_by_email(email: str):
    res = supabase.table("users").select("*").eq("email", email).single().execute()
    return res.data

def insert_user(email: str, password_hash: str, full_name: str, role: str):
    res = supabase.table("users").insert({
        "email": email,
        "password_hash": password_hash,
        "full_name": full_name,
        "role": role
    }).execute()
    return res.data[0]

def insert_doctor_profile(user_id: str, specialty: str, license_no: str, lat: float, lng: float, address: str):
    res = supabase.table("doctors").insert({
        "user_id": user_id,
        "specialty": specialty,
        "license_no": license_no,
        "lat": lat,
        "lng": lng,
        "address": address
    }).execute()
    return res.data[0]

def get_doctors(specialty: str | None = None):
    query = supabase.table("doctors").select("*")

    if specialty:
        query = query.eq("specialty", specialty)

    return query.execute().data

def insert_appointment(patient_id: str, doctor_id: str, scheduled_at: str):
    res = supabase.table("appointments").insert({
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "scheduled_at": scheduled_at
    }).execute()
    return res.data[0]

def get_appointments_for_patient(patient_id: str):
    return supabase.table("appointments").select("*").eq("patient_id", patient_id).execute().data

def get_appointments_for_doctor(doctor_id: str):
    return supabase.table("appointments").select("*").eq("doctor_id", doctor_id).execute().data

def insert_intake_form(appointment_id: str, patient_id: str, symptoms: str, allergies: str, medications: str, medical_history: str):
    res = supabase.table("intake_forms").insert({
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "symptoms": symptoms,
        "allergies": allergies,
        "medications": medications,
        "medical_history": medical_history
    }).execute()
    return res.data[0]

def insert_soap_note(appointment_id: str, doctor_id: str, subjective: str, objective: str, assessment: str, plan: str, raw_transcript: str):
    res = supabase.table("soap_notes").insert({
        "appointment_id": appointment_id,
        "doctor_id": doctor_id,
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "plan": plan,
        "raw_transcript": raw_transcript
    }).execute()
    return res.data[0]

def approve_soap_note(note_id: str):
    res = supabase.table("soap_notes").update({
        "approved": True,
        "approved_at": "now()"
    }).eq("id", note_id).execute()
    return res.data[0]