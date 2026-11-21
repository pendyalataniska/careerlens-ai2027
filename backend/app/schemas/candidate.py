from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole


class CandidateProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    headline: str | None = Field(default=None, max_length=180)
    location: str | None = Field(default=None, max_length=180)
    summary: str | None = Field(default=None, max_length=5000)

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CandidateUserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole


class CandidateProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    headline: str | None
    location: str | None
    summary: str | None
    user: CandidateUserPublic


class CandidateDashboardJob(BaseModel):
    id: UUID
    title: str
    company_name: str | None
    location: str | None
    total_score: float
    created_at: datetime


class CandidateDashboardPublic(BaseModel):
    profile: CandidateProfilePublic
    latest_resume_id: UUID | None
    resume_status: str | None
    skills: list[str]
    matches: list[CandidateDashboardJob]
    interview_sessions: int
    completed_interviews: int
    disclaimer: str
