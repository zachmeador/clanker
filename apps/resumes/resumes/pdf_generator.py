"""PDF generation for resumes."""

import os
import re
from pathlib import Path
from typing import Dict, Optional
import markdown

# Fix library path for weasyprint on macOS
if os.name == 'posix' and os.uname().sysname == 'Darwin':  # macOS
    homebrew_lib = '/opt/homebrew/lib'
    if homebrew_lib not in os.environ.get('DYLD_FALLBACK_LIBRARY_PATH', ''):
        current_path = os.environ.get('DYLD_FALLBACK_LIBRARY_PATH', '')
        new_path = f"{homebrew_lib}:{current_path}" if current_path else homebrew_lib
        os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = new_path

from weasyprint import HTML, CSS


class PDFTemplate:
    """Base template for PDF generation."""

    def parse_sections(self, markdown_text: str) -> Dict[str, str]:
        """Parse markdown into sections based on headers."""
        sections = {}

        # Extract name (first # header)
        name_match = re.search(r'^#\s+(.+)$', markdown_text, re.MULTILINE)
        if name_match:
            sections['name'] = name_match.group(1).strip()

        # Extract contact info (usually after name, before first ##)
        lines = markdown_text.split('\n')
        contact_lines = []
        in_contact = False

        for i, line in enumerate(lines):
            if line.startswith('# ') and not in_contact:
                in_contact = True
                continue
            elif line.startswith('## '):
                in_contact = False
                break
            elif in_contact and line.strip():
                contact_lines.append(line.strip())

        sections['contact'] = ' | '.join(contact_lines)

        # Extract sections by ## headers
        section_pattern = r'^##\s+(.+)$'
        current_section = None
        current_content = []

        for line in lines:
            if re.match(section_pattern, line):
                # Save previous section
                if current_section:
                    sections[current_section.lower().replace(' ', '_')] = '\n'.join(current_content)
                # Start new section
                current_section = re.match(section_pattern, line).group(1)
                current_content = []
            elif current_section:
                current_content.append(line)

        # Don't forget the last section
        if current_section:
            sections[current_section.lower().replace(' ', '_')] = '\n'.join(current_content)

        return sections

    def generate_html(self, sections: Dict[str, str]) -> str:
        """Generate HTML from sections. Override in subclasses."""
        raise NotImplementedError

    def get_css(self) -> str:
        """Return CSS for this template. Override in subclasses."""
        raise NotImplementedError


class ProfessionalTemplate(PDFTemplate):
    """Clean, professional single-column template."""

    def generate_html(self, sections: Dict[str, str]) -> str:
        """Generate professional HTML layout."""
        # Convert markdown content to HTML for each section
        md = markdown.Markdown()

        html_sections = {}
        for key, content in sections.items():
            if key not in ['name', 'contact']:
                html_sections[key] = md.convert(content)
            else:
                html_sections[key] = content

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{sections.get('name', 'Resume')}</title>
</head>
<body>
    <header>
        <h1>{sections.get('name', '')}</h1>
        <p class="contact">{sections.get('contact', '')}</p>
    </header>

    {self._render_section('Professional Summary', html_sections.get('professional_summary', ''))}
    {self._render_section('Professional Experience', html_sections.get('professional_experience', ''))}
    {self._render_section('Technical Skills', html_sections.get('technical_skills', ''))}
    {self._render_section('Education', html_sections.get('education', ''))}
    {self._render_section('Notable Projects', html_sections.get('notable_projects', ''))}
