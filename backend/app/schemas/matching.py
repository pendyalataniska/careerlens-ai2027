from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MatchingAnalyzeRequest(BaseModel):
    job_id: UUID
    resume_id: UUID | None = None


class ScoreComponent(BaseModel):
    score: float = Field(ge=0, le=1)
    configured_weight: float = Field(ge=0, le=1)
    effective_weight: float = Field(ge=0, le=1)
    explanation: str


class MatchDetails(BaseModel):
    matching_skills: list[str]
    missing_required_skills: list[str]
    components: dict[str, ScoreComponent]
    explanations: list[str]
    scoring_model_version: str
    score_completeness: str


class MatchingResultPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    resume_id: UUID
    total_score: float = Field(ge=0, le=100)
    score_details: MatchDetails
    scoring_model_version: str
    created_at: datetime


class MatchingRecommendations(BaseModel):
    items: list[MatchingResultPublic]
    limit: int
    scoring_policy: dict[str, float]
    scoring_model_version: str
