from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=20, max_length=20_000)
    location: str | None = Field(default=None, max_length=180)
    employment_type: str | None = Field(default=None, max_length=40)
    required_skills: list[str] = Field(default_factory=list, max_length=100)
    minimum_experience_years: int | None = Field(default=None, ge=0, le=60)
    required_education: str | None = Field(default=None, max_length=300)

    @field_validator("required_skills")
    @classmethod
    def normalize_required_skills(cls, skills: list[str]) -> list[str]:
        normalized = [skill.strip() for skill in skills if skill.strip()]
        return list(dict.fromkeys(normalized))


class JobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    location: str | None
    employment_type: str | None
    created_at: datetime
    company_name: str | None
    required_skills: list[str] = Field(default_factory=list)
    minimum_experience_years: int | None
    required_education: str | None


class JobList(BaseModel):
    items: list[JobPublic]
    total: int
    limit: int
    offset: int
