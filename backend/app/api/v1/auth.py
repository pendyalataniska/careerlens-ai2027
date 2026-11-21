from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DbSession
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from app.services.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def build_auth_response(user: User, token: str, expires_in: int) -> AuthResponse:
    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserPublic(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        ),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: DbSession) -> AuthResponse:
    try:
        user = register_user(db, payload)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None

    token, expires_in = create_access_token(user.id)
    return build_auth_response(user, token, expires_in)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    try:
        user, token, expires_in = authenticate_user(db, payload)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    return build_auth_response(user, token, expires_in)


@router.get("/me", response_model=UserPublic)
def get_me(user: CurrentUser) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )
