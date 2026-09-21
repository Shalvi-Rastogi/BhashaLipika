def extract_cell_style(cell):
    # DOCX format jaisa rich structure
    style_data = {
        "font_name": None,
        "font_size": None,
        "font_color": None,
        "bold": False,
        "italic": False,
        "underline": False,
        "highlight_color": None,
        "strike": None,
        "double_strike": None,
        "all_caps": None,
        "small_caps": None,
        "subscript": None,
        "superscript": None,
        "hidden": None,
        "outline": None,
        "shadow": None,
        "emboss": None,
        "imprint": None,
        "rtl": None,
        "complex_script": None,
        "cs_bold": None,
        "cs_italic": None
    }
    
    if cell.font:
        style_data["font_name"] = cell.font.name
        style_data["font_size"] = cell.font.size
        style_data["bold"] = cell.font.bold
        style_data["italic"] = cell.font.italic
        style_data["strike"] = cell.font.strikethrough
        
        # Excel underline check
        if cell.font.underline:
            style_data["underline"] = True
            
        # Extract Font Color if it exists (openpyxl rgb formatting)
        if cell.font.color and hasattr(cell.font.color, 'rgb') and cell.font.color.rgb:
            style_data["font_color"] = {
                "type": "rgb",
                "value": str(cell.font.color.rgb)
            }
            
    return style_data