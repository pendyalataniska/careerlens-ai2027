from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResumePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_type: Literal["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    file_size_bytes: int
    extraction_status: str
    task_id: str | None = None
    created_at: datetime


class ResumeTaskPublic(BaseModel):
    resume_id: UUID
    status: str
    task_id: str | None
    limitations: list[str]


class ExtractedSkill(BaseModel):
    name: str
    source: Literal["resume_text"]


class ExtractedEvidence(BaseModel):
    text: str
    source: Literal["resume_text"]


class ResumeAnalysisPublic(BaseModel):
    resume_id: UUID
    extraction_status: str
    skills: list[ExtractedSkill]
    skill_section_evidence: list[ExtractedEvidence]
    education: list[ExtractedEvidence]
    work_experience: list[ExtractedEvidence]
    projects: list[ExtractedEvidence]
    certifications: list[ExtractedEvidence]
    contact_information_redacted: bool = True
    limitations: list[str]
