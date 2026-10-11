# CareIT

CareIT is a telehealth workflow and FHIR R4 interoperability prototype for independent practitioners. It takes a patient from symptom intake and specialist discovery through booking, clinician-reviewed SOAP documentation, and an exportable FHIR bundle.

This repository is the operational source of truth for the project. The documented local and self-hosted paths below are deliberately independent of a particular hosted demo: if a Vercel or Render deployment disappears, a new developer can clone this repository, configure replacement services, and run or redeploy CareIT.

> **Clinical boundary:** CareIT is not an EMR and does not diagnose, prescribe autonomously, or provide production EMR connectivity. Clinicians review and approve SOAP notes before export; controlled-substance prescriptions are blocked.

## What is included

- Patient symptom intake with specialty suggestions
- Practitioner discovery using OpenStreetMap, with embedded/seeded fallbacks
- Patient booking and clinician appointment workflows
- Transcript-to-SOAP drafting with clinician approval
- Deterministic FHIR R4 bundle generation (`Consent`, `Composition`, and optional `MedicationRequest`)
- Clerk authentication with Supabase-backed user and clinical-workflow records

## Repository map

The deployable application lives under `projects/Code-and-Cure`.

```text
.
├── README.md
├── requirements.txt                     # Root Python dependency snapshot
└── projects/Code-and-Cure/
    ├── src/api/                         # FastAPI gateway
    ├── src/core_logic/                  # Testable Python domain logic
    ├── src/database/                    # Supabase schema and access helpers
    ├── src/frontend/                    # Next.js / TypeScript interface
    ├── scripts/                         # Database migrations and test runner
    ├── .env.example                     # API environment template
    ├── DEPLOYMENT.md                    # Render / Vercel configuration reference
    ├── Dockerfile.api                   # API production image
    └── render.yaml                      # Render Blueprint
```

## Architecture

| Component | Technology | Responsibility |
|---|---|---|
| Web app | Next.js 14, React, TypeScript, Tailwind | Patient and clinician experience |
| API | FastAPI, Pydantic | Authentication, workflow orchestration, HTTP endpoints |
| Domain logic | Python | Triage, SOAP parsing, FHIR serialization, safety rules |
| Persistence | Supabase / PostgreSQL | Users, appointments, notes, audit data |
| Identity | Clerk | Production identity, session management, and role provisioning |

The API exposes `/healthz` for health checks and versioned endpoints under `/api/v1`.

## Fast local setup

### Prerequisites

- Git
- Python 3.12+
- Node.js 20+ and npm
- A Supabase project for persistence (or an already-provisioned project)
- Docker Desktop only if you are building container images

### 1. Clone and enter the application

```bash
git clone https://github.com/PrajanManojKumarRekha/CareIT.git
cd CareIT/projects/Code-and-Cure
```

### 2. Configure the API

Create the local API configuration from the committed template. Do not commit the resulting `.env` file.

```bash
cp .env.example .env
```

For local development, set real values for `SUPABASE_URL`, `SUPABASE_KEY`, `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, and `CLERK_JWT_ISSUER`. Keep `APP_ENV=development`. Clerk owns password and email-verification flows; the API mirrors authenticated users into Supabase.

If the checkout is stored in OneDrive, retain `ALLOW_ONEDRIVE_DOTENV=true` locally. In production, set `ALLOW_DOTENV=false` and `ALLOW_ONEDRIVE_DOTENV=false`, then configure secrets in the hosting platform rather than in a synced `.env` file.

Before using an existing Supabase project with the hardened authentication flow, apply the checked-in migration:

```bash
# Run this in the Supabase SQL editor or with your approved PostgreSQL migration workflow.
scripts/auth_hardening.sql
```

### 3. Install and start the API

```bash
python3 -m venv .venv
source .venv/bin/activate                 # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python3 -m pip install --upgrade pip
python3 -m pip install -r src/api/requirements.txt
python3 -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Confirm the service is live:

```bash
curl http://127.0.0.1:8000/healthz
```

Expected response: `{"status":"ok"}`.

### 4. Configure and start the frontend

In a second terminal:

```bash
cd CareIT/projects/Code-and-Cure/src/frontend
cp .env.example .env.local
npm ci
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` and a real `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` in `src/frontend/.env.local`.

