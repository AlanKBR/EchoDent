from __future__ import annotations

from typing import Any, Mapping

from flask import render_template
from weasyprint import HTML as WeasyPrint


def generate_pdf(
    template_name_or_string: str,
    context: Mapping[str, Any],
    base_url: str,
) -> bytes:
    """Render a Jinja template and return a PDF as bytes using WeasyPrint.

    - template_name_or_string: Jinja template path under templates/
    - context: Dict of variables to render in the template
    - base_url: Base URL for resolving relative assets (CSS, images)
    """
    html_string = render_template(template_name_or_string, **(context or {}))

    # Instantiate WeasyPrint with the rendered HTML
    doc = WeasyPrint(string=html_string, base_url=base_url)

    # Generate PDF bytes (ensure bytes fallback to satisfy type checkers)
    pdf_bytes = doc.write_pdf() or b""
    return pdf_bytes
