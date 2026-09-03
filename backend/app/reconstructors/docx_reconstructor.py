from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import json
import os
import re
import zipfile

from docx.oxml.shared import OxmlElement
from docx.oxml.ns import qn

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# FONT CONFIGURATION
# ============================================================

DEVANAGARI_FONT_NAME = "Nirmala UI"

DEVANAGARI_FONT_PATHS = [
    r"C:\Windows\Fonts\Nirmala.ttf",
    r"C:\Windows\Fonts\NirmalaUI.ttf",
    r"C:\Windows\Fonts\Nirmala.ttc",
    r"C:\Windows\Fonts\Mangal.ttf",
    r"C:\Windows\Fonts\Kokila.ttf",
    r"C:\Windows\Fonts\kokila.ttf",
]


def get_font_path():
    """
    Find a Devanagari-compatible font for PIL image reconstruction.
    """

    for font_path in DEVANAGARI_FONT_PATHS:
        if os.path.exists(font_path):
            return font_path

    return None


# ============================================================
# SCRIPT DETECTION
# ============================================================

def contains_devanagari(text):
    """
    Check whether text contains Devanagari characters.
    """

    if not text:
        return False

    for char in text:
        if "\u0900" <= char <= "\u097F":
            return True

    return False


# ============================================================
# WORD FONT SUPPORT
# ============================================================

def apply_devanagari_font(run, text):
    """
    Set a Devanagari-compatible complex-script font
    without unnecessarily changing Latin font.
    """

    if not contains_devanagari(text):
        return

    rPr = run._element.get_or_add_rPr()

    rFonts = rPr.find(qn("w:rFonts"))

    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)

    # Complex script font
    rFonts.set(qn("w:cs"), DEVANAGARI_FONT_NAME)

    # East Asian fallback
    rFonts.set(qn("w:eastAsia"), DEVANAGARI_FONT_NAME)


# ============================================================
# APPLY RUN STYLE
# ============================================================

def apply_style_to_run(run, style_dict):
    """
    Apply extracted run formatting to a reconstructed run.
    """

    if not style_dict:
        return

    font_name = style_dict.get("font_name")
    is_bold = style_dict.get("bold")
    is_italic = style_dict.get("italic")
    is_underline = style_dict.get("underline")

    # --------------------------------------------------------
    # Heavy font detection
    # --------------------------------------------------------

    if font_name:
        lower_font = font_name.lower()

        if "black" in lower_font or "bold" in lower_font:
            is_bold = True

    # --------------------------------------------------------
    # Basic formatting
    # --------------------------------------------------------

    if is_bold is not None:
        run.bold = is_bold

    if is_italic is not None:
        run.italic = is_italic

    if is_underline is not None:
        run.underline = is_underline

    for property_name in (
        "strike",
        "double_strike",
        "all_caps",
        "small_caps",
        "subscript",
        "superscript",
        "hidden",
        "outline",
        "shadow",
        "emboss",
        "imprint",
    ):
        property_value = style_dict.get(property_name)

        if property_value is not None:
            setattr(run.font, property_name, property_value)

    # --------------------------------------------------------
    # Font name
    # --------------------------------------------------------

    if font_name:
        try:
            run.font.name = font_name
        except Exception:
            pass

    # --------------------------------------------------------
    # Font size
    # --------------------------------------------------------

    font_size = style_dict.get("font_size")

    if font_size:
        try:
            run.font.size = Pt(float(font_size))
        except Exception:
            pass

    # --------------------------------------------------------
    # Font color
    # --------------------------------------------------------

    font_color = style_dict.get("font_color")

    if isinstance(font_color, dict):

        if font_color.get("type") == "rgb":

            hex_value = font_color.get("value")

            if hex_value:
                try:
                    run.font.color.rgb = RGBColor.from_string(hex_value)
                except Exception:
                    pass

    # --------------------------------------------------------
    # Complex script formatting
    # --------------------------------------------------------

    rPr = run._element.get_or_add_rPr()

    if is_bold is True:

        bCs = rPr.find(qn("w:bCs"))

        if bCs is None:
            bCs = OxmlElement("w:bCs")
            rPr.append(bCs)

        bCs.set(qn("w:val"), "1")

    if is_italic is True:

        iCs = rPr.find(qn("w:iCs"))

        if iCs is None:
            iCs = OxmlElement("w:iCs")
            rPr.append(iCs)

        iCs.set(qn("w:val"), "1")

    if font_size:

        szCs = rPr.find(qn("w:szCs"))

        if szCs is None:
            szCs = OxmlElement("w:szCs")
            rPr.append(szCs)

        try:
            szCs.set(
                qn("w:val"),
                str(int(float(font_size) * 2))
            )
        except Exception:
            pass

    # --------------------------------------------------------
    # Devanagari font
    # --------------------------------------------------------

    apply_devanagari_font(
        run,
        run.text
    )


