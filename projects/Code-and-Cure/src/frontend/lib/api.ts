function resolveApiBaseUrl(): string {
  const configuredBase = (
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    ""
  ).trim();

  if (configuredBase) {
    return configuredBase
      .replace("http://localhost:8000", "http://127.0.0.1:8000")
      .replace("https://localhost:8000", "https://127.0.0.1:8000")
      .replace(/\/$/, "");
  }

  if (typeof window !== "undefined") {
    const localHosts = new Set(["localhost", "127.0.0.1"]);
    const host = localHosts.has(window.location.hostname) ? "127.0.0.1" : window.location.hostname;
    return `${window.location.protocol}//${host}:8000`;
  }

  return "http://127.0.0.1:8000";
}

export const API_BASE_URL = resolveApiBaseUrl();
const BROWSER_TOKEN_KEY = "careit_access_token";

type AccessTokenProvider = () => Promise<string | null> | string | null;

let accessTokenProvider: AccessTokenProvider | null = null;
let storedAccessToken: string | null = null;

export function setAccessTokenProvider(provider: AccessTokenProvider | null) {
  accessTokenProvider = provider;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getStoredToken(): Promise<string | null> {
  if (accessTokenProvider) {
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const token = await accessTokenProvider();
      const normalized = token?.trim() || null;
      if (normalized) {
        storedAccessToken = normalized;
        return normalized;
      }
      if (attempt < 4) {
        await sleep(150);
      }
    }
  }
  if (typeof window !== "undefined") {
    const persisted = window.localStorage.getItem(BROWSER_TOKEN_KEY)?.trim() || null;
    if (persisted) {
      storedAccessToken = persisted;
      return persisted;
    }
  }
  return storedAccessToken;
}

function formatErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => {
        if (typeof entry === "string") return entry;
        if (entry && typeof entry === "object") {
          const obj = entry as { msg?: unknown; loc?: unknown };
          const msg = typeof obj.msg === "string" ? obj.msg : null;
          const loc = Array.isArray(obj.loc) ? obj.loc.join(".") : null;
          if (msg && loc) return `${loc}: ${msg}`;
          if (msg) return msg;
        }
        return null;
      })
      .filter((value): value is string => Boolean(value));
    if (messages.length) return messages.join("; ");
  }
  if (detail && typeof detail === "object") {
    const obj = detail as { message?: unknown; detail?: unknown; error?: unknown };
    if (typeof obj.message === "string" && obj.message.trim()) return obj.message;
    if (typeof obj.error === "string" && obj.error.trim()) return obj.error;
  }
  return fallback;
}

// Standard JSON fetch with Authorization header
async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: "include" });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `Unable to reach the API at ${API_BASE_URL}. Check NEXT_PUBLIC_API_BASE_URL/NEXT_PUBLIC_API_URL, the backend server, and CORS settings.`
      );
    }
    throw error;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(formatErrorDetail(err.detail, `HTTP ${res.status}`));
  }
  return res.json();
}

// Multipart form-data upload — do NOT set Content-Type; browser adds boundary
async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const token = await getStoredToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers,
      credentials: "include",
      body: formData,
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `Unable to reach the API at ${API_BASE_URL}. Check NEXT_PUBLIC_API_BASE_URL/NEXT_PUBLIC_API_URL, the backend server, and CORS settings.`
      );
    }
    throw error;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(formatErrorDetail(err.detail, `HTTP ${res.status}`));
  }
  return res.json();
}

export function setStoredToken(token: string | null) {
  storedAccessToken = token?.trim() || null;
  if (typeof window !== "undefined") {
    if (storedAccessToken) {
      window.localStorage.setItem(BROWSER_TOKEN_KEY, storedAccessToken);
    } else {
      window.localStorage.removeItem(BROWSER_TOKEN_KEY);
    }
  }
}

export function clearStoredToken() {
  storedAccessToken = null;
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(BROWSER_TOKEN_KEY);
  }
}

