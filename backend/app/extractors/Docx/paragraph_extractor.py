import re

from docx.text.paragraph import Paragraph

from .style_extractor import extract_run_style
from .utils import (
    get_alignment,
    get_indent,
    get_spacing,
    get_line_spacing,
)


def detect_list(paragraph):
    """
    Detect whether a paragraph is a numbered or bulleted list.

    Returns:
        (is_list, list_type)
    """

    # -------------------------------
    # Word Numbering/Bullets
    # -------------------------------
    pPr = paragraph._p.pPr

    if pPr is not None and pPr.numPr is not None:

        text = paragraph.text.strip()

        if re.match(r"^\d+[.)]", text):
            return True, "numbered"

        return True, "bulleted"

    # -------------------------------
    # Style-based Lists
    # -------------------------------
    style_name = paragraph.style.name.lower() if paragraph.style else ""

    if "list bullet" in style_name:
        return True, "bulleted"

    if "list number" in style_name:
        return True, "numbered"

    # -------------------------------
    # Manually Typed Numbering
    # -------------------------------
    text = paragraph.text.strip()

    if re.match(r"^\d+[.)]\s+", text):
        return True, "numbered"

    if re.match(r"^[a-zA-Z][.)]\s+", text):
        return True, "numbered"

    # -------------------------------
    # Manually Typed Bullets
    # -------------------------------
    if re.match(r"^[•\-*]\s+", text):
        return True, "bulleted"

    return False, None


def process_paragraph(block, element_id):
    """
    Process a DOCX paragraph.

    Supports:
    - Headings
    - Paragraphs
    - Numbered Lists
    - Bulleted Lists
    """

    if not isinstance(block, Paragraph):
        return None

    if not block.text.strip():
        return None

    style_name = block.style.name if block.style else "Normal"

    element_type = "paragraph"
    level = None
    list_type = None

    # -----------------------------------
    # Heading
    # -----------------------------------
    if style_name.startswith("Heading"):

        element_type = "heading"

        try:
            level = int(style_name.split()[-1])
        except (ValueError, IndexError):
            level = 1

    else:

        is_list, list_type = detect_list(block)

        if is_list:
            element_type = "list_item"

    # -----------------------------------
    # Runs
    # -----------------------------------
    runs = []

    for run in block.runs:

        if not run.text:
            continue

        runs.append(
            {
                "text": run.text,
                "style": extract_run_style(run),
            }
        )

    # -----------------------------------
    # Paragraph Formatting
    # -----------------------------------
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

    # -----------------------------------
    # Final JSON
    # -----------------------------------
    return {

        "id": element_id,

        "type": element_type,

        "list_type": list_type,

        "level": level,

        "order": element_id,

        "text": block.text.strip(),

        "runs": runs,

        "paragraph_style": paragraph_style,

    }