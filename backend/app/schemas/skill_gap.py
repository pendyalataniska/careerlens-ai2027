from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.learning_activity import LearningActivityStatus


class LearningResourcePublic(BaseModel):
    id: str
    title: str
    provider: str
    url: str
    description: str
    status: LearningActivityStatus | None = None
    activity_id: UUID | None = None


class SkillEvidencePublic(BaseModel):
    skill: str
    category: Literal["strong_match", "partial_match", "missing"]
    explanation: str
    learning_progress: int = Field(ge=0, le=100)
    resources: list[LearningResourcePublic]


class SkillGapAnalysisPublic(BaseModel):
    job_id: UUID
    job_title: str
    resume_id: UUID
    strong_matches: list[SkillEvidencePublic]
    partial_matches: list[SkillEvidencePublic]
    missing_skills: list[SkillEvidencePublic]
    evidence_note: str


class LearningActivityCreate(BaseModel):
    skill: str = Field(min_length=1, max_length=120)
    resource_id: str = Field(min_length=1, max_length=120)
    status: LearningActivityStatus = LearningActivityStatus.PLANNED


class LearningActivityUpdate(BaseModel):
    status: LearningActivityStatus


class LearningActivityPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    skill: str
    resource_id: str
    status: LearningActivityStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class RelatedJobPublic(BaseModel):
    job_id: UUID
    title: str
    company_name: str | None
    location: str | None
    matching_skills: list[str]
    missing_skills: list[str]
    explanation: str


class RelatedJobsPublic(BaseModel):
    items: list[RelatedJobPublic]
