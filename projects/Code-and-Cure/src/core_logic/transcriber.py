"""Audio/video transcription provider with provider fallback.

Priority chain:
  1. ElevenLabs Speech API   — if ELEVENLABS_API_KEY env var is set
  2. OpenAI Whisper API      — if OPENAI_API_KEY env var is set
  3. Local openai-whisper    — if openai-whisper package is installed (CPU, slower)
  4. TranscriptionError      — structured error; caller degrades to manual transcript input

No medical content is fabricated. Transcription returns the raw speech content
exactly as the provider produces it — no summarisation or inference applied here.
"""

import io
import os
import tempfile
from dataclasses import dataclass
import httpx

# Max file size for OpenAI Whisper API (25 MB hard limit)
WHISPER_API_MAX_BYTES = 25 * 1024 * 1024

SUPPORTED_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4a", ".mp3", ".wav", ".ogg", ".oga"}
SUPPORTED_CONTENT_TYPES = {
    "video/mp4", "video/webm", "video/quicktime",
    "audio/mpeg", "audio/mp4", "audio/x-m4a",
    "audio/wav", "audio/wave", "audio/x-wav",
    "audio/webm", "audio/ogg", "application/ogg",
}

# Module-level cache so local Whisper model is not re-loaded on every call
_local_whisper_model = None


@dataclass
class TranscriptionResult:
    transcript: str
    provider: str          # "openai_whisper_api" | "elevenlabs_speech_api" | "local_whisper"
    language_detected: str
    duration_seconds: float | None


class TranscriptionError(Exception):
    """Raised when no transcription provider can produce a result."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "recording.mp4",
    language: str | None = None,
) -> TranscriptionResult:
    """
    Transcribe raw audio/video bytes to text.

    Tries providers in priority order. If all fail, raises TranscriptionError
    so the API layer can return a structured HTTP error instead of a 500.

    Args:
        audio_bytes: Raw binary content of the uploaded file.
        filename:    Original filename (used to infer format).
        language:    ISO-639-1 hint (e.g. "en", "es"). None = auto-detect.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    _last_errors: list[str] = []

    if elevenlabs_api_key:
        try:
            return _transcribe_elevenlabs_api(audio_bytes, filename, language, elevenlabs_api_key)
        except Exception as exc:
            # If the API call itself fails (network, quota, etc.) fall through
            # to other providers rather than crashing the request.
            _last_errors.append(f"ElevenLabs: {exc}")
    else:
        _last_errors.append("ElevenLabs: ELEVENLABS_API_KEY not set")

    if openai_api_key:
        try:
            return _transcribe_openai_api(audio_bytes, filename, language, openai_api_key)
        except Exception as exc:
            _last_errors.append(f"OpenAI: {exc}")
    else:
        _last_errors.append("OpenAI: OPENAI_API_KEY not set")

    # Local Whisper fallback
    try:
        return _transcribe_local_whisper(audio_bytes, filename, language)
    except ImportError:
        _last_errors.append("Local Whisper: openai-whisper package not installed")
    except Exception as exc:
        _last_errors.append(f"Local Whisper: {exc}")

    raise TranscriptionError(
        code="TRANSCRIPTION_PROVIDER_UNAVAILABLE",
        message="No transcription provider available. Provider statuses: " + " | ".join(_last_errors),
    )


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _transcribe_openai_api(
    audio_bytes: bytes,
    filename: str,
    language: str | None,
    api_key: str,
) -> TranscriptionResult:
    from openai import OpenAI  # type: ignore[import]

    client = OpenAI(api_key=api_key)

    # BytesIO wrapper — openai SDK reads .name to infer content type
    buf = io.BytesIO(audio_bytes)
    buf.name = filename

    kwargs: dict = {"model": "whisper-1", "file": buf, "response_format": "verbose_json"}
    if language:
        kwargs["language"] = language

    response = client.audio.transcriptions.create(**kwargs)

    return TranscriptionResult(
        transcript=response.text.strip(),
        provider="openai_whisper_api",
        language_detected=getattr(response, "language", language or "en"),
        duration_seconds=getattr(response, "duration", None),
    )


def _transcribe_elevenlabs_api(
    audio_bytes: bytes,
    filename: str,
    language: str | None,
    api_key: str,
) -> TranscriptionResult:
    # ElevenLabs speech endpoint accepts multipart upload and returns JSON.
    # We keep parsing defensive because response shape can vary by model/version.
    with httpx.Client(timeout=120.0) as client:
        files = {"file": (filename, audio_bytes)}
        data = {"model_id": "scribe_v1"}
        if language:
            data["language_code"] = language

        response = client.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": api_key},
            files=files,
            data=data,
        )
        response.raise_for_status()
        payload = response.json()

    transcript = (
        payload.get("text")
        or payload.get("transcript")
        or payload.get("raw_text")
        or ""
    ).strip()
    if not transcript:
        raise TranscriptionError(
            code="ELEVENLABS_EMPTY_TRANSCRIPT",
            message="ElevenLabs returned no transcript text.",
        )

    detected_language = (
        payload.get("language_code")
        or payload.get("language")
        or language
        or "en"
    )
    duration = payload.get("duration") or payload.get("audio_duration")
    try:
        duration_seconds = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_seconds = None

    return TranscriptionResult(
        transcript=transcript,
        provider="elevenlabs_speech_api",
        language_detected=detected_language,
        duration_seconds=duration_seconds,
    )


def _transcribe_local_whisper(
    audio_bytes: bytes,
    filename: str,
    language: str | None,
) -> TranscriptionResult:
    global _local_whisper_model

    import whisper  # type: ignore[import]  # openai-whisper package

    # Load model once and cache at module level
    if _local_whisper_model is None:
        _local_whisper_model = whisper.load_model("base")

    import os as _os
    suffix = _os.path.splitext(filename)[1].lower() or ".mp4"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        options: dict = {}
        if language:
            options["language"] = language
        result = _local_whisper_model.transcribe(tmp_path, **options)
    finally:
        _os.unlink(tmp_path)

    return TranscriptionResult(
        transcript=result["text"].strip(),
        provider="local_whisper",
        language_detected=result.get("language", language or "en"),
        duration_seconds=None,
    )
