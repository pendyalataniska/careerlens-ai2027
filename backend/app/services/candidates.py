from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.candidate import CandidateProfile
from app.models.user import User
from app.schemas.candidate import CandidateProfileUpdate


def get_candidate_profile(db: Session, user: User) -> CandidateProfile | None:
    return db.scalar(
        select(CandidateProfile)
        .options(joinedload(CandidateProfile.user))
        .where(CandidateProfile.user_id == user.id)
    )


def update_candidate_profile(
    db: Session, user: User, changes: CandidateProfileUpdate
) -> CandidateProfile | None:
    profile = get_candidate_profile(db, user)
    if profile is None:
        return None

    updates = changes.model_dump(exclude_unset=True)
    if "full_name" in updates:
        full_name = updates.pop("full_name")
        if full_name is not None:
            names = full_name.strip().split(maxsplit=1)
            profile.first_name = names[0]
            profile.last_name = names[1] if len(names) > 1 else ""
    for field, value in updates.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
