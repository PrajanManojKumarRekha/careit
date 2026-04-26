# CareIT - Responsible AI Documentation

As a telehealth platform bridging solo medical practitioners with patients, CareIT leverages Artificial Intelligence to streamline triage, medical documentation, and interoperability. Because we operate in the healthcare domain, we hold our AI implementations to the highest standards of safety, fairness, and transparency.

This document outlines our commitment to Responsible AI across the four pillars of our architecture: Frontend, API Gateway, Core AI/Medical Logic, and Database/Security.

---

## 1. Data Sources

*   **Zero-Shot & Few-Shot Prompting:** Our AI Care Navigator (Symptom NLP) and SOAP Note generator do not train on patient data. We rely on pre-trained foundation models (e.g., Google Gemini/OpenAI) using strict zero-shot or few-shot prompts with synthetic examples.

*   **Transcription Audio:** Audio data processed for clinical documentation is held entirely in ephemeral memory. No audio recordings are permanently stored or used to train acoustic models.

*   **Simulated Clinical Data:** All FHIR R4 bundling and testing during development was conducted using synthetic patient data (MOCK_DB). No Real World Data (RWD) or Protected Health Information (PHI) was used in the creation of our AI logic.

## 2. Model Choices

*   **Symptom Triage (NLP):** We utilize a lightweight, high-speed LLM for initial symptom parsing to extract cues (e.g., "headache", "fever"). It acts strictly as a classifier to map symptoms to specialties (e.g., Neurology, General Practice), not as a diagnostic tool.

*   **Speech-to-Text (Transcription):** We utilize a local Whisper-style model (or equivalent secure API) for transcription. This ensures high accuracy for medical terminology while keeping data processing highly controlled.

*   **SOAP Note Generation:** We utilize an advanced LLM specifically prompted for medical summarization. 
    *   *Constraint:* The model is hard-coded via system prompts to only use information present in the transcript. It is explicitly forbidden from hallucinating medical advice or inferring symptoms not spoken by the patient.

## 3. Bias Considerations

*   **Transcription Bias:** We recognize that Speech-to-Text models often struggle with accents, dialects, and non-native speakers. 

  *Mitigation:* We have implemented a "Human-in-the-loop" (HITL) approval gate. The AI only produces a draft SOAP note. The doctor must manually review and edit the transcription and SOAP draft before it is approved and exported to the EMR.

*   **Triage Bias:** NLP symptom checkers can misunderstand colloquial descriptions of pain, potentially under-triaging marginalized groups.

    *Mitigation:* Our triage system acts only as a recommendation engine to help patients find the right specialist. It does not block care or deny appointments. Patients always have the option to manually select a doctor via the Mapbox Discovery tool regardless of the AI's recommendation.

## 4. Failure Cases & Fallbacks

*   **Mapbox / Geolocation Failures (Patient Portal):** 

    *   *The Failure:* The patient denies browser location permissions, has a strict ad-blocker that breaks Mapbox, or is on a slow 3G connection causing the interactive map to fail. If the map is the only way to find a doctor, the patient is blocked from care.

    *   *Fallback / Mitigation:* The UI is built on a split-screen layout. The text-based list of doctors on the left side always loads instantly from the API. The map is a progressive enhancement. If the map fails or location is denied, the UI gracefully falls back to showing doctors based on a manual zip code search.

*   **Silent Upload Failures (Clinical Documentation):** 

    *   *The Failure:* A doctor drags and drops a 2-hour long video file (1 GB) into the upload zone, but the API has a 25 MB limit. If the UI just spins endlessly or throws a generic "Error 500", the doctor gets frustrated and abandons the platform.

    *   *Fallback / Mitigation:* The drag-and-drop UI component performs immediate client-side validation. Before even touching the backend API, the frontend checks the file size and type. If it's too big, the UI instantly turns red and says: File too large. Please upload an audio clip under 25MB."*
 