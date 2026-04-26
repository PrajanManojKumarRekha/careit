from fastapi import APIRouter, HTTPException, Response, Depends
from passlib.context import CryptContext
from src.api.models import UserLogin, UserRegister, AuthResponse
from src.api.jwt_handler import create_token
from src.api.dependencies import get_current_user
import uuid

router = APIRouter()

# Password hashing context (uses bcrypt algorithm)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- MOCK DATABASE ---
# Replaces Supabase for the hackathon until Person 4's client is ready.
# We store the users in-memory to simulate database behavior.
MOCK_DB_USERS = {}

@router.post("/register")
async def register(user: UserRegister):
    """
    Registers a new user (Patient or Doctor).
    Hashes the password securely and saves them to the database.
    """
    # 1. Validation
    if user.email in MOCK_DB_USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    if user.role not in ["patient", "doctor"]:
        raise HTTPException(status_code=400, detail="Role must be 'patient' or 'doctor'")

    # 2. Hash the password before saving! Never save plain text passwords.
    hashed_password = pwd_context.hash(user.password)
    user_id = str(uuid.uuid4())
    
    # 3. Save to mock database (simulate writing to Supabase)
    MOCK_DB_USERS[user.email] = {
        "id": user_id,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": hashed_password,
        "role": user.role
    }
    
    return {
        "user_id": user_id,
        "email": user.email,
        "role": user.role,
        "message": "User registered successfully"
    }

@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin):
    """
    Authenticates a user and issues a real JWT.
    """
    # Look up the user by email
    user = MOCK_DB_USERS.get(credentials.email)
    
    # 1. Validation: Check if user exists and if the hashed password matches
    if not user or not pwd_context.verify(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # 2. Token Generation
    # Create the payload containing the user ID and role for our dependency guards
    token_payload = {
        "user_id": user["id"],
        "role": user["role"]
    }
    token = create_token(token_payload)
    
    # 3. Return the AuthResponse contract with the real JWT
    return AuthResponse(
        access_token=token,
        role=user["role"]
    )

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Validates the JWT token and returns the current user's payload.
    Used by the frontend to restore sessions on page reload.
    """
    return current_user
