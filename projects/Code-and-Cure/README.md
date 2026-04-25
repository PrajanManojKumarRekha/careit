Project Name - CureIT
Team Members- Prajan Manoj Kumar Rekha (PrajanManojKumarRekha), Eric Cariaga (eCarCodes), Jessica C O'Bonna (jessic-o), Shayan Ali (CodewithShayan456)
Problem Statement – What problem are you solving?

Healthcare providers, especially small clinics and independent practitioners, face increasing administrative overload do to inefficient documentation, fragmented scheduling tools, and inconsistent clinical note-taking workflows.

Patient records are often scattered across multiple systems or stored in unstructured formats, making it difficult for providers to quickly access and interpret relevant medical history.
Scheduling appointments is frequently handled through disconnected platforms, leading to inefficiencies and double-booking risks. Additionally, clinicians spend a significant portion of their time manually writing or refining clinical notes, reducing time available for patient care.

These challenges reduce workflow efficiency, increased cognitive load for providers, and inconsistent clinical documentation quality across patient visits.

Solution – Describe your solution and how it works.

CureIT is a lightweight, AI-assisted clinical documentation and scheduling platform designed specifically for small healthcare practices and independent practitioners. It streamlines patient management, enhances clinical note-taking, and improves overall workflow efficiency without requiring complex enterprise-level infrastructure.

The system enables:

Doctor Discovery & Scheduling
Patients can search for doctors using location filters and availability data, then book appointments through an integrated scheduling system.
Structured Patient Intake
Patients provide medical history, allergies, and symptoms through guided input forms before consultations.
Real-Time Consultation Support
Consultation sessions are recorded as structured notes during the session, improving documentation consistency.
Standardized Medical Record Formatting
Consultation data is organized into structured formats compatible with healthcare data standards such as FHIR.
Calendar Synchronization
Booked appointments are automatically reflected in both patient and doctor calendars.

Tech Stack – Technologies, frameworks, and tools used.

Frontend
TypeScript
React / Next.js
Tailwind CSS
Google Maps API - Doctor search and location visualization
Calendly API - Appointment scheduling

Backend
Python (FastAPI)
Node.js
OAuth 2.0 Authentication
WebRTC - Real-time communication support

Healthcare Data Integration
FHIR (Fast Healthcare Interoperability Resources) - Primary standard
HL7 (Optional) - Legacy compatibility support

Database
Supabase (PostgreSQL)

Security Considerations

The system follows secure design practices aligned with healthcare software expectations.

Key measures:
OAuth based authentication
Role-based access control
Encrypted data transmission
Secure API communication
Activity logging for traceability

Designed with awareness of regulations such as:
HIPAA
Setup Instructions - How to run your project locally.
Demo - Link to a demo video, live deployment, or screenshots.