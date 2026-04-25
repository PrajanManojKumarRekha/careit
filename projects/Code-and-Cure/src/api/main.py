from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routes (We will build these next)
# from src.api.routes import auth, symptoms, doctors, appointments, soap, fhir

app = FastAPI(
    title="CareIT Telehealth API",
    description="Backend API for doctor discovery and telehealth documentation",
    version="0.1.0"
)

# --- CORS CONFIGURATION ---
# Necessary for the Next.js frontend (localhost:3000) to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "CareIT API Gateway is active",
        "version": "0.1.0"
    }

# --- ROUTER INCLUSIONS ---
# These will be enabled as we implement each module
# app.include_router(auth.router, prefix="/auth", tags=["Auth"])
# app.include_router(symptoms.router, prefix="/symptoms", tags=["Intake"])
# app.include_router(doctors.router, prefix="/doctors", tags=["Discovery"])