# ============================================================
# APPLY PARAGRAPH STYLE
# ============================================================

def apply_paragraph_style(paragraph, paragraph_style):
    """
    Apply paragraph-level formatting.
    """

    if not paragraph_style:
        return

    alignment = paragraph_style.get("alignment")

    if alignment:

        alignment_map = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }

        if alignment in alignment_map:
            paragraph.alignment = alignment_map[alignment]

    for property_name in (
        "left_indent",
        "right_indent",
        "first_line_indent",
        "space_before",
        "space_after",
    ):
        property_value = paragraph_style.get(property_name)

        if property_value is not None:
            setattr(
                paragraph.paragraph_format,
                property_name,
                Pt(float(property_value))
            )

    line_spacing = paragraph_style.get("line_spacing")

    if line_spacing is not None:
        paragraph.paragraph_format.line_spacing = (
            float(line_spacing)
        )

    for property_name in (
        "keep_together",
        "keep_with_next",
        "page_break_before",
        "widow_control",
    ):
        property_value = paragraph_style.get(property_name)

        if property_value is not None:
            setattr(
                paragraph.paragraph_format,
                property_name,
                property_value
            )


# ============================================================
# ADD TEXT TO PARAGRAPH
# ============================================================

def populate_paragraph(paragraph, paragraph_data):
    """
    Replace paragraph content while preserving paragraph properties.
    """

    # Clear only runs/content.
    # Paragraph formatting remains intact.
    paragraph.clear()

    paragraph_style = paragraph_data.get(
        "paragraph_style",
        {}
    )

    apply_paragraph_style(
        paragraph,
        paragraph_style
    )

    runs_data = paragraph_data.get(
        "runs",
        []
    )

    if runs_data:

        for run_data in runs_data:

            text = run_data.get(
                "text",
                ""
            )

            if not text:
                continue

            style = run_data.get(
                "style",
                {}
            )

            # Handle newline inside a run
            lines = text.split("\n")

            for index, line in enumerate(lines):

                if line:
                    new_run = paragraph.add_run(line)

                    apply_style_to_run(
                        new_run,
                        style
                    )

                if index < len(lines) - 1:

                    if paragraph.runs:
                        paragraph.runs[-1].add_break()

    else:

        text = paragraph_data.get(
            "text",
            ""
        )

        if text:

            run = paragraph.add_run(text)

            apply_style_to_run(
                run,
                {}
            )


# ============================================================
# RECONSTRUCT NORMAL PARAGRAPHS
# ============================================================

