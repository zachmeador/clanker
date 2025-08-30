# resumes

AI-powered resume generator that makes the tedious process of tailoring resumes simple.

## Overview

This app uses clanker's new storage conventions:
- **Vault** (`data/default/vault/resumes/`): Stores your background.md, generated resumes, and exported PDF resumes

## Setup

1. Copy `.env.example` to `.env` and add your API keys
2. Install with uv: `uv sync`
3. Initialize: `uv run python -m resumes.cli init`

## Usage

```bash
# Parse a job posting (text only)
uv run resumes parse-job job_posting.txt

# List all jobs
uv run resumes list-jobs

# Generate a resume
uv run resumes generate <job-id>

# Generate with specific tone
uv run resumes generate <job-id> --tone technical

# Export resume to PDF
uv run resumes export <job-id>

# Export with modern template
uv run resumes export <job-id> --template modern

# Show your background
uv run resumes show-background
```

## PDF Export

The app exports your markdown resumes to professional PDFs using the `export` command:
- **Templates**: Choose between 'professional' (default) or 'modern' styles
- **Storage**: PDFs are saved to the app vault under `data/default/vault/resumes/jobs/<job-id>/resumes/`
- **Requirements**: WeasyPrint requires system dependencies:
  - macOS: `brew install cairo pango gdk-pixbuf libffi`
  - Ubuntu: `sudo apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0`

## How it works

1. **One source of truth**: Your background lives in the vault as `background.md`
2. **Smart parsing**: LLM analyzes job postings to extract requirements and keywords
3. **Tailored generation**: Creates resumes optimized for each specific role
4. **Natural iteration**: Regenerate with different tones or feedback

## Storage Structure

```
# At clanker root level:
data/default/vault/resumes/
├── background.md                 # Your experience/education/skills
└── jobs/
    └── <company_title_mmyy>/
        ├── metadata.yaml         # Parsed job metadata
        └── resumes/
            └── <timestamp>.pdf  # Exported resume PDFs

# Generated markdown resumes are stored at:
data/default/vault/resumes/resumes/<Company>_<Title>_<timestamp>.md
```