// ---- Types ----
export interface AuthResponse {
  access_token?: string | null;
  status?: string;
  user_id?: string;
  role: string;
  email?: string;
  full_name?: string;
  message?: string | null;
}

export interface Doctor {
  id: string;
  name: string;
  specialty: string;
  location: string;
  rating: number;
  review_count: number;
  lat?: number | null;
  lng?: number | null;
  distance_miles?: number | null;
}

export interface AppointmentSlot {
  id: string;
  doctor_id: string;
  start_time: string;
  is_available: boolean;
}

export interface Appointment {
  id: string;
  patient_id: string;
  doctor_id: string;
  scheduled_at: string;
  status: string;
  workflow_status?: string;
  notes?: string | null;
  meeting_link?: string | null;
}

export interface TriageResponse {
  recommended_specialty: string;
  department: string;
  rationale: string;
  extracted_symptom_cues: string[];
  confidence: number | null;
}

export interface TriageChatMessage {
  role: "user" | "assistant";
  text: string;
}

export interface TriageChatResponse {
  status: "follow_up" | "recommendation" | "emergency";
  message: string;
  recommended_specialty?: string | null;
  rationale?: string | null;
  extracted_symptom_cues: string[];
  confidence: number | null;
  follow_up_question?: string | null;
  suggested_replies: string[];
  conversation_summary?: string | null;
}

export interface SOAPNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface TranscriptChunkResponse {
  appointment_id: string;
  transcript_so_far: string;
  soap_draft: SOAPNote;
  is_updated: boolean;
}

export interface EHRExportResponse {
  export_id: string;
  status: string;
  fhir_bundle: Record<string, unknown>;
  submission_timestamp: string;
}

export interface EMRHandoffResponse {
  submission_id: string;
  target_emr: string;
  status: string;
  fhir_bundle_id: string;
  payload_hash: string;
  submitted_at: string;
  acknowledged_at: string | null;
  simulated_response: Record<string, unknown>;
}

export interface SOAPDraftMeta {
  derived_from_transcript: boolean;
  transcript_chars_processed: number;
  update_timestamp: string;
  chunk_index: number;
  quality_hint: "minimal" | "partial" | "sufficient";
  change_summary: string;
}

export interface SOAPDraftWithMeta {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  metadata: SOAPDraftMeta;
}

export interface SessionStartResponse {
  session_id: string;
  appointment_id: string;
  status: string;
  provider_mode: string;
  language: string;
  created_at: string;
}

export interface SessionChunkResponse {
  session_id: string;
  appointment_id: string;
  chunk_index: number;
  transcript_so_far: string;
  soap_draft: SOAPDraftWithMeta;
  provider_status: string;
  session_status: string;
}

export interface SessionStateResponse {
  session_id: string;
  appointment_id: string;
  status: string;
  transcript: string;
  last_chunk_index: number;
  soap_draft: SOAPDraftWithMeta | null;
  provider_mode: string;
  language: string;
  created_at: string;
  updated_at: string;
}

export interface SessionFinalizeResponse {
  session_id: string;
  appointment_id: string;
  status: string;
  transcript: string;
  final_soap: SOAPDraftWithMeta;
  handoff_ready: boolean;
  message: string;
}

export interface TranscribeUploadResponse {
  appointment_id: string;
  transcript: string;
  soap_draft: SOAPDraftWithMeta;
  transcription_provider: string;
  language_detected: string;
  duration_seconds: number | null;
  file_info: { filename: string; size_mb: number; content_type: string };
  warning: string | null;
}

export interface IntakeForm {
  appointment_id: string;
  symptoms: string;
  medical_history?: string | null;
  medications?: string | null;
  allergies?: string | null;
  patient_id?: string;
}

export interface Prescription {
  id: string;
  appointment_id: string;
  patient_id: string;
  doctor_id: string;
  requested_medication: string;
  approval_status: string;
  block_reason?: string | null;
  created_at?: string;
}

