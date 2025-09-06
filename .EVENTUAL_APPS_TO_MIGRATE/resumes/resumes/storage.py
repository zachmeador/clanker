"""Storage operations for resume vault using clanker vault."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from clanker.storage.vault import Vault

from .models import AppConfig, JobPosting, ResumeMetadata


class ResumeStorage:
    """Handle resume and job posting storage in vault."""

    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize storage with vault."""
        self.config = config or AppConfig.load()
        self.vault = Vault.for_app("resumes")

    def _generate_job_id(self, company: str, title: str, created_at: str) -> str:
        """Generate a string ID from company, title, and date (MMYY format)."""
        # Clean company and title
        clean_company = company.lower().replace(" ", "_").replace("/", "_").replace(".", "")
        clean_title = title.lower().replace(" ", "_").replace("/", "_").replace(".", "")

        # Extract MMYY from created_at (format: YYYY-MM-DD HH:MM:SS)
        date_parts = created_at.split()[0].split("-")  # Get YYYY-MM-DD part
        if len(date_parts) >= 2:
            mmyy = f"{date_parts[1]}{date_parts[0][2:]}"  # MMYY
        else:
            mmyy = datetime.now().strftime("%m%y")

        # Limit lengths to keep ID manageable
        clean_company = clean_company[:30]
        clean_title = clean_title[:30]

        return f"{clean_company}_{clean_title}_{mmyy}"

    def init_background_template(self):
        """Create background.md template in vault if it doesn't exist."""
        if not self.vault.exists("background.md"):
            template = """# Professional Background

## Experience

### Senior Software Engineer | TechCorp Inc. | 2021-Present
- Led development of microservices architecture serving 10M+ users
- Reduced API response time by 40% through optimization
- Mentored 5 junior developers and conducted code reviews

### Software Engineer | StartupXYZ | 2019-2021
- Built RESTful APIs using Python and FastAPI
- Implemented CI/CD pipelines reducing deployment time by 60%
- Collaborated with product team to deliver 15+ features

## Education

### Bachelor of Science in Computer Science
**University of Technology** | 2015-2019
- GPA: 3.8/4.0
- Relevant coursework: Algorithms, Database Systems, Machine Learning

## Projects

### Open Source Contribution | 2020
- Contributed to popular Python library with 10K+ stars
- Implemented feature for async processing
"""
            self.vault.write("background.md", template)
            print("Created background.md template in vault")

    def load_user_background(self) -> str:
        """Load user background from vault."""
        if self.vault.exists("background.md"):
            content = self.vault.read("background.md")
            return content if isinstance(content, str) else str(content)
        else:
            self.init_background_template()
            content = self.vault.read("background.md")
            return content if isinstance(content, str) else str(content)

    def save_job_posting(self, job: JobPosting) -> str:
        """Save a job posting to vault."""
        # Generate string job ID
        job_id = self._generate_job_id(job.company, job.title, job.created_at)

        # Check if job already exists
        metadata_path = f"jobs/{job_id}/metadata.yaml"
        if self.vault.exists(metadata_path):
            print(f"Job already exists with ID: {job_id}")
            return job_id

        # Prepare job metadata
        job_metadata: Dict[str, Any] = {
            "id": job_id,
            "title": job.title,
            "company": job.company,
            "industry": job.industry,
            "location": job.location,
            "url": None,  # Can be added later
            "description_text": job.practical_description,
            "requirements": job.requirements,
            "responsibilities": job.responsibilities,
            "keywords": job.keywords,
            "pay": job.pay,
            "posted_date": job.created_at,
            "created_at": job.created_at,
            "raw_content": job.raw_content,
            "model_provider": job.model_provider,
            "model_name": job.model_name
        }

        # Save job metadata to vault
        self.vault.write(metadata_path, job_metadata)

        print(f"Saved job posting: {job.title} at {job.company}")
        print(f"Job ID: {job_id}")
        return job_id

    def load_job_posting(self, job_id: str) -> Optional[JobPosting]:
        """Load a job posting by ID."""
        metadata_path = f"jobs/{job_id}/metadata.yaml"

        if not self.vault.exists(metadata_path):
            return None

        job_data = self.vault.read(metadata_path)

        # Reconstruct JobPosting from metadata
        return JobPosting(
            id=job_data["id"],
            title=job_data["title"],
            company=job_data["company"],
            location=job_data.get("location"),
            requirements=job_data.get("requirements", []),
            responsibilities=job_data.get("responsibilities", []),
            keywords=job_data.get("keywords", []),
            pay=job_data.get("pay"),
            industry=job_data.get("industry", "Unknown"),
            practical_description=job_data["description_text"],
            created_at=job_data["created_at"],
            raw_content=job_data.get("raw_content", ""),
            model_provider=job_data.get("model_provider", "unknown"),
            model_name=job_data.get("model_name", "unknown")
        )

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all jobs with company info."""
        result = []

        # List all directories under jobs/
        jobs_files = self.vault.list("jobs")

        # Find all metadata.yaml files
        metadata_files = [f for f in jobs_files if f.endswith("metadata.yaml")]

        for metadata_file in metadata_files:
            try:
                job_data = self.vault.read(metadata_file)
                result.append({
                    "id": job_data["id"],
                    "title": job_data["title"],
                    "company": job_data["company"],
                    "created_at": job_data["created_at"]
                })
            except Exception as e:
                print(f"Error reading job metadata from {metadata_file}: {e}")
                continue

        return sorted(result, key=lambda x: x["created_at"], reverse=True)

    def save_resume(self, job_id: str, resume_content: str, metadata: ResumeMetadata) -> str:
        """Save a resume for a job posting in vault."""
        job = self.load_job_posting(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Clean the filename parts first
        clean_company = job.company.replace(" ", "_").replace("/", "_")
        clean_title = job.title.replace(" ", "_").replace("/", "_")
        filename = f"resumes/{clean_company}_{clean_title}_{timestamp}.md"

        self.vault.write(filename, resume_content)

        # Save metadata
        metadata_filename = f"resumes/{clean_company}_{clean_title}_{timestamp}_metadata.yaml"
        self.vault.write(metadata_filename, metadata.model_dump())

        print(f"Saved resume: {filename}")
        return filename

    def get_latest_resume_markdown(self, job_id: str) -> Optional[str]:
        """Get the latest resume markdown content for a job."""
        job = self.load_job_posting(job_id)
        if not job:
            return None

        # List resumes in vault for this job
        resumes = self.vault.list("resumes")

        # Convert company and title to match filename format
        clean_company = job.company.replace(" ", "_").replace("/", "_")
        clean_title = job.title.replace(" ", "_").replace("/", "_")

        # Find markdown resumes for this job
        job_resumes = [r for r in resumes
                       if clean_company in r and clean_title in r and r.endswith('.md') and not r.endswith('_metadata.yaml')]

        if not job_resumes:
            return None

        # Get the latest resume
        latest_resume = sorted(job_resumes)[-1]
        content = self.vault.read(latest_resume)
        return content if isinstance(content, str) else str(content)

    def save_resume_pdf(self, job_id: str, pdf_content: bytes, timestamp: Optional[str] = None) -> str:
        """Save a resume PDF to vault organized by job ID."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create path organized by job ID
        pdf_path = f"jobs/{job_id}/resumes/{timestamp}.pdf"

        # Save PDF to vault
        self.vault.write(pdf_path, pdf_content)

        print(f"Saved resume PDF to vault: {pdf_path}")
        return pdf_path

    def list_resumes(self, job_id: str) -> List[str]:
        """List all resume files for a job."""
        job = self.load_job_posting(job_id)
        if not job:
            return []

        # List resumes in vault for this job
        resumes = self.vault.list("resumes")

        # Convert company and title to match filename format
        clean_company = job.company.replace(" ", "_").replace("/", "_")
        clean_title = job.title.replace(" ", "_").replace("/", "_")

        # Find all resume files for this job
        job_resumes = [r for r in resumes
                       if clean_company in r and clean_title in r and (r.endswith('.md') or r.endswith('.pdf'))]

        return sorted(job_resumes)
