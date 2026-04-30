import os
import json
import logging
import re

from fastapi import APIRouter, Depends
from src.api.models import SymptomRequest, TriageChatRequest, TriageChatResponse, TriageResponse
from src.api.dependencies import require_role
from src.core_logic.symptom_mapper import map_symptom_to_specialty
from src.core_logic import detect_red_flag_escalation, SymptomInput

logger = logging.getLogger(__name__)

router = APIRouter()

_SPECIALTIES = [
    "Cardiology", "Pulmonology", "Neurology", "Dermatology",
    "Gastroenterology", "Nephrology", "Orthopedics", "ENT",
    "Psychiatry", "Endocrinology", "Urology", "Ophthalmology",
    "Gynecology", "Rheumatology", "Oncology", "General Practice",
]

_SYSTEM_PROMPT = """You are a clinical triage assistant. A patient will describe their symptoms in plain language.
Your job is to identify the MOST APPROPRIATE medical specialty for their primary complaint.

Respond with ONLY a valid JSON object — no extra text, no markdown fences:
{
  "specialty": "<specialty>",
  "rationale": "<1–2 sentence explanation that references the patient's specific symptoms>",
  "confidence": <number between 0.55 and 0.95>
}

Allowed specialties (pick exactly ONE):
Cardiology, Pulmonology, Neurology, Dermatology, Gastroenterology, Nephrology,
Orthopedics, ENT, Psychiatry, Endocrinology, Urology, Ophthalmology,
Gynecology, Rheumatology, Oncology, General Practice

Strict clinical routing rules — follow these precisely:
- Headache (with or without nausea, light sensitivity, or aura) → Neurology
- Migraine, dizziness, vertigo, numbness, tingling, memory problems → Neurology
- Cough, shortness of breath, wheezing, breathing difficulty (non-cardiac) → Pulmonology
- Sore throat, ear pain, earache, runny nose, nasal congestion, sneezing, sinus pain → ENT
- Skin rash, itching, hives, acne, eczema, psoriasis, skin lesions → Dermatology
- Stomach pain, nausea, vomiting, diarrhea, heartburn, bloating → Gastroenterology
- Joint pain, bone pain, back pain, knee/shoulder/hip pain, sports injury → Orthopedics
- Chest pain, palpitations, irregular heartbeat, high blood pressure → Cardiology
- Anxiety, depression, insomnia, panic attacks, mood problems → Psychiatry
- Eye pain, vision changes, blurred vision, eye redness → Ophthalmology
- Diabetes, thyroid issues, hormone imbalance, unexplained weight changes → Endocrinology
- Urinary pain, prostate issues, kidney stones → Urology/Nephrology
- Menstrual issues, pelvic pain, pregnancy concerns → Gynecology
- Fever alone is ambiguous — look at accompanying symptoms to determine specialty
- General Practice ONLY when: (a) symptoms genuinely span multiple unrelated systems, (b) routine checkup/vaccination, (c) prescription refill, (d) truly cannot determine a specific specialist
- NEVER default to General Practice when a more specific specialist clearly applies"""

_CHAT_PROMPT = """You are a careful outpatient triage assistant for a telehealth website.
You are NOT diagnosing. Your job is to either:
1. ask one concise, high-value follow-up question when you do not yet have enough information, or
2. recommend the best specialist once you have enough information, or
3. escalate immediately for emergencies.

Return ONLY JSON with this shape:
{
  "status": "follow_up" | "recommendation" | "emergency",
  "message": "<short patient-facing response>",
  "recommended_specialty": "<specialty or null>",
  "rationale": "<professional rationale or null>",
  "confidence": <number between 0.40 and 0.98 or null>,
  "follow_up_question": "<one clarifying question or null>",
  "suggested_replies": ["<optional short reply>", "<optional short reply>"],
  "conversation_summary": "<brief summary of the symptoms so far>"
}

Allowed specialties:
Cardiology, Pulmonology, Neurology, Dermatology, Gastroenterology, Nephrology,
Orthopedics, ENT, Psychiatry, Endocrinology, Urology, Ophthalmology,
Gynecology, Rheumatology, Oncology, General Practice, Emergency Medicine

Rules:
- If emergency red flags are present, use status=emergency and specialty=Emergency Medicine.
- Ask follow-up questions when key information is missing: duration, severity, body location, associated symptoms, triggers, pregnancy status when relevant.
- Ask at most one question at a time.
- Do not recommend General Practice unless the presentation is broad, nonspecific, or still unclear after clarifying.
- Keep tone professional, clear, and brief."""