// ---- API surface ----
export const api = {
  auth: {
    syncSession: () =>
      apiFetch<AuthResponse>("/api/v1/auth/session", {
        method: "POST",
        body: JSON.stringify({}),
      }),
    me: () =>
      apiFetch<AuthResponse>("/api/v1/auth/me"),
    logout: () =>
      apiFetch<{ status: string }>("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({}),
      }),
    demoLogin: (role: "patient" | "doctor") =>
      apiFetch<AuthResponse>("/api/v1/auth/demo-login", {
        method: "POST",
        body: JSON.stringify({ role }),
      }),
  },

  symptoms: {
    analyze: (symptoms: string, red_flag_context?: string) =>
      apiFetch<TriageResponse>("/api/v1/symptoms/analyze", {
        method: "POST",
        body: JSON.stringify({ symptoms, red_flag_context }),
      }),
    chat: (message: string, history: TriageChatMessage[]) =>
      apiFetch<TriageChatResponse>("/api/v1/symptoms/chat", {
        method: "POST",
        body: JSON.stringify({ message, history }),
      }),
  },

  doctors: {
    list: (params?: {
      specialty?: string;
      q?: string;
      location?: string;
      latitude?: number;
      longitude?: number;
      radius?: number;
      source?: "auto" | "db" | "live";
    }) => {
      const qs = new URLSearchParams();
      if (params?.specialty) qs.set("specialty", params.specialty);
      if (params?.q) qs.set("q", params.q);
      if (params?.location) qs.set("location", params.location);
      if (params?.latitude !== undefined) qs.set("latitude", String(params.latitude));
      if (params?.longitude !== undefined) qs.set("longitude", String(params.longitude));
      if (params?.radius !== undefined) qs.set("radius", String(params.radius));
      if (params?.source) qs.set("source", params.source);
      const queryString = qs.toString();
      return apiFetch<Doctor[]>(`/api/v1/doctors/${queryString ? `?${queryString}` : ""}`);
    },
    slots: (doctorId: string) =>
      apiFetch<AppointmentSlot[]>(`/api/v1/doctors/${doctorId}/slots`),
  },

  appointments: {
    book: (doctor_id: string, scheduled_at: string) =>
      apiFetch<{ appointment_id: string; status: string; booking: Appointment }>(
        "/api/v1/appointments/",
        {
          method: "POST",
          body: JSON.stringify({ doctor_id, scheduled_at }),
        }
      ),
    list: () => apiFetch<Appointment[]>("/api/v1/appointments/"),
    get: (appointment_id: string) =>
      apiFetch<Appointment>(`/api/v1/appointments/${appointment_id}`),
    cancel: (appointment_id: string) =>
      apiFetch<{ appointment_id: string; status: string; message: string }>(
        `/api/v1/appointments/${appointment_id}/cancel`,
        { method: "PATCH" }
      ),
    reschedule: (appointment_id: string, new_scheduled_at: string) =>
      apiFetch<{ appointment_id: string; scheduled_at: string; status: string; message: string }>(
        `/api/v1/appointments/${appointment_id}/reschedule`,
        {
          method: "PATCH",
          body: JSON.stringify({ new_scheduled_at }),
        }
      ),
    updateMeetingLink: (appointment_id: string, meeting_link: string | null) =>
      apiFetch<{ appointment_id: string; meeting_link: string | null; message: string; booking: Appointment }>(
        `/api/v1/appointments/${appointment_id}/meeting-link`,
        {
          method: "PATCH",
          body: JSON.stringify({ meeting_link }),
        }
      ),
  },

  intake: {
    get: (appointmentId: string) =>
      apiFetch<IntakeForm>(`/api/v1/intake/${appointmentId}`),
    submit: (form: IntakeForm) =>
      apiFetch("/api/v1/intake/", {
        method: "POST",
        body: JSON.stringify(form),
      }),
  },

  soap: {
    sendChunk: (appointment_id: string, chunk: string) =>
      apiFetch<TranscriptChunkResponse>("/api/v1/soap/transcript", {
        method: "POST",
        body: JSON.stringify({ appointment_id, chunk }),
      }),
    approve: (appointment_id: string, edited_note: SOAPNote) =>
      apiFetch<{ status: string; note_id: string; approved_at: string }>(
        "/api/v1/soap/approve",
        {
          method: "PATCH",
          body: JSON.stringify({ appointment_id, edited_note }),
        }
      ),
    transcribeUpload: (appointmentId: string, file: File, language = "en") => {
      const formData = new FormData();
      formData.append("appointment_id", appointmentId);
      formData.append("language", language);
      formData.append("file", file);
      return apiUpload<TranscribeUploadResponse>("/api/v1/soap/transcribe-upload", formData);
    },
    generate: (transcript: string) =>
      apiFetch<SOAPNote>("/api/v1/soap/generate", {
        method: "POST",
        body: JSON.stringify({ transcript }),
      }),
    downloadDocument: async (appointmentId: string) => {
      const token = await getStoredToken();
      let res: Response;
      try {
        res = await fetch(`${API_BASE_URL}/api/v1/soap/${appointmentId}/document/download`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          credentials: "include",
        });
      } catch (error) {
        if (error instanceof TypeError) {
          throw new Error(
            `Unable to reach the API at ${API_BASE_URL}. Check NEXT_PUBLIC_API_BASE_URL/NEXT_PUBLIC_API_URL, the backend server, and CORS settings.`
          );
        }
        throw error;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Failed to download SOAP document");
      }
      return res.blob();
    },
    reuploadDocument: (appointmentId: string, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiUpload<{ status: string; message: string }>(
        `/api/v1/soap/${appointmentId}/document/reupload`,
        formData
      );
    },
    emailDocument: (appointmentId: string, targetEmail: string) => {
      const formData = new FormData();
      formData.append("target_email", targetEmail);
      return apiUpload<{ status: string; message: string; target_email: string }>(
        `/api/v1/soap/${appointmentId}/document/email`,
        formData
      );
    },
  },

  fhir: {
    export: (appointmentId: string) =>
      apiFetch<EHRExportResponse>(`/api/v1/fhir/export/${appointmentId}`),
    submit: (appointmentId: string) =>
      apiFetch<EMRHandoffResponse>(`/api/v1/fhir/submit/${appointmentId}`, {
        method: "POST",
      }),
  },

  session: {
    start: (appointment_id: string, language = "en") =>
      apiFetch<SessionStartResponse>("/api/v1/soap/session/start", {
        method: "POST",
        body: JSON.stringify({ appointment_id, language, source_language: language, target_language: language }),
      }),
    sendChunk: (session_id: string, appointment_id: string, chunk_index: number, transcript_chunk: string) =>
      apiFetch<SessionChunkResponse>(`/api/v1/soap/session/${session_id}/chunk`, {
        method: "POST",
        body: JSON.stringify({ appointment_id, chunk_index, transcript_chunk }),
      }),
    getState: (session_id: string) =>
      apiFetch<SessionStateResponse>(`/api/v1/soap/session/${session_id}/state`),
    finalize: (session_id: string) =>
      apiFetch<SessionFinalizeResponse>(`/api/v1/soap/session/${session_id}/finalize`, {
        method: "POST",
      }),
  },
  prescriptions: {
    list: () => apiFetch<Prescription[]>("/api/v1/prescriptions/"),
    create: (appointment_id: string, medication_name: string) =>
      apiFetch<Prescription>("/api/v1/prescriptions/", {
        method: "POST",
        body: JSON.stringify({ appointment_id, medication_name }),
      }),
    remove: (prescription_id: string) =>
      apiFetch<{ status: string; message: string; prescription_id: string }>(
        `/api/v1/prescriptions/${prescription_id}`,
        { method: "DELETE" }
      ),
  },
};