Open [http://localhost:3000](http://localhost:3000). The frontend expects the API to be available on port 8000.

## End-to-end validation runbook

Use two real Clerk accounts: a self-registered patient and a clinic-provisioned doctor with a verified clinician profile in Supabase.

1. Start the API and frontend using the local setup above.
2. Confirm `GET /healthz` returns `{"status":"ok"}`.
3. Sign in as the patient and submit a symptom description.
4. Accept or change the suggested specialty, select a practitioner, and book a slot.
5. Sign in as the assigned doctor and open the appointment.
6. Use **Paste Transcript** rather than live transcription, generate a SOAP draft, review it, and approve it.
7. Export the resulting FHIR bundle and show the `Consent` and `Composition` resources.

Resilience built into the workflow:

- If speech providers are unavailable, use manual transcript input.
- If public OpenStreetMap lookups are unavailable, the application uses its embedded/seeded practitioner fallback.
- Clerk email delivery and verification must be configured in the Clerk dashboard before production validation.

Never present the synthetic FHIR acknowledgement as a live EMR submission.

## Quality checks

Run these from `projects/Code-and-Cure` before a deployment:

```bash
# Backend and core logic checks
python3 -m pytest src/core_logic/test_logic.py src/core_logic/test_stream_session.py src/api/test_security_integration.py

# Frontend production build
cd src/frontend
npm run build
```

On macOS/Linux, the repository also provides `scripts/run_tests.sh` to run both steps.

## Hosting and recovery

The application can be hosted as two services:

| Service | Current hosted target | Source directory |
|---|---|---|
| Frontend | Vercel | `projects/Code-and-Cure/src/frontend` |
| API | Render | `projects/Code-and-Cure` |

Detailed platform configuration lives in [projects/Code-and-Cure/DEPLOYMENT.md](projects/Code-and-Cure/DEPLOYMENT.md), and the API has a Render Blueprint at [projects/Code-and-Cure/render.yaml](projects/Code-and-Cure/render.yaml). Treat these files and the environment templates as the recovery checklist—not the state of a particular deployment.

### Recreate a hosted environment

1. Provision a Supabase project and apply the database schema/migrations used by the application.
2. Provision a Clerk application and create the `careit-api` token template if Clerk authentication is required.
3. Deploy the API from `projects/Code-and-Cure` using `render.yaml`, or run `Dockerfile.api` on any container host.
4. Set the production API environment variables from `.env.example` and `DEPLOYMENT.md`. Use real secrets; do not copy placeholder values.
5. Deploy the frontend from `src/frontend` and set `NEXT_PUBLIC_API_BASE_URL` to the public API URL **at build time**.
6. Set API `CORS_ORIGINS` and `ALLOWED_HOSTS` to the deployed frontend and API hostnames.
7. Visit `/healthz`, open the frontend, and complete the end-to-end validation runbook before sharing the URL.

Production startup validates required secrets, CORS, cookie security, and allowed hosts. That failure is intentional: correct the configuration rather than bypassing the validation.

### Self-hosting notes

`Dockerfile.api` builds the FastAPI service. For the frontend Docker image, build with `NEXT_OUTPUT_MODE=standalone`, because the frontend Dockerfile copies Next.js standalone output:

```bash
cd projects/Code-and-Cure/src/frontend
NEXT_OUTPUT_MODE=standalone docker build -t careit-frontend .
```

Keep the API, frontend, database, and identity configuration in separate managed services. Back up Supabase data and record the deployed environment-variable names in your password manager or secret-management system; never place production secrets in Git or OneDrive.

## Required configuration overview

| Area | Key variables |
|---|---|
| API/runtime | `APP_ENV`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `ALLOWED_HOSTS` |
| Database | `SUPABASE_URL`, `SUPABASE_KEY` |
| Clerk | `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, `CLERK_JWT_ISSUER`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` |
| Frontend/API connection | `NEXT_PUBLIC_API_BASE_URL` |
| Email | `AUTH_EMAIL_DELIVERY_MODE`, `AUTH_EMAIL_FROM`, SMTP variables |
| Transcription (optional) | `ELEVENLABS_API_KEY`, `GROQ_API_KEY` |

Refer to the two `.env.example` files for the complete supported set and safe local defaults.

## Guardrails

- Keep patient data and all secrets out of version control.
- Require clinician review before any FHIR export.
- Do not claim the synthetic FHIR handoff is a live vendor integration.
- Validate a replacement host with the runbook before retiring an existing deployment.
