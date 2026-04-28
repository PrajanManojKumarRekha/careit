from fastapi import Cookie, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.api.config import JWT_COOKIE_NAME
from src.api.jwt_handler import decode_token

# This automatically extracts the Bearer token from the Authorization header
security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
    access_token: str | None = Cookie(default=None, alias=JWT_COOKIE_NAME),
) -> dict:
    """
    Reads the JWT from the 'Authorization: Bearer <token>' header,
    decodes it using our jwt_handler, and returns the user payload 
    (which contains 'user_id' and 'role').
    
    If the token is missing or invalid, this throws a 401 Unauthorized.
    """
    token = credentials.credentials if credentials else access_token
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(token)

def require_role(required_role: str):
    """
    A dependency factory that creates role-specific guards for our routes.
    
    Usage example:
        @router.post("/generate", dependencies=[Depends(require_role("doctor"))])
    
    This ensures that a patient cannot access a doctor-only endpoint, 
    and vice-versa. It enforces the strict access boundaries defined in 
    the Responsibilities document.
    """
    async def role_checker(user: dict = Depends(get_current_user)):
        # Check if the role in the JWT payload matches the required role
        if user.get("role") != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. This route requires '{required_role}' privileges."
            )
        return user
    
    return role_checker