_DURATION_PATTERN = re.compile(
    r"\b(today|yesterday|tonight|this morning|hours?|days?|weeks?|months?|years?|since|for \d+|started)\b"
)
_SEVERITY_PATTERN = re.compile(
    r"\b(mild|moderate|severe|worst|pain scale|8/10|9/10|10/10|worsening|constant|comes and goes|intermittent)\b"
)
_LOCATION_PATTERN = re.compile(
    r"\b(head|chest|arm|leg|back|knee|shoulder|hip|eye|ear|throat|stomach|abdomen|side|flank|pelvic|skin|face|neck)\b"
)


async def _openai_triage(symptoms: str) -> dict | None:
    """Call GPT-4o-mini for specialty triage. Returns parsed dict or None on any failure."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-proj-YOUR"):
        return None
    try:
        from openai import AsyncOpenAI  # lazy import — same pattern as transcriber.py
        client = AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": f"Patient symptoms: {symptoms}"},
            ],
            max_tokens=300,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "{}").strip()
        data = json.loads(raw)
        specialty = data.get("specialty", "")
        if specialty not in _SPECIALTIES:
            logger.warning("OpenAI returned unrecognised specialty %r — falling back to rules", specialty)
            return None
        return data
    except Exception as exc:
        logger.warning("OpenAI triage error (%s) — falling back to keyword rules", exc)
        return None


async def _openai_triage_chat(history: list[dict[str, str]], conversation_text: str) -> dict | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-proj-YOUR"):
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        messages = [{"role": "system", "content": _CHAT_PROMPT}]
        messages.extend(history[-8:])
        messages.append({"role": "user", "content": f"Conversation summary input: {conversation_text}"})
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=450,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "{}").strip()
        data = json.loads(raw)
        if data.get("status") not in {"follow_up", "recommendation", "emergency"}:
            return None
        specialty = data.get("recommended_specialty")
        if specialty and specialty not in _SPECIALTIES + ["Emergency Medicine"]:
            return None
        return data
    except Exception as exc:
        logger.warning("OpenAI conversational triage error (%s) — falling back to rules", exc)
        return None


def _build_conversation_text(history: list[str], latest_message: str) -> str:
    pieces = [item.strip() for item in history if item.strip()]
    if latest_message.strip():
        pieces.append(latest_message.strip())
    return " ".join(pieces).strip()


def _suggested_replies_for_question(question: str) -> list[str]:
    lower = question.lower()
    if "how long" in lower or "when did" in lower:
        return ["Started today", "A few days ago", "More than a week"]
    if "how severe" in lower or "pain" in lower:
        return ["Mild", "Moderate", "Severe"]
    if "where" in lower or "which side" in lower:
        return ["Left side", "Right side", "Center", "It moves around"]
    if "breathing" in lower:
        return ["Only with activity", "Even at rest", "With cough/wheezing"]
    return []


def _fallback_follow_up_question(symptoms: str, specialty: str, confidence: float | None, turn_count: int) -> str | None:
    normalized = symptoms.lower()
    if turn_count >= 3 and (confidence or 0) < 0.72:
        return None
    if not _DURATION_PATTERN.search(normalized):
        return "How long have these symptoms been going on, and did they start suddenly or gradually?"
    if not _SEVERITY_PATTERN.search(normalized):
        return "How severe are the symptoms right now, and are they getting worse, staying the same, or coming and going?"
    if specialty in {"Neurology", "Orthopedics", "ENT", "Ophthalmology", "Gastroenterology", "Dermatology", "Gynecology", "Urology", "Nephrology"} and not _LOCATION_PATTERN.search(normalized):
        return "Where in your body are you feeling this most, and is it on one side or both?"
    if specialty == "Cardiology" and "shortness of breath" not in normalized and "palpitations" not in normalized:
        return "Are you also having shortness of breath, dizziness, fainting, or pain spreading to your arm, back, or jaw?"
    if specialty == "Pulmonology" and "fever" not in normalized and "wheez" not in normalized:
        return "Do you also have fever, wheezing, chest tightness, or trouble breathing at rest?"
    if specialty == "Gastroenterology" and "vomit" not in normalized and "diarr" not in normalized and "constipation" not in normalized:
        return "Are you also having nausea, vomiting, diarrhea, constipation, heartburn, or blood in your stool?"
    return None


def _fallback_triage_chat(history: list[str], latest_message: str) -> TriageChatResponse:
    conversation_text = _build_conversation_text(history, latest_message)
    escalation = detect_red_flag_escalation(conversation_text)
    if escalation.escalation_required:
        return TriageChatResponse(
            status="emergency",
            message=escalation.escalation_reason,
            recommended_specialty="Emergency Medicine",
            rationale=escalation.escalation_reason,
            extracted_symptom_cues=escalation.matched_red_flags,
            confidence=0.99,
            conversation_summary=conversation_text,
        )

    result = map_symptom_to_specialty(SymptomInput(symptom=conversation_text))
    follow_up_question = _fallback_follow_up_question(
        conversation_text,
        result.specialty,
        result.confidence,
        turn_count=max(1, len(history) + 1),
    )
    if follow_up_question:
        return TriageChatResponse(
            status="follow_up",
            message="I want to narrow this down before suggesting the best specialist.",
            follow_up_question=follow_up_question,
            suggested_replies=_suggested_replies_for_question(follow_up_question),
            extracted_symptom_cues=result.matched_cues,
            confidence=result.confidence,
            conversation_summary=conversation_text,
        )

    specialty = result.specialty if (result.confidence or 0) >= 0.6 else "General Practice"
    rationale = result.rationale
    if specialty == "General Practice" and (result.confidence or 0) < 0.6:
        rationale = (
            "Your symptoms are still somewhat broad or nonspecific from the information provided. "
            "A general practice clinician is the safest first step and can redirect you if needed."
        )

    return TriageChatResponse(
        status="recommendation",
        message=f"Based on what you've shared, the best starting point appears to be **{specialty}**.",
        recommended_specialty=specialty,
        rationale=rationale,
        extracted_symptom_cues=result.matched_cues,
        confidence=result.confidence,
        conversation_summary=conversation_text,
    )


@router.post("/analyze", response_model=TriageResponse, dependencies=[Depends(require_role("patient"))])
async def analyze_symptoms(request: SymptomRequest):
    """
    AI Care Navigator — tries GPT-4o-mini first, falls back to rule-based keyword mapper.
    """
    check_text = request.symptoms
    if request.red_flag_context:
        check_text = f"{request.symptoms} {request.red_flag_context}"

    # 1. Emergency escalation — always runs first
    escalation = detect_red_flag_escalation(check_text)
    if escalation.escalation_required:
        return TriageResponse(
            recommended_specialty="Emergency Medicine",
            department="Navigation",
            rationale=escalation.escalation_reason,
            extracted_symptom_cues=escalation.matched_red_flags,
            confidence=0.99,
        )

    # 2. GPT-4o-mini triage (when OPENAI_API_KEY is set)
    openai_result = await _openai_triage(request.symptoms)
    if openai_result:
        return TriageResponse(
            recommended_specialty=openai_result["specialty"],
            department="Navigation",
            rationale=openai_result.get(
                "rationale",
                "Based on your symptoms, this specialist is best positioned to help."
            ),
            extracted_symptom_cues=[],
            confidence=float(openai_result.get("confidence", 0.80)),
        )

    # 3. Keyword-based fallback (no API key or OpenAI unavailable)
    result = map_symptom_to_specialty(SymptomInput(symptom=request.symptoms))
    return TriageResponse(
        recommended_specialty=result.specialty,
        department=result.department,
        rationale=result.rationale,
        extracted_symptom_cues=result.matched_cues,
        confidence=result.confidence,
    )


@router.post("/chat", response_model=TriageChatResponse, dependencies=[Depends(require_role("patient"))])
async def triage_chat(request: TriageChatRequest):
    user_history = [item.text for item in request.history if item.role == "user" and item.text.strip()]
    conversation_text = _build_conversation_text(user_history, request.message)

    escalation = detect_red_flag_escalation(conversation_text)
    if escalation.escalation_required:
        return TriageChatResponse(
            status="emergency",
            message=escalation.escalation_reason,
            recommended_specialty="Emergency Medicine",
            rationale=escalation.escalation_reason,
            extracted_symptom_cues=escalation.matched_red_flags,
            confidence=0.99,
            conversation_summary=conversation_text,
        )

    openai_result = await _openai_triage_chat(
        history=[{"role": item.role, "content": item.text} for item in request.history if item.text.strip()],
        conversation_text=conversation_text,
    )
    if openai_result:
        return TriageChatResponse(
            status=openai_result["status"],
            message=openai_result.get("message") or "",
            recommended_specialty=openai_result.get("recommended_specialty"),
            rationale=openai_result.get("rationale"),
            extracted_symptom_cues=[],
            confidence=float(openai_result["confidence"]) if openai_result.get("confidence") is not None else None,
            follow_up_question=openai_result.get("follow_up_question"),
            suggested_replies=openai_result.get("suggested_replies") or [],
            conversation_summary=openai_result.get("conversation_summary") or conversation_text,
        )

    return _fallback_triage_chat(user_history, request.message)
