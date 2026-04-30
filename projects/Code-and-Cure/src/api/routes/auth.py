from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import get_current_user

router = APIRouter()


_CLERK_ONLY_MESSAGE = (
    "This API now uses Clerk-managed authentication. Complete sign-in and sign-up from the Next.js frontend."
)


@router.post("/register", status_code=status.HTTP_410_GONE)
async def register() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/verify-email", status_code=status.HTTP_410_GONE)
async def verify_email() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/resend-verification", status_code=status.HTTP_410_GONE)
async def resend_verification() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/login", status_code=status.HTTP_410_GONE)
async def login() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/login/verify", status_code=status.HTTP_410_GONE)
async def verify_login() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_CLERK_ONLY_MESSAGE)


@router.post("/session")
async def sync_session(current_user: dict = Depends(get_current_user)) -> dict:
    return {
        "status": "authenticated",
        "user_id": current_user["user_id"],
        "role": current_user["role"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
    }


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)) -> dict:
    return {
        "user_id": current_user["user_id"],
        "role": current_user["role"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
    }


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key="__session", path="/")
    return {"status": "success"}
