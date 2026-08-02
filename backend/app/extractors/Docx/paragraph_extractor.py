from docx.text.paragraph import Paragraph

from .style_extractor import extract_run_style
from .utils import (
    get_alignment,
    get_indent,
    get_spacing,
    get_line_spacing,
)


def process_paragraph(block, element_id):
    """
    Process a DOCX paragraph and return it as a JSON element.

    Handles:
    - Headings
    - Paragraphs
    - Run formatting
    - Paragraph formatting
    """

    # --------------------------------------------------
    # Ignore non-paragraph blocks
    # --------------------------------------------------
    if not isinstance(block, Paragraph):
        return None

    # --------------------------------------------------
    # Skip empty paragraphs
    # --------------------------------------------------
    if not block.text.strip():
        return None

    # --------------------------------------------------
    # Style Name
    # --------------------------------------------------
    style_name = block.style.name if block.style else "Normal"

    # --------------------------------------------------
    # Detect Heading
    # --------------------------------------------------
    element_type = "paragraph"
    level = None

    if style_name.startswith("Heading"):

        element_type = "heading"

        try:
            level = int(style_name.split()[-1])
        except (ValueError, IndexError):
            level = 1

    # --------------------------------------------------
    # Extract Runs
    # --------------------------------------------------
    runs = []

    for run in block.runs:

        # Skip empty runs
        if not run.text:
            continue

        runs.append(
            {
                "text": run.text,
                "style": extract_run_style(run),
            }
        )

    # --------------------------------------------------
    # Paragraph Formatting
    # --------------------------------------------------
    paragraph_style = {

        "style_name": style_name,

        "alignment": get_alignment(block.alignment),

        "left_indent": get_indent(
            block.paragraph_format.left_indent
        ),

        "right_indent": get_indent(
            block.paragraph_format.right_indent
        ),

        "first_line_indent": get_indent(
            block.paragraph_format.first_line_indent
        ),

        "line_spacing": get_line_spacing(
            block.paragraph_format.line_spacing
        ),

        "space_before": get_spacing(
            block.paragraph_format.space_before
        ),

        "space_after": get_spacing(
            block.paragraph_format.space_after
        ),

        "keep_together": block.paragraph_format.keep_together,

        "keep_with_next": block.paragraph_format.keep_with_next,

        "page_break_before": block.paragraph_format.page_break_before,

        "widow_control": block.paragraph_format.widow_control,
    }

    # --------------------------------------------------
    # Final JSON Element
    # --------------------------------------------------
    element = {

        "id": element_id,

        "type": element_type,

        "level": level,

        "order": element_id,

        "text": block.text,

        "runs": runs,

        "paragraph_style": paragraph_style,

    }

    return element