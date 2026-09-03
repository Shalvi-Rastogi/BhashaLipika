from .utils import get_font_size, get_font_color

def extract_run_style(run):
    """
    Extract formatting information from a DOCX run with Style Inheritance.
    """
    font = run.font

    # 1. Direct explicit formatting check karein
    is_bold = font.bold
    is_italic = font.italic
    is_underline = font.underline

    # 2. Inherited from Character Style check karein
    if run.style and run.style.font:
        if is_bold is None: is_bold = run.style.font.bold
        if is_italic is None: is_italic = run.style.font.italic
        if is_underline is None: is_underline = run.style.font.underline

    # 3. Inherited from Parent Paragraph Style check karein (Sabse zaroori step)
    try:
        paragraph = run._parent
        if paragraph and hasattr(paragraph, 'style') and paragraph.style and paragraph.style.font:
            if is_bold is None: is_bold = paragraph.style.font.bold
            if is_italic is None: is_italic = paragraph.style.font.italic
            if is_underline is None: is_underline = paragraph.style.font.underline
    except Exception:
        pass

    # Ensure karein ki JSON mein 'null' na jaye (Convert None to False)
    final_bold = bool(is_bold)
    final_italic = bool(is_italic)
    final_underline = bool(is_underline)
    
    # Complex script bold (Hindi ke liye) ko direct bold se sync karein
    cs_bold = font.cs_bold
    if cs_bold is None:
        cs_bold = final_bold
    else:
        cs_bold = bool(cs_bold)

    style = {

        # ==========================
        # Font Information
        # ==========================
        "font_name": font.name,
        "font_size": get_font_size(font.size),
        "font_color": get_font_color(font.color),

        # ==========================
        # Basic Formatting (FIXED: Inheritance applied)
        # ==========================
        "bold": final_bold,
        "italic": final_italic,
        "underline": final_underline,

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
        "cs_bold": cs_bold,
        "cs_italic": bool(font.cs_italic) if font.cs_italic is not None else final_italic,

        # ==========================
        # Style Information
        # ==========================
        #"language_id": str(font.lang) if font.lang else None,
        #"style": run.style.name if run.style else None,

    }

    return style