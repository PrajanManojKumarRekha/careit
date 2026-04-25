"""Step-1 contract tests for core_logic package."""

from src.core_logic import FhirBundleResult
from src.core_logic import PrescriptionRequest
from src.core_logic import PrescriptionSafetyResult
from src.core_logic import SlotRequest
from src.core_logic import SlotResult
from src.core_logic import SoapNote
from src.core_logic import SpecialtyRecommendation
from src.core_logic import SymptomInput


def test_contracts_can_be_instantiated() -> None:
    symptom = SymptomInput(symptom="headache", patient_id="patient-123")
    recommendation = SpecialtyRecommendation(
        specialty="Neurology",
        department="CareNavigation",
        rationale="Symptom map match",
        source_symptom="headache",
    )
    slot_request = SlotRequest(
        candidate_slots=["10:00", "10:30"],
        booked_slots=["10:00"],
    )
    slot_result = SlotResult(available_slots=["10:30"])
    soap_note = SoapNote(
        subjective="Headache for 2 days.",
        objective="No acute distress.",
        assessment="Likely tension headache.",
        plan="Hydration and follow-up.",
    )
    prescription = PrescriptionRequest(
        medication_name="Acetaminophen",
        dosage_text="500 mg",
        frequency_text="q8h prn",
        duration_text="3 days",
        rxnorm_code="161",
    )
    safety = PrescriptionSafetyResult(
        is_allowed=True,
        reason="General/non-controlled medication.",
        normalized_medication_name="acetaminophen",
    )
    fhir = FhirBundleResult(bundle={"resourceType": "Bundle"}, included_resource_types=["Consent"])

    assert symptom.symptom == "headache"
    assert recommendation.specialty == "Neurology"
    assert slot_request.booked_slots == ["10:00"]
    assert slot_result.available_slots == ["10:30"]
    assert soap_note.subjective.startswith("Headache")
    assert prescription.medication_name == "Acetaminophen"
    assert safety.is_allowed is True
    assert fhir.bundle["resourceType"] == "Bundle"


def test_slot_request_defaults_are_explicit() -> None:
    request = SlotRequest(candidate_slots=[], booked_slots=[])

    assert request.candidate_slots == []
    assert request.booked_slots == []
