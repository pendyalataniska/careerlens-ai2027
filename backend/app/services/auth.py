from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.candidate import CandidateProfile
from app.models.recruiter import RecruiterProfile
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register_user(db: Session, request: RegisterRequest) -> User:
    normalized_email = str(request.email).strip().lower()
    user = User(
        email=normalized_email,
        hashed_password=hash_password(request.password),
        role=request.role,
    )
    if request.role == UserRole.CANDIDATE:
        names = request.full_name.strip().split(maxsplit=1)
        user.candidate_profile = CandidateProfile(
            first_name=names[0],
            last_name=names[1] if len(names) > 1 else "",
        )
    else:
        user.recruiter_profile = RecruiterProfile(
            full_name=request.full_name.strip(),
            company_name=request.company_name.strip() if request.company_name else None,
        )

    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint_name = getattr(
            getattr(exc.orig, "diag", None), "constraint_name", None
        )
        message = str(exc.orig).lower()
        if (
            constraint_name == "ix_users_email"
            or "users.email" in message
            or "users_email_key" in message
        ):
            raise EmailAlreadyRegisteredError from exc
        raise
    db.refresh(user)
    return user


def authenticate_user(db: Session, request: LoginRequest) -> tuple[User, str, int]:
    user = db.scalar(
        select(User).where(User.email == str(request.email).strip().lower())
    )
    if (
        user is None
        or not user.is_active
        or not verify_password(request.password, user.hashed_password)
    ):
        raise InvalidCredentialsError
    access_token, expires_in = create_access_token(user.id)
    return user, access_token, expires_in
