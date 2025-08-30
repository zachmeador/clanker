"""Pydantic-AI agents for resume management."""

import os
from pathlib import Path
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIModel

from .models import (
    JobPosting,
    JobPostingContent,
    ModelConfig,
    ResumeContent,
    ResumeDeps,
    ResumeMetadata,
    UserBackground,
)


# System prompts
JOB_PARSER_SYSTEM_PROMPT = """You are an expert at parsing job postings and extracting comprehensive structured information for resume optimization.

Your task is to analyze the raw job posting content and extract:

1. **Job title and company name** - Extract exactly as stated
2. **Location** - Include if mentioned, even if remote/hybrid
3. **Comprehensive requirements** - Extract ALL requirements including technical skills, experience, education, certifications
4. **Detailed responsibilities** - Preserve technical depth and specificity
5. **Comprehensive keywords** - Extract technical and business terms
6. **Pay information** - Extract salary/compensation details or null
7. **Industry** - Determine the specific industry/sector this role is in. Be as specific as possible rather than using broad categories. Examples: "Financial Technology (FinTech)", "Enterprise Software", "Healthcare IT", "E-commerce", "Cloud Infrastructure", "Cybersecurity", "Management Consulting", "Investment Banking", "Pharmaceuticals", "Medical Devices", "Automotive Manufacturing", "Renewable Energy", "Real Estate Technology", "Educational Technology", etc.
8. **Practical description** - Provide an honest breakdown of how someone in this role would actually spend their time, rank-ordered by cumulative percentage of time spent. AVOID ALL corporate buzzwords, MBA-speak, and HR jargon. Be specific about the actual activities IN THAT SPECIFIC INDUSTRY. Tailor the activities to the industry context. Examples:
   - For agribusiness data scientist: "30% - Cleaning sensor data from farms (soil, weather, irrigation), 25% - Building crop yield prediction models, 20% - Creating reports for farmers and agronomists, 15% - Field visits to validate predictions, 10% - Meetings with agricultural engineers"
   - For fintech software dev: "45% - Writing code for payment processing systems, 25% - Debugging transaction failures and security issues, 15% - Regulatory compliance meetings and documentation, 10% - Code reviews focused on financial accuracy, 5% - Learning about banking regulations"
   - For healthcare consulting: "35% - Building Excel models of patient flow and costs, 30% - Meetings with hospital administrators, 20% - Analyzing clinical data and outcomes, 10% - Creating PowerPoints for C-suite presentations, 5% - Site visits to medical facilities"

Guidelines:
- Be exhaustive in extraction - don't summarize or condense
- Preserve technical precision and industry-specific language
- Extract implicit requirements from job descriptions
- Consider both hard and soft requirements
- For industry classification, be specific but concise
- For practical description, strip away ALL corporate speak and buzzwords - describe the actual work in plain English as if explaining to a friend what you'd be doing at your desk each day"""

RESUME_GENERATOR_SYSTEM_PROMPT = """You are an expert resume writer who creates tailored resumes for specific job postings.

Your task is to generate a professional resume that:
1. Tailors content specifically to the job posting requirements
2. Uses the user's background information effectively
3. Matches the tone and style appropriate for the role
4. Emphasizes relevant skills and experiences
5. Uses strong action verbs and quantifiable achievements where possible

Guidelines:
- Extract and emphasize skills that match the job requirements
- Reorganize experience to highlight the most relevant positions first
- Use keywords from the job posting naturally throughout the resume
- Adapt the language style to match the company's tone
- Keep the resume concise but comprehensive
- Focus on achievements and impact, not just duties

The resume should follow this general structure:
- Contact information
- Professional summary (2-3 sentences tailored to the role)
- Experience (most relevant first)
- Education
- Skills (technical and relevant to the job)

If user feedback is provided, incorporate those specific changes and improvements."""


def create_model_from_config(config: ModelConfig):
    """Create pydantic-ai model from config."""
    if config.provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic models.")
        return AnthropicModel(config.model_name, api_key=api_key)
    elif config.provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI models.")
        return OpenAIModel(config.model_name, api_key=api_key)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")


def create_job_parser_agent(model_config: ModelConfig) -> Agent[JobPostingContent]:
    """Create job parser agent with specified model config."""
    model = create_model_from_config(model_config)
    return Agent(
        model,
        output_type=JobPostingContent,
        system_prompt=JOB_PARSER_SYSTEM_PROMPT,
        retries=3
    )


def create_resume_generator_agent(model_config: ModelConfig) -> Agent[ResumeContent]:
    """Create resume generator agent with specified model config."""
    model = create_model_from_config(model_config)
    return Agent(
        model,
        output_type=ResumeContent,
        system_prompt=RESUME_GENERATOR_SYSTEM_PROMPT,
        retries=3
    )


def parse_job_posting(raw_content: str, model_config: ModelConfig, job_id: Optional[str] = None) -> JobPosting:
    """Parse raw job posting content into structured data."""
    agent = create_job_parser_agent(model_config)

    result = agent.run_sync(
        f"Parse this job posting:\n\n{raw_content}",
        message_history=[],
    )

    # System creates the full JobPosting with metadata
    from datetime import datetime
    posting_id = job_id or datetime.now().strftime("%Y%m%d%H%M%S")
    created_at = datetime.now().isoformat()

    return JobPosting.from_content(
        result.output,
        posting_id,
        created_at,
        model_config.provider,
        model_config.model_name,
        raw_content  # Pass original raw content directly
    )


def generate_resume(deps: ResumeDeps, model_config: ModelConfig) -> tuple[ResumeContent, ResumeMetadata]:
    """Generate a tailored resume."""
    agent = create_resume_generator_agent(model_config)

    # Build the prompt with all context
    job = deps.job_posting
    prompt = f"""Generate a tailored resume for this job posting.

## JOB POSTING
Title: {job.title}
Company: {job.company}
Industry: {job.industry}
Location: {job.location or 'Not specified'}

Requirements:
{chr(10).join('- ' + req for req in job.requirements)}

Responsibilities:
{chr(10).join('- ' + resp for resp in job.responsibilities)}

Keywords: {', '.join(job.keywords)}

Pay: {job.pay or 'Not specified'}

Practical Description:
{job.practical_description}

## USER BACKGROUND
{deps.user_background.experience_md}
{deps.user_background.education_md}
{deps.user_background.contact_md}
{deps.user_background.skills_md}

## ADDITIONAL CONTEXT
Template: {deps.template}
Tone: {deps.tone or 'professional'}
{f'User Feedback: {deps.user_feedback}' if deps.user_feedback else ''}

Generate a resume that is specifically tailored to this job posting, emphasizing relevant experience and skills."""

    result = agent.run_sync(
        prompt,
        message_history=[],
    )

    # Create metadata
    metadata = ResumeMetadata(
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        model_provider=model_config.provider,
        model_name=model_config.model_name,
        tone=deps.tone,
        user_feedback=deps.user_feedback
    )

    return result.output, metadata

