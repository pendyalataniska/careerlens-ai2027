from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


InterviewCategory = Literal["TECHNICAL", "HR"]
InterviewStatus = Literal["DRAFT", "IN_PROGRESS", "COMPLETED"]


class InterviewRolePublic(BaseModel):
    id: UUID
    title: str
    company_name: str | None
    location: str | None
    required_skills: list[str]


class InterviewSessionCreate(BaseModel):
    job_id: UUID
    technical_questions: int = Field(default=5, ge=1, le=10)
    hr_questions: int = Field(default=3, ge=1, le=10)


class InterviewQuestionCreate(BaseModel):
    category: InterviewCategory
    prompt: str = Field(min_length=10, max_length=1000)
    targeted_skills: list[str] = Field(min_length=1, max_length=5)


class InterviewQuestionEvaluation(BaseModel):
    score: int = Field(ge=1, le=5)
    feedback: str = Field(min_length=1, max_length=1200)


class InterviewEvaluationPublic(BaseModel):
    relevance: InterviewQuestionEvaluation
    technical_correctness: InterviewQuestionEvaluation
    clarity: InterviewQuestionEvaluation
    completeness: InterviewQuestionEvaluation
    overall_feedback: str = Field(min_length=1, max_length=2000)
    strengths: list[str] = Field(max_length=5)
    areas_to_improve: list[str] = Field(max_length=5)


class InterviewQuestionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    category: InterviewCategory
    prompt: str
    targeted_skills: list[str]
    answer: str | None
    evaluation: InterviewEvaluationPublic | None
    answered_at: datetime | None


class InterviewSessionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID | None
    role_title: str
    status: InterviewStatus
    created_at: datetime
    completed_at: datetime | None
    questions: list[InterviewQuestionPublic]
    answered_questions: int
    total_questions: int
    average_score: float | None = Field(
        description="Mean of rubric scores (1-5); practice feedback only, not employability."
    )
    score_disclaimer: str


class InterviewAnswerCreate(BaseModel):
    answer: str = Field(min_length=10, max_length=10_000)

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 10:
            raise ValueError("Answer must contain at least 10 non-whitespace characters.")
        return normalized


class InterviewAnalyticsPublic(BaseModel):
    total_sessions: int
    completed_sessions: int
    total_questions: int
    answered_questions: int
    average_score: float | None = Field(
        description="Mean of rubric scores (1-5); practice feedback only, not employability."
    )
    criterion_averages: dict[
        Literal["relevance", "technical_correctness", "clarity", "completeness"],
        float | None,
    ]
    disclaimer: str


class InterviewSessionList(BaseModel):
    items: list[InterviewSessionPublic]
