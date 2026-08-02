from .utils import get_font_size, get_font_color


def extract_run_style(run):
    """
    Extract formatting information from a DOCX run.
    """

    font = run.font

    style = {

        # ==========================
        # Font Information
        # ==========================
        "font_name": font.name,
        "font_size": get_font_size(font.size),
        "font_color": get_font_color(font.color),

        # ==========================
        # Basic Formatting
        # ==========================
        "bold": font.bold,
        "italic": font.italic,
        "underline": font.underline,

        # ==========================
        # Highlight
        # ==========================
        "highlight_color": (
            str(font.highlight_color)
            if font.highlight_color is not None
            else None
        ),

        # ==========================
        # Text Effects
        # ==========================
        "strike": font.strike,
        "double_strike": font.double_strike,

        "all_caps": font.all_caps,
        "small_caps": font.small_caps,

        "subscript": font.subscript,
        "superscript": font.superscript,

        "hidden": font.hidden,
        "outline": font.outline,
        "shadow": font.shadow,
        "emboss": font.emboss,
        "imprint": font.imprint,

        # ==========================
        # Advanced Properties
        # ==========================
        "rtl": font.rtl,
        "complex_script": font.complex_script,
        "cs_bold": font.cs_bold,
        "cs_italic": font.cs_italic,

        # ==========================
        # Style Information
        # ==========================
        #"language_id": str(font.lang) if font.lang else None,
        #"style": run.style.name if run.style else None,

    }

    return style