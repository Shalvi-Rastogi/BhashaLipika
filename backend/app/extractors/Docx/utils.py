from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


def get_font_size(size):
    """
    Convert font size to points.
    """
    if size is None:
        return None
    return round(size.pt, 2)


def get_font_color(color):
    """
    Extract font color information.
    Supports both RGB and Theme colors.
    """

    if color is None:
        return None

    # RGB Color
    if color.rgb:
        return {
            "type": "rgb",
            "value": str(color.rgb)
        }

    # Theme Color
    if color.theme_color:
        return {
            "type": "theme",
            "value": str(color.theme_color)
        }

    return None


def get_alignment(alignment):
    """
    Convert alignment enum to readable string.
    """

    alignment_map = {
        WD_PARAGRAPH_ALIGNMENT.LEFT: "left",
        WD_PARAGRAPH_ALIGNMENT.CENTER: "center",
        WD_PARAGRAPH_ALIGNMENT.RIGHT: "right",
        WD_PARAGRAPH_ALIGNMENT.JUSTIFY: "justify",
        WD_PARAGRAPH_ALIGNMENT.DISTRIBUTE: "distribute",
        WD_PARAGRAPH_ALIGNMENT.JUSTIFY_MED: "justify_medium",
        WD_PARAGRAPH_ALIGNMENT.JUSTIFY_HI: "justify_high",
        WD_PARAGRAPH_ALIGNMENT.JUSTIFY_LOW: "justify_low",
    }

    return alignment_map.get(alignment, "left")


def get_indent(indent):
    if indent is None:
        return None
    return round(indent.pt, 2)


def get_spacing(space):
    if space is None:
        return None
    return round(space.pt, 2)


def get_line_spacing(line_spacing):
    if line_spacing is None:
        return None

    if isinstance(line_spacing, (int, float)):
        return line_spacing

    try:
        return round(line_spacing.pt, 2)
    except AttributeError:
        return line_spacing