def reconstruct_paragraphs(document, elements):

    print("\n========== PARAGRAPH RECONSTRUCTION ==========")

    text_elements = [
        element
        for element in elements
        if element.get("type")
        in [
            "paragraph",
            "heading",
            "list_item"
        ]
    ]

    original_paragraphs = [
        paragraph
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    print(
        "Original paragraphs:",
        len(original_paragraphs)
    )

    print(
        "Translated text elements:",
        len(text_elements)
    )

    for index, (paragraph, element) in enumerate(zip(
        original_paragraphs,
        text_elements
    )):

        element_text = element.get(
            "text",
            ""
        ).strip()

        if (
            element_text.lower() in {
                "secretary-general",
                "महासचिव"
            }
            and index > 0
            and text_elements[index - 1].get(
                "text",
                ""
            ).strip().endswith(",")
        ):
            continue

        runs_data = element.get(
            "runs",
            []
        )

        paragraph_style = element.get(
            "paragraph_style",
            {}
        )

        paragraph.clear()

        apply_paragraph_style(
            paragraph,
            paragraph_style
        )

        current_text = element.get(
            "text",
            ""
        ).strip()

        is_numbered_heading = (
            element.get("type") == "list_item"
            and re.match(
                r"^\s*\d+[.)]\s+",
                current_text
            ) is not None
        )

        if (
            current_text.lower() in {
                "secretary-general",
                "महासचिव"
            }
            and index > 0
            and text_elements[index - 1].get(
                "text",
                ""
            ).strip().endswith(",")
        ):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        if index + 1 < len(text_elements):
            next_text = text_elements[index + 1].get(
                "text",
                ""
            ).strip().lower()

            if (
                current_text.endswith(",")
                and next_text in {
                    "secretary-general",
                    "महासचिव"
                }
            ):
                previous_element = paragraph._p.getprevious()

                while previous_element is not None:
                    has_text = any(
                        node.tag == qn("w:t")
                        and node.text
                        and node.text.strip()
                        for node in previous_element.iter()
                    )

                    if has_text or previous_element.tag != qn("w:p"):
                        break

                    previous_element.getparent().remove(
                        previous_element
                    )
                    previous_element = paragraph._p.getprevious()

                next_element = text_elements[index + 1]
                runs_data = runs_data + [
                    {
                        "text": "\n",
                        "style": {}
                    }
                ] + next_element.get("runs", [])

                paragraph.paragraph_format.keep_with_next = False
                paragraph.paragraph_format.keep_together = False
                paragraph.paragraph_format.page_break_before = False
                paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

                paragraph_properties = paragraph._p.pPr

                if paragraph_properties is not None:
                    numbering_properties = paragraph_properties.numPr

                    if numbering_properties is not None:
                        paragraph_properties.remove(
                            numbering_properties
                        )

                paragraph.paragraph_format.left_indent = None
                paragraph.paragraph_format.right_indent = None
                paragraph.paragraph_format.first_line_indent = None
                paragraph.paragraph_format.left_indent = None

                next_paragraph = original_paragraphs[index + 1]
                next_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                next_paragraph.paragraph_format.left_indent = None
                next_paragraph.paragraph_format.right_indent = None
                next_paragraph.paragraph_format.first_line_indent = None
                paragraph_element = paragraph._p
                paragraph_element.addnext(
                    next_paragraph._p
                )
                paragraph_element.getnext().getparent().remove(
                    paragraph_element.getnext()
                )

        if runs_data:

            for run_data in runs_data:

                text = run_data.get(
                    "text",
                    ""
                )

                text = text.replace(
                    ". . f..",
                    "w.e.f."
                )

                if not text:
                    continue

                style = run_data.get(
                    "style",
                    {}
                )

                if is_numbered_heading:
                    style = dict(style)
                    style["bold"] = True

                lines = text.split("\n")

                for index, line in enumerate(lines):

                    if line:

                        new_run = paragraph.add_run(
                            line
                        )

                        apply_style_to_run(
                            new_run,
                            style
                        )

                    if index < len(lines) - 1:

                        if paragraph.runs:
                            paragraph.runs[-1].add_break()

        else:

            text = element.get(
                "text",
                ""
            )

            if text:

                new_run = paragraph.add_run(
                    text
                )

                apply_style_to_run(
                    new_run,
                    {}
                )


# ============================================================
# GET PARAGRAPH DATA
# ============================================================

def get_paragraph_data_list(cell_data):
    """
    Safely get paragraph data from JSON.
    """

    paragraphs = cell_data.get(
        "paragraphs",
        []
    )

    if not isinstance(paragraphs, list):
        return []

    return paragraphs


# ============================================================
# RECONSTRUCT CELL PARAGRAPHS
# ============================================================

def reconstruct_cell_paragraphs(
    cell,
    cell_data
):
    """
    Reconstruct text inside a table cell.

    IMPORTANT:
    This function does NOT delete nested tables.
    """

    nested_tables_data = cell_data.get(
        "nested_tables",
        []
    )

    paragraph_data_list = get_paragraph_data_list(
        cell_data
    )

    # --------------------------------------------------------
    # If cell contains nested table
    # --------------------------------------------------------

    if nested_tables_data:

        # The outer cell normally contains only an empty
        # paragraph before the nested table.
        #
        # Do NOT write cell.text here.
        #
        # Only update actual nested tables later.

        for paragraph in cell.paragraphs:

            if paragraph.text.strip():

                # Only clear unexpected direct text.
                paragraph.clear()

        return

    # --------------------------------------------------------
    # Normal table cell
    # --------------------------------------------------------

    if not paragraph_data_list:

        text = cell_data.get(
            "text",
            ""
        )

        if text:

            paragraph = (
                cell.paragraphs[0]
                if cell.paragraphs
                else cell.add_paragraph()
            )

            paragraph.clear()

            run = paragraph.add_run(
                text
            )

            apply_style_to_run(
                run,
                {}
            )

        return

    # --------------------------------------------------------
    # Populate paragraphs
    # --------------------------------------------------------

    existing_paragraphs = cell.paragraphs

    for index, paragraph_data in enumerate(
        paragraph_data_list
    ):

        if index < len(existing_paragraphs):

            paragraph = existing_paragraphs[index]

        else:

            paragraph = cell.add_paragraph()

        populate_paragraph(
            paragraph,
            paragraph_data
        )

    # --------------------------------------------------------
    # Clear extra original paragraphs
    # --------------------------------------------------------

    for index in range(
        len(paragraph_data_list),
        len(existing_paragraphs)
    ):

        existing_paragraphs[index].clear()


# ============================================================
# RECONSTRUCT NESTED TABLE
# ============================================================

def reconstruct_existing_nested_table(
    existing_table,
    table_data,
    level=1
):
    """
    IMPORTANT:

    Reconstructs an ALREADY EXISTING nested table.

    It does NOT create a new table.

    This preserves:
        - borders
        - width
        - row height
        - column width
        - cell margins
        - table position
        - original table structure
    """

    print(
        f"      Nested table level {level}: "
        f"{len(existing_table.rows)} rows x "
        f"{len(existing_table.columns)} columns"
    )

    rows_data = table_data.get(
        "rows",
        []
    )

    # --------------------------------------------------------
    # Process existing rows
    # --------------------------------------------------------

    for row_data in rows_data:

        row_index = row_data.get(
            "row_index"
        )

        if row_index is None:
            continue

        if row_index >= len(existing_table.rows):
            print(
                f"      Warning: row {row_index} "
                f"does not exist in original table."
            )
            continue

        existing_row = existing_table.rows[
            row_index
        ]

        cells_data = row_data.get(
            "cells",
            []
        )

        for cell_data in cells_data:

            column_index = cell_data.get(
                "column"
            )

            if column_index is None:
                column_index = cell_data.get(
                    "cell_index"
                )

            if column_index is None:
                continue

            if column_index >= len(existing_row.cells):
                print(
                    f"      Warning: column "
                    f"{column_index} does not exist."
                )
                continue

            existing_cell = existing_row.cells[
                column_index
            ]

            # ------------------------------------------------
            # Update direct cell text
            # ------------------------------------------------

            reconstruct_cell_paragraphs(
                existing_cell,
                cell_data
            )

            # ------------------------------------------------
            # Handle deeper nested tables
            # ------------------------------------------------

            nested_tables_data = cell_data.get(
                "nested_tables",
                []
            )

            if nested_tables_data:

                existing_nested_tables = (
                    existing_cell.tables
                )

                for nested_index, nested_data in enumerate(
                    nested_tables_data
                ):

                    if nested_index < len(
                        existing_nested_tables
                    ):

                        reconstruct_existing_nested_table(
                            existing_nested_tables[
                                nested_index
                            ],
                            nested_data,
                            level + 1
                        )

                    else:

                        print(
                            "      Warning: JSON contains "
                            "an additional nested table "
                            "that does not exist in "
                            "original DOCX."
                        )


# ============================================================
# RECONSTRUCT TOP-LEVEL TABLE
# ============================================================

def reconstruct_existing_table(
    existing_table,
    table_data
):
    """
    Reconstruct a top-level table by modifying
    the original table in-place.
    """

    rows_data = table_data.get(
        "rows",
        []
    )

    for row_data in rows_data:

        row_index = row_data.get(
            "row_index"
        )

        if row_index is None:
            continue

        if row_index >= len(existing_table.rows):
            continue

        existing_row = existing_table.rows[
            row_index
        ]

        cells_data = row_data.get(
            "cells",
            []
        )

        for cell_data in cells_data:

            column_index = cell_data.get(
                "column"
            )

            if column_index is None:
                column_index = cell_data.get(
                    "cell_index"
                )

            if column_index is None:
                continue

            if column_index >= len(existing_row.cells):
                continue

            existing_cell = existing_row.cells[
                column_index
            ]

            # ------------------------------------------------
            # Normal cell / outer cell text
            # ------------------------------------------------

            reconstruct_cell_paragraphs(
                existing_cell,
                cell_data
            )

            # ------------------------------------------------
            # Nested table
            # ------------------------------------------------

            nested_tables_data = cell_data.get(
                "nested_tables",
                []
            )

            if nested_tables_data:

                original_nested_tables = (
                    existing_cell.tables
                )

                for nested_index, nested_data in enumerate(
                    nested_tables_data
                ):

                    if nested_index < len(
                        original_nested_tables
                    ):

                        reconstruct_existing_nested_table(
                            original_nested_tables[
                                nested_index
                            ],
                            nested_data,
                            level=1
                        )

                    else:

                        print(
                            "WARNING: Nested table "
                            "exists in JSON but not "
                            "in original DOCX."
                        )


# ============================================================
# TABLE RECONSTRUCTION
# ============================================================

def reconstruct_tables(
    document,
    elements
):

    print(
        "\n========== TABLE RECONSTRUCTION =========="
    )

    table_elements = [
        element
        for element in elements
        if element.get("type") == "table"
    ]

    original_tables = document.tables

    print(
        "Original top-level tables:",
        len(original_tables)
    )

    print(
        "Translated top-level tables:",
        len(table_elements)
    )

    for table_index, table in enumerate(
        original_tables
    ):

        translated_table = None

        # ----------------------------------------------------
        # First try table_index
        # ----------------------------------------------------

        for element in table_elements:

            if element.get("table_index") == table_index:

                translated_table = element
                break

        # ----------------------------------------------------
        # Fallback: order
        # ----------------------------------------------------

        if translated_table is None:

            if table_index < len(table_elements):

                translated_table = (
                    table_elements[table_index]
                )

        if translated_table is None:

            print(
                f"Skipping original table "
                f"{table_index}"
            )

            continue

        print(
            f"\nReconstructing top-level table "
            f"{table_index}"
        )

        reconstruct_existing_table(
            table,
            translated_table
        )


# ============================================================
# IMAGE FONT
# ============================================================

def get_image_font_path():

    return get_font_path()


# ============================================================
# IMAGE FONT SIZE
# ============================================================

def calculate_font_size(
    draw,
    text,
    box_width,
    box_height,
    font_path
):
    """
    Calculate the largest possible font that fits
    inside OCR bounding box.
    """

    if not font_path:
        return ImageFont.load_default()

    if not text:
        return ImageFont.load_default()

    # Start from original OCR box height
    font_size = max(
        8,
        int(box_height * 0.80)
    )

    while font_size >= 8:

        try:

            font = ImageFont.truetype(
                font_path,
                font_size
            )

            bbox = draw.textbbox(
                (0, 0),
                text,
                font=font
            )

            text_width = (
                bbox[2] - bbox[0]
            )

            text_height = (
                bbox[3] - bbox[1]
            )

            if (
                text_width <= box_width
                and text_height <= box_height
            ):
                return font

            font_size -= 1

        except Exception:

            break

    try:

        return ImageFont.truetype(
            font_path,
            8
        )

    except Exception:

        return ImageFont.load_default()


# ============================================================
# BACKGROUND COLOR
# ============================================================

def get_background_color(
    image,
    x1,
    y1,
    x2,
    y2
):

    try:

        pixels = []

        sample_points = [
            (
                max(0, x1 - 2),
                max(0, y1)
            ),
            (
                max(0, x1 - 2),
                min(image.height - 1, y2)
            ),
            (
                min(image.width - 1, x2 + 2),
                max(0, y1)
            ),
            (
                min(image.width - 1, x2 + 2),
                min(image.height - 1, y2)
            )
        ]

        for point in sample_points:

            pixel = image.getpixel(
                point
            )

            if isinstance(pixel, tuple):

                if len(pixel) >= 3:
                    pixels.append(
                        pixel[:3]
                    )

        if pixels:

            r = sum(
                p[0] for p in pixels
            ) // len(pixels)

            g = sum(
                p[1] for p in pixels
            ) // len(pixels)

            b = sum(
                p[2] for p in pixels
            ) // len(pixels)

            return (
                r,
                g,
                b
            )

    except Exception:
        pass

    return "white"


# ============================================================
# IMAGE RECONSTRUCTION
# ============================================================

def reconstruct_image(
    original_image_path,
    image_element,
    output_image_path
):

    try:

        image = Image.open(
            original_image_path
        ).convert("RGB")

        draw = ImageDraw.Draw(
            image
        )

        ocr_details = image_element.get(
            "ocr_details",
            []
        )

        if not ocr_details:

            image.save(
                output_image_path
            )

            return True

        font_path = get_image_font_path()

        if font_path:

            print(
                f"Using image font: {font_path}"
            )

        else:

            print(
                "Devanagari image font not found."
            )

        for item in ocr_details:

            translated_text = item.get(
                "translated_text",
                ""
            )

            if not translated_text:

                translated_text = item.get(
                    "text",
                    ""
                )

            bbox = item.get(
                "bbox"
            )

            if not bbox or not translated_text:
                continue

            x1 = min(
                int(point[0])
                for point in bbox
            )

            y1 = min(
                int(point[1])
                for point in bbox
            )

            x2 = max(
                int(point[0])
                for point in bbox
            )

            y2 = max(
                int(point[1])
                for point in bbox
            )

            x1 = max(
                0,
                min(image.width - 1, x1)
            )

            y1 = max(
                0,
                min(image.height - 1, y1)
            )

            x2 = max(
                x1 + 1,
                min(image.width - 1, x2)
            )

            y2 = max(
                y1 + 1,
                min(image.height - 1, y2)
            )

            box_width = max(
                1,
                x2 - x1
            )

            box_height = max(
                1,
                y2 - y1
            )

            # ----------------------------------------------
            # Background
            # ----------------------------------------------

            background_color = (
                get_background_color(
                    image,
                    x1,
                    y1,
                    x2,
                    y2
                )
            )

            draw.rectangle(
                [
                    x1,
                    y1,
                    x2,
                    y2
                ],
                fill=background_color
            )

            # ----------------------------------------------
            # Font
            # ----------------------------------------------

            font = calculate_font_size(
                draw,
                translated_text,
                box_width,
                box_height,
                font_path
            )

            # ----------------------------------------------
            # Text bbox
            # ----------------------------------------------

            text_bbox = draw.textbbox(
                (0, 0),
                translated_text,
                font=font
            )

            text_width = (
                text_bbox[2]
                - text_bbox[0]
            )

            text_height = (
                text_bbox[3]
                - text_bbox[1]
            )

            # ----------------------------------------------
            # Center text
            # ----------------------------------------------

            text_x = (
                x1
                + (box_width - text_width) / 2
                - text_bbox[0]
            )

            text_y = (
                y1
                + (box_height - text_height) / 2
                - text_bbox[1]
            )

            draw.text(
                (
                    text_x,
                    text_y
                ),
                translated_text,
                fill="black",
                font=font
            )

        image.save(
            output_image_path
        )

        print(
            f"Reconstructed image saved: "
            f"{output_image_path}"
        )

        return True

    except Exception as e:

        print(
            f"Image reconstruction failed: {e}"
        )

        return False


# ============================================================
# EXTRACT IMAGES FROM DOCX
# ============================================================

def extract_images_from_docx(
    docx_path,
    temp_folder
):

    extracted_images = []

    os.makedirs(
        temp_folder,
        exist_ok=True
    )

    try:

        with zipfile.ZipFile(
            docx_path,
            "r"
        ) as z:

            for file_name in z.namelist():

                if not file_name.startswith(
                    "word/media/"
                ):
                    continue

                image_name = os.path.basename(
                    file_name
                )

                output_path = os.path.join(
                    temp_folder,
                    image_name
                )

                with open(
                    output_path,
                    "wb"
                ) as f:

                    f.write(
                        z.read(file_name)
                    )

                extracted_images.append(
                    {
                        "name": image_name,
                        "path": output_path,
                        "zip_name": file_name
                    }
                )

        return extracted_images

    except Exception as e:

        print(
            f"Image extraction failed: {e}"
        )

        return []


# ============================================================
# REPLACE IMAGES INSIDE DOCX
# ============================================================

def replace_images_in_docx(
    original_docx_path,
    output_docx_path,
    reconstructed_images
):

    try:

        reconstructed_map = {
            item["original_name"]:
            item["reconstructed_path"]
            for item in reconstructed_images
        }

        temp_docx = (
            output_docx_path
            + ".tmp"
        )

        with zipfile.ZipFile(
            original_docx_path,
            "r"
        ) as zin:

            with zipfile.ZipFile(
                temp_docx,
                "w",
                zipfile.ZIP_DEFLATED
            ) as zout:

                for item in zin.infolist():

                    data = zin.read(
                        item.filename
                    )

                    if item.filename.startswith(
                        "word/media/"
                    ):

                        image_name = os.path.basename(
                            item.filename
                        )

                        reconstructed_path = (
                            reconstructed_map.get(
                                image_name
                            )
                        )

                        if (
                            reconstructed_path
                            and os.path.exists(
                                reconstructed_path
                            )
                        ):

                            with open(
                                reconstructed_path,
                                "rb"
                            ) as image_file:

                                data = (
                                    image_file.read()
                                )

                    zout.writestr(
                        item,
                        data
                    )

        os.replace(
            temp_docx,
            output_docx_path
        )

        return True

    except Exception as e:

        print(
            f"Failed to replace images "
            f"in DOCX: {e}"
        )

        return False


# ============================================================
# IMAGE RECONSTRUCTION PIPELINE
# ============================================================

def reconstruct_images_pipeline(
    original_docx_path,
    elements,
    temp_folder
):

    print(
        "\n========== IMAGE RECONSTRUCTION =========="
    )

    image_elements = [
        element
        for element in elements
        if element.get("type") == "image_text"
    ]

    print(
        "Translated image elements:",
        len(image_elements)
    )

    if not image_elements:
        return []

    extracted_images = extract_images_from_docx(
        original_docx_path,
        temp_folder
    )

    if not extracted_images:
        return []

    reconstructed_images = []

    for index, image_element in enumerate(
        image_elements
    ):

        image_name = image_element.get(
            "image_name",
            ""
        )

        matching_image = next(
            (
                ext
                for ext in extracted_images
                if (
                    ext["name"] == image_name
                    or
                    ext["name"].replace(
                        "image",
                        "image_"
                    ) == image_name
                )
            ),
            None
        )

        if (
            matching_image is None
            and index < len(extracted_images)
        ):

            matching_image = (
                extracted_images[index]
            )

        if matching_image is None:
            continue

        original_image_path = (
            matching_image["path"]
        )

        reconstructed_image_path = os.path.join(
            temp_folder,
            f"reconstructed_"
            f"{index + 1}_"
            f"{matching_image['name']}"
        )

        success = reconstruct_image(
            original_image_path,
            image_element,
            reconstructed_image_path
        )

        if success:

            reconstructed_images.append(
                {
                    "original_name":
                        matching_image["name"],

                    "reconstructed_path":
                        reconstructed_image_path
                }
            )

    return reconstructed_images


# ============================================================
# MAIN DOCX RECONSTRUCTION
# ============================================================

def reconstruct_docx(
    original_docx_path,
    translated_json_path,
    output_docx_path
):

    print(
        "\n=========================================="
    )

    print(
        "STARTING DOCX RECONSTRUCTION"
    )

    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # Validate files
    # --------------------------------------------------------

    if not os.path.exists(
        original_docx_path
    ):

        raise FileNotFoundError(
            f"Original DOCX not found: "
            f"{original_docx_path}"
        )

    if not os.path.exists(
        translated_json_path
    ):

        raise FileNotFoundError(
            f"Translated JSON not found: "
            f"{translated_json_path}"
        )

    # --------------------------------------------------------
    # Load original DOCX
    # --------------------------------------------------------

    document = Document(
        original_docx_path
    )

    # --------------------------------------------------------
    # Load translated JSON
    # --------------------------------------------------------

    with open(
        translated_json_path,
        "r",
        encoding="utf-8"
    ) as file:

        translated_data = json.load(
            file
        )

    elements = translated_data.get(
        "elements",
        []
    )

    print(
        "Total JSON elements:",
        len(elements)
    )

    # --------------------------------------------------------
    # Temporary folder
    # --------------------------------------------------------

    base_dir = os.path.dirname(
        os.path.abspath(
            original_docx_path
        )
    )

    temp_folder = os.path.join(
        base_dir,
        "temp",
        os.path.splitext(
            os.path.basename(
                original_docx_path
            )
        )[0]
    )

    os.makedirs(
        temp_folder,
        exist_ok=True
    )

    # ========================================================
    # STEP 1 - PARAGRAPHS
    # ========================================================

    reconstruct_paragraphs(
        document,
        elements
    )

    # ========================================================
    # STEP 2 - TABLES
    # ========================================================

    reconstruct_tables(
        document,
        elements
    )

    # ========================================================
    # STEP 3 - IMAGES
    # ========================================================

    reconstructed_images = (
        reconstruct_images_pipeline(
            original_docx_path,
            elements,
            temp_folder
        )
    )

    # ========================================================
    # STEP 4 - SAVE DOCX
    # ========================================================

    output_dir = os.path.dirname(
        os.path.abspath(
            output_docx_path
        )
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    document.save(
        output_docx_path
    )

    # ========================================================
    # STEP 5 - REPLACE IMAGES
    # ========================================================

    if reconstructed_images:

        print(
            "\n========== REPLACING DOCX IMAGES =========="
        )

        success = replace_images_in_docx(
            output_docx_path,
            output_docx_path,
            reconstructed_images
        )

        if success:

            print(
                "Final DOCX updated with "
                "reconstructed images."
            )

    # ========================================================
    # DONE
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "DOCX RECONSTRUCTION COMPLETED"
    )

    print(
        "=========================================="
    )

    print(
        f"Output: {output_docx_path}"
    )

    return output_docx_path