"""
Authentication Endpoints & Security Dependency
==============================================
Provides signup, login, logout, token refresh, password reset, and the
core `get_current_user` FastAPI dependency for multi-tenant route protection.
Supports dual auth transport: Authorization Bearer header and secure httpOnly cookies.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.core.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.logging import get_logger
from app.core.security import (
    auth_rate_limiter,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.storage import storage
from app.models.schemas import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

logger = get_logger("auth")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

bearer_scheme = HTTPBearer(auto_error=False)


def _get_client_ip(request: Request) -> str:
    """Extracts client IP for rate limiting behind proxies or direct."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Sets secure cookies for browser-based navigation and XHR."""
    is_prod = settings.ENV == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clears authentication cookies upon logout."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/auth")


async def get_current_user(
    request: Request,
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    access_token_cookie: Optional[str] = Cookie(default=None, alias="access_token"),
) -> UserResponse:
    """
    FastAPI dependency that extracts, verifies, and resolves the current authenticated user.
    Prioritizes Authorization header ('Bearer <token>') and falls back to httpOnly cookie.
    Raises 401 Unauthorized cleanly if missing, invalid, expired, or user deactivated.
    """
    token: Optional[str] = None
    if bearer_creds and bearer_creds.credentials:
        token = bearer_creds.credentials
    elif access_token_cookie:
        token = access_token_cookie

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for API access.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_row = storage.get_user_by_id(user_id)
    if not user_row or not user_row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is invalid or inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse(
        id=user_row["id"],
        email=user_row["email"],
        full_name=user_row["full_name"],
        is_active=bool(user_row["is_active"]),
        email_verified=bool(user_row["email_verified"]),
        created_at=user_row["created_at"],
    )


# -------------------------------------------------------------
# Auth API Endpoints
# -------------------------------------------------------------
@auth_router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, request: Request, response: Response):
    """Registers a new user account and returns JWT credentials."""
    client_ip = _get_client_ip(request)
    if not auth_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please wait a minute.",
        )

    if len(user_in.password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )

    pwd_hash = hash_password(user_in.password)
    try:
        user = storage.create_user(
            email=user_in.email,
            password_hash=pwd_hash,
            full_name=user_in.full_name,
        )
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

    access_token = create_access_token({"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token({"sub": user.id, "email": user.email})
    _set_auth_cookies(response, access_token, refresh_token)

    logger.info("user_signup_success", user_id=user.id, email=user.email)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user,
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(login_in: UserLogin, request: Request, response: Response):
    """Authenticates credentials and returns JWT access + refresh tokens."""
    client_ip = _get_client_ip(request)
    rate_key = f"{client_ip}:{login_in.email.strip().lower()}"

    if not auth_rate_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait a minute.",
        )

    user_row = storage.get_user_by_email(login_in.email)
    if not user_row or not verify_password(login_in.password, user_row["password_hash"]):
        # Generic error message to prevent account enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user_row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    auth_rate_limiter.reset(rate_key)

    user = UserResponse(
        id=user_row["id"],
        email=user_row["email"],
        full_name=user_row["full_name"],
        is_active=bool(user_row["is_active"]),
        email_verified=bool(user_row["email_verified"]),
        created_at=user_row["created_at"],
    )

    access_token = create_access_token({"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token({"sub": user.id, "email": user.email})
    _set_auth_cookies(response, access_token, refresh_token)

    logger.info("user_login_success", user_id=user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user,
    )


@auth_router.post("/logout")
async def logout(response: Response):
    """Clears authentication cookies."""
    _clear_auth_cookies(response)
    return {"status": "ok", "message": "Successfully logged out."}


@auth_router.get("/me", response_model=UserResponse)
async def get_my_account(current_user: UserResponse = Depends(get_current_user)):
    """Returns the authenticated user's account info."""
    return current_user


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_req: Optional[RefreshTokenRequest] = None,
    refresh_cookie: Optional[str] = Cookie(default=None, alias="refresh_token"),
):
    """Issues fresh access & refresh tokens from a valid refresh token."""
    token = None
    if refresh_req and refresh_req.refresh_token:
        token = refresh_req.refresh_token
    elif refresh_cookie:
        token = refresh_cookie

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required.",
        )

    try:
        payload = decode_token(token)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is not a refresh token.",
        )

    user_id = payload.get("sub")
    user_row = storage.get_user_by_id(user_id) if user_id else None
    if not user_row or not user_row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    user = UserResponse(
        id=user_row["id"],
        email=user_row["email"],
        full_name=user_row["full_name"],
        is_active=bool(user_row["is_active"]),
        email_verified=bool(user_row["email_verified"]),
        created_at=user_row["created_at"],
    )

    new_access = create_access_token({"sub": user.id, "email": user.email})
    new_refresh = create_refresh_token({"sub": user.id, "email": user.email})
    _set_auth_cookies(response, new_access, new_refresh)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        user=user,
    )


@auth_router.post("/forgot-password")
async def forgot_password(forgot_in: ForgotPasswordRequest, request: Request):
    """
    Generates a password reset token. Logs the reset token in development.
    Can be connected to an email service (Postmark, SendGrid) via env var.
    """
    client_ip = _get_client_ip(request)
    if not auth_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please wait a minute.",
        )

    user_row = storage.get_user_by_email(forgot_in.email)
    if user_row:
        reset_token = str(uuid.uuid4())
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        storage.create_password_reset(reset_token, user_row["id"], expires_at)
        logger.info(
            "password_reset_token_generated",
            user_id=user_row["id"],
            token=reset_token,
            hint="Use this token with POST /api/auth/reset-password",
        )

    # Generic return to prevent email probing
    return {
        "status": "ok",
        "message": "If that email is registered, password reset instructions have been dispatched.",
    }


@auth_router.post("/reset-password")
async def reset_password(reset_in: ResetPasswordRequest):
    """Consumes a valid reset token and updates the user's password."""
    token_record = storage.get_password_reset(reset_in.token)
    if not token_record or token_record["used"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset token.",
        )

    # Check expiration
    expires = datetime.fromisoformat(token_record["expires_at"])
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired.",
        )

    if len(reset_in.new_password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters.",
        )

    new_hash = hash_password(reset_in.new_password)
    storage.update_user_password(token_record["user_id"], new_hash)
    storage.mark_password_reset_used(reset_in.token)

    logger.info("password_reset_successful", user_id=token_record["user_id"])
    return {"status": "ok", "message": "Password successfully reset. You may now log in."}
