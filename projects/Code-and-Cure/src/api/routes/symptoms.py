from fastapi import APIRouter, Depends
from src.api.models import SymptomRequest, TriageResponse
from src.api.dependencies import require_role

router = APIRouter()

# --- MOCK PERSON 3 SERVICE (CORE LOGIC) ---
# To satisfy the "Traffic Controller" architecture, the API route must not 
# contain medical logic. We mock Person 3's function here until they merge.
# In production: from src.core_logic.triage import suggest_specialties
def mock_suggest_specialties(symptoms: str, red_flag: str = None) -> TriageResponse:
    MOCK_TRIAGE_MAP = {
        "headache":      {"specialty": "Neurology",         "department": "Navigation/Coordination", "confidence": 0.92},
        "chest pain":    {"specialty": "Cardiology",        "department": "Navigation/Coordination", "confidence": 0.95},
        "skin rash":     {"specialty": "Dermatology",       "department": "Navigation/Coordination", "confidence": 0.88},
    }
    symptom_text = symptoms.strip().lower()
    extracted_cues = [k for k in MOCK_TRIAGE_MAP.keys() if k in symptom_text]

    if red_flag:
        return TriageResponse(
            recommended_specialty="Emergency Medicine",
            department="Clinical/Signer",
            rationale=f"Red flag detected: {red_flag}",
            extracted_symptom_cues=extracted_cues or [symptom_text],
            confidence=0.99
        )

    for cue in extracted_cues:
        res = MOCK_TRIAGE_MAP[cue]
        return TriageResponse(
            recommended_specialty=res["specialty"], department=res["department"],
            rationale=f"Matched '{cue}'", extracted_symptom_cues=extracted_cues, confidence=res["confidence"]
        )

    return TriageResponse(
        recommended_specialty="General Practice", department="Navigation/Coordination",
        rationale="Fallback", extracted_symptom_cues=[symptom_text], confidence=0.50
    )


@router.post("/analyze", response_model=TriageResponse, dependencies=[Depends(require_role("patient"))])
async def analyze_symptoms(request: SymptomRequest):
    """
    AI Care Navigator Route:
    Validates the HTTP request, then immediately delegates the work 
    to the Core Logic service function.
    """
    # DELEGATE TO LOGIC LAYER (Zero business logic in the API route)
    triage_result = mock_suggest_specialties(request.symptoms, request.red_flag_context)
    
    return triage_result