</body>
</html>"""

    def _render_section(self, title: str, content: str) -> str:
        """Render a section if content exists."""
        if not content.strip():
            return ''
        return f"""
    <section>
        <h2>{title}</h2>
        {content}
    </section>"""

    def get_css(self) -> str:
        """Professional template CSS."""
        return """
        @page {
            margin: 0.75in;
            size: letter;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
            max-width: none;
            margin: 0;
        }

        header {
            text-align: center;
            margin-bottom: 20pt;
        }

        h1 {
            font-size: 24pt;
            font-weight: 600;
            margin: 0 0 8pt 0;
            color: #1a1a1a;
        }

        .contact {
            font-size: 10pt;
            color: #666;
            margin: 0;
        }

        h2 {
            font-size: 14pt;
            font-weight: 600;
            margin: 16pt 0 8pt 0;
            color: #2c2c2c;
            border-bottom: 1pt solid #ddd;
            padding-bottom: 4pt;
        }

        h3 {
            font-size: 12pt;
            font-weight: 600;
            margin: 12pt 0 4pt 0;
            color: #333;
        }

        p {
            margin: 0 0 8pt 0;
        }

        ul {
            margin: 4pt 0 8pt 0;
            padding-left: 16pt;
        }

        li {
            margin: 2pt 0;
        }

        /* Prevent awkward page breaks */
        h2, h3 {
            page-break-after: avoid;
        }

        li {
            page-break-inside: avoid;
        }

        section {
            page-break-inside: avoid;
        }
        """


class ModernTemplate(PDFTemplate):
    """Modern template with color accents."""

    def generate_html(self, sections: Dict[str, str]) -> str:
        """Generate modern HTML layout."""
        # Convert markdown content to HTML for each section
        md = markdown.Markdown()

        html_sections = {}
        for key, content in sections.items():
            if key not in ['name', 'contact']:
                html_sections[key] = md.convert(content)
            else:
                html_sections[key] = content

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{sections.get('name', 'Resume')}</title>
</head>
<body>
    <header>
        <h1>{sections.get('name', '')}</h1>
        <div class="contact-box">
            <p>{sections.get('contact', '')}</p>
        </div>
    </header>

    {self._render_section('Summary', html_sections.get('professional_summary', ''))}
    {self._render_section('Experience', html_sections.get('professional_experience', ''))}
    {self._render_section('Skills', html_sections.get('technical_skills', ''))}
    {self._render_section('Education', html_sections.get('education', ''))}
    {self._render_section('Projects', html_sections.get('notable_projects', ''))}
</body>
</html>"""

    def _render_section(self, title: str, content: str) -> str:
        """Render a section if content exists."""
        if not content.strip():
            return ''
        return f"""
    <section>
        <h2>{title}</h2>
        <div class="section-content">
            {content}
        </div>
    </section>"""

    def get_css(self) -> str:
        """Modern template CSS with color accents."""
        return """
        @page {
            margin: 0.75in;
            size: letter;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #2d3748;
            max-width: none;
            margin: 0;
        }

        header {
            text-align: center;
            margin-bottom: 24pt;
        }

        h1 {
            font-size: 28pt;
            font-weight: 700;
            margin: 0 0 12pt 0;
            color: #1a202c;
            letter-spacing: -0.02em;
        }

        .contact-box {
            background-color: #f7fafc;
            padding: 8pt 12pt;
            border-radius: 4pt;
            border-left: 3pt solid #2b6cb0;
            display: inline-block;
        }

        .contact-box p {
            font-size: 10pt;
            color: #718096;
            margin: 0;
            font-weight: 500;
        }

        h2 {
            font-size: 16pt;
            font-weight: 600;
            margin: 20pt 0 10pt 0;
            color: #2b6cb0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 2pt solid #e2e8f0;
            padding-bottom: 6pt;
        }

        h3 {
            font-size: 13pt;
            font-weight: 600;
            margin: 14pt 0 6pt 0;
            color: #2d3748;
        }

        p {
            margin: 0 0 10pt 0;
        }

        ul {
            margin: 6pt 0 10pt 0;
            padding-left: 18pt;
        }

        li {
            margin: 3pt 0;
            position: relative;
        }

        li::marker {
            color: #2b6cb0;
        }

        .section-content {
            margin-left: 6pt;
        }

        /* Page breaks */
        h2, h3 {
            page-break-after: avoid;
        }

        li {
            page-break-inside: avoid;
        }

        section {
            page-break-inside: avoid;
        }
        """


class PDFGenerator:
    """Convert markdown resume to PDF with template support."""

    def __init__(self):
        self.templates = {
            'professional': ProfessionalTemplate(),
            'modern': ModernTemplate(),
        }

    def generate(self, content: str, output_path: Path, template: str = 'professional') -> Path:
        """Generate PDF from markdown content using specified template."""
        if template not in self.templates:
            available = ', '.join(self.templates.keys())
            raise ValueError(f"Unknown template '{template}'. Available: {available}")

        # Get template
        tmpl = self.templates[template]

        # Parse markdown into sections
        sections = tmpl.parse_sections(content)

        # Generate HTML
        html = tmpl.generate_html(sections)

        # Get CSS
        css = tmpl.get_css()

        # Generate PDF
        pdf_path = output_path.with_suffix('.pdf')
        HTML(string=html).write_pdf(
            pdf_path,
            stylesheets=[CSS(string=css)]
        )

        return pdf_path

    def get_available_templates(self) -> list[str]:
        """Get list of available template names."""
        return list(self.templates.keys())

