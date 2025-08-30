"""Pydantic models for resume data validation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for LLM model."""

    provider: str = "anthropic"
    model_name: str = "claude-3-5-sonnet-latest"
    temperature: float = 0.7

    # Supported models by provider
    SUPPORTED_MODELS: dict[str, List[str]] = {
        "anthropic": [
            "claude-opus-4-1",
            "claude-opus-4-0",
            "claude-sonnet-4-0",
            "claude-3-7-sonnet-latest",
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest"
        ],
        "openai": [
            "gpt-4o-2024-08-06",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo"
        ]
    }


class UserBackground(BaseModel):
    """Raw markdown content from user's background files."""

    experience_md: str
    education_md: str = ""
    contact_md: str = ""
    skills_md: str = ""  # Optional skills section


class JobPostingContent(BaseModel):
    """Content extracted from job posting by LLM - no system metadata."""

    title: str
    company: str
    location: Optional[str] = None
    requirements: List[str]
    responsibilities: List[str]
    keywords: List[str]
    pay: Optional[str] = None  # Salary information (range or single figure)
    industry: str  # Approximation of what industry this role is in
    practical_description: str  # What the job would actually entail in practice, not HR speak


class JobPosting(BaseModel):
    """Complete job posting with system metadata."""

    id: str  # System-generated numeric timestamp
    title: str
    company: str
    location: Optional[str] = None
    requirements: List[str]
    responsibilities: List[str]
    keywords: List[str]
    pay: Optional[str] = None
    industry: str  # Approximation of what industry this role is in
    practical_description: str  # What the job would actually entail in practice, not HR speak
    created_at: str  # ISO format datetime when posting was added
    raw_content: str
    model_provider: str = "unknown"  # Provider used to parse this posting
    model_name: str = "unknown"  # Model name used to parse this posting

    @classmethod
    def from_content(cls, content: JobPostingContent, id: str, created_at: str,
                    model_provider: str, model_name: str, raw_content: str) -> 'JobPosting':
        """Create JobPosting from LLM content and system metadata."""
        return cls(
            id=id,
            title=content.title,
            company=content.company,
            location=content.location,
            requirements=content.requirements,
            responsibilities=content.responsibilities,
            keywords=content.keywords,
            pay=content.pay,
            industry=content.industry,
            practical_description=content.practical_description,
            created_at=created_at,
            raw_content=raw_content,
            model_provider=model_provider,
            model_name=model_name,
        )


class ResumeContent(BaseModel):
    """Generated resume content."""

    resume_markdown: str
    summary: str = ""  # Brief summary of what was emphasized


class ResumeMetadata(BaseModel):
    """Metadata for a generated resume."""

    job_id: str
    job_title: str
    company: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    model_provider: str
    model_name: str
    tone: Optional[str] = None
    user_feedback: Optional[str] = None


class AppConfig(BaseModel):
    """Simple application configuration."""

    default_model: ModelConfig = ModelConfig()
    data_dir: str = "data"

    @classmethod
    def load(cls) -> 'AppConfig':
        """Load configuration with defaults."""
        import os
        from pathlib import Path

        # Allow custom data directory via environment variable
        data_dir = os.getenv("RESUMES_DATA_DIR", "data")

        return cls(
            default_model=ModelConfig(),
            data_dir=data_dir
        )


@dataclass
class ResumeDeps:
    """Dependencies for resume generation agent."""
    job_posting: JobPosting
    user_background: UserBackground
    template: str  # Simple template string for now
    tone: Optional[str]
    user_feedback: Optional[str]
