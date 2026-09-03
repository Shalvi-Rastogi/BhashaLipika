from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import json
import os
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
# APPLY RUN STYLE (FIXED FOR PROPER HINDI BOLDING)
# ============================================================

def apply_style_to_run(run, style_dict):
    """
    Apply extracted run formatting to a reconstructed run.
    """
    if not style_dict:
        return

    font_name = style_dict.get("font_name")
    
    # Check dono ko karein: normal bold aur complex script bold
    is_bold = style_dict.get("bold") is True or style_dict.get("cs_bold") is True
    is_italic = style_dict.get("italic") is True or style_dict.get("cs_italic") is True
    is_underline = style_dict.get("underline") is True

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
    if is_bold:
        run.bold = True
    if is_italic:
        run.italic = True
    if is_underline:
        run.underline = True

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
    # Complex script formatting (STRICT OOXML ORDERING)
    # --------------------------------------------------------
    rPr = run._element.get_or_add_rPr()

    if is_bold:
        bCs = rPr.find(qn("w:bCs"))
        if bCs is None:
            bCs = OxmlElement("w:bCs")
            # Tag injection strictly AFTER English bold tag
            b = rPr.find(qn("w:b"))
            if b is not None:
                b.addnext(bCs)
            else:
                rPr.insert(0, bCs)

    if is_italic:
        iCs = rPr.find(qn("w:iCs"))
        if iCs is None:
            iCs = OxmlElement("w:iCs")
            i = rPr.find(qn("w:i"))
            if i is not None:
                i.addnext(iCs)
            else:
                rPr.insert(0, iCs)

    if font_size:
        szCs = rPr.find(qn("w:szCs"))
        if szCs is None:
            szCs = OxmlElement("w:szCs")
            sz = rPr.find(qn("w:sz"))
            if sz is not None:
                sz.addnext(szCs)
            else:
                rPr.append(szCs)
        try:
            szCs.set(qn("w:val"), str(int(float(font_size) * 2)))
        except Exception:
            pass

    # --------------------------------------------------------
    # Devanagari font
    # --------------------------------------------------------
    apply_devanagari_font(run, run.text)


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

    paragraph_style = paragraph_data.get("paragraph_style", {})
    apply_paragraph_style(paragraph, paragraph_style)

    runs_data = paragraph_data.get("runs", [])

    if runs_data:
        for run_data in runs_data:
            text = run_data.get("text", "")
            if not text:
                continue

            style = run_data.get("style", {})

            # Handle newline inside a run
            lines = text.split("\n")
            for index, line in enumerate(lines):
                if line:
                    new_run = paragraph.add_run(line)
                    apply_style_to_run(new_run, style)

                if index < len(lines) - 1:
                    if paragraph.runs:
                        paragraph.runs[-1].add_break()
    else:
        text = paragraph_data.get("text", "")
        if text:
            run = paragraph.add_run(text)
            apply_style_to_run(run, {})


# ============================================================
# RECONSTRUCT NORMAL PARAGRAPHS
# ============================================================

def reconstruct_paragraphs(document, elements):
    print("\n========== PARAGRAPH RECONSTRUCTION ==========")

    text_elements = [
        element for element in elements
        if element.get("type") in ["paragraph", "heading", "list_item"]
    ]

    original_paragraphs = [
        paragraph for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    print("Original paragraphs:", len(original_paragraphs))
    print("Translated text elements:", len(text_elements))

    for index, (paragraph, element) in enumerate(zip(original_paragraphs, text_elements)):

        # =========================================================
        # 1. FOOTNOTE BACKUP LOGIC (Clear karne se pehle save karo)
        # =========================================================
        special_tags = []
        for run in paragraph.runs:
            for child in run._element:
                if child.tag.endswith('footnoteReference') or child.tag.endswith('endnoteReference'):
                    special_tags.append(child)

        element_text = element.get("text", "").strip()

        if (
            element_text.lower() in {"secretary-general", "महासचिव"}
            and index > 0
            and text_elements[index - 1].get("text", "").strip().endswith(",")
        ):
            continue

        runs_data = element.get("runs", [])
        paragraph_style = element.get("paragraph_style", {})

        # Purana text aur normal runs yahan delete honge
        paragraph.clear()
        
        # NOTE: Agar aapke pas apply_paragraph_style function defined nahi hai toh aap 
        # is line ko hata sakti hain, ya phir aapne use upar define kiya hoga.
        if 'apply_paragraph_style' in globals():
            apply_paragraph_style(paragraph, paragraph_style)

        current_text = element.get("text", "").strip()

        if (
            current_text.lower() in {"secretary-general", "महासचिव"}
            and index > 0
            and text_elements[index - 1].get("text", "").strip().endswith(",")
        ):
            # Fallback agar WD_ALIGN_PARAGRAPH import na ho toh 2 ka matlab RIGHT hota hai
            paragraph.alignment = 2

        if index + 1 < len(text_elements):
            next_text = text_elements[index + 1].get("text", "").strip().lower()

            if (
                current_text.endswith(",")
                and next_text in {"secretary-general", "महासचिव"}
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

                    previous_element.getparent().remove(previous_element)
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
                paragraph.alignment = 2 # RIGHT

                paragraph_properties = paragraph._p.pPr
                if paragraph_properties is not None:
                    numbering_properties = paragraph_properties.numPr
                    if numbering_properties is not None:
                        paragraph_properties.remove(numbering_properties)

                paragraph.paragraph_format.left_indent = None
                paragraph.paragraph_format.right_indent = None
                paragraph.paragraph_format.first_line_indent = None
                paragraph.paragraph_format.left_indent = None

                next_paragraph = original_paragraphs[index + 1]
                next_paragraph.alignment = 2 # RIGHT
                next_paragraph.paragraph_format.left_indent = None
                next_paragraph.paragraph_format.right_indent = None
                next_paragraph.paragraph_format.first_line_indent = None
                
                paragraph_element = paragraph._p
                paragraph_element.addnext(next_paragraph._p)
                paragraph_element.getnext().getparent().remove(paragraph_element.getnext())

        if runs_data:
            for run_data in runs_data:
                text = run_data.get("text", "")
                text = text.replace(". . f..", "w.e.f.")
                if not text:
                    continue

                style = run_data.get("style", {})
                lines = text.split("\n")

                for index, line in enumerate(lines):
                    if line:
                        new_run = paragraph.add_run(line)
                        apply_style_to_run(new_run, style)

                    if index < len(lines) - 1:
                        if paragraph.runs:
                            paragraph.runs[-1].add_break()
        else:
            text = element.get("text", "")
            if text:
                new_run = paragraph.add_run(text)
                apply_style_to_run(new_run, {})

        # =========================================================
        # 2. FOOTNOTE RESTORE LOGIC (Naya text aane ke baad wapas lagao)
        # =========================================================
        if special_tags:
            if not paragraph.runs:
                # Agar text khali ho gaya toh ek dummy run daal do tags ke liye
                paragraph.add_run()
            last_run = paragraph.runs[-1]
            for tag in special_tags:
                last_run._element.append(tag)


# ============================================================
# GET PARAGRAPH DATA
# ============================================================

def get_paragraph_data_list(cell_data):
    """
    Safely get paragraph data from JSON.
    """
    paragraphs = cell_data.get("paragraphs", [])
    if not isinstance(paragraphs, list):
        return []
    return paragraphs


# ============================================================
# RECONSTRUCT CELL PARAGRAPHS
# ============================================================

def reconstruct_cell_paragraphs(cell, cell_data):
    """
    Reconstruct text inside a table cell.
    IMPORTANT: This function does NOT delete nested tables.
    """
    nested_tables_data = cell_data.get("nested_tables", [])
    paragraph_data_list = get_paragraph_data_list(cell_data)

    if nested_tables_data:
        for paragraph in cell.paragraphs:
            if paragraph.text.strip():
                paragraph.clear()
        return

    if not paragraph_data_list:
        text = cell_data.get("text", "")
        if text:
            paragraph = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
            paragraph.clear()
            run = paragraph.add_run(text)
            apply_style_to_run(run, {})
        return

    existing_paragraphs = cell.paragraphs

    for index, paragraph_data in enumerate(paragraph_data_list):
        if index < len(existing_paragraphs):
            paragraph = existing_paragraphs[index]
        else:
            paragraph = cell.add_paragraph()

        populate_paragraph(paragraph, paragraph_data)

    for index in range(len(paragraph_data_list), len(existing_paragraphs)):
        existing_paragraphs[index].clear()


# ============================================================
# RECONSTRUCT NESTED TABLE
# ============================================================

def reconstruct_existing_nested_table(existing_table, table_data, level=1):
    print(f"      Nested table level {level}: {len(existing_table.rows)} rows x {len(existing_table.columns)} columns")
    rows_data = table_data.get("rows", [])

    for row_data in rows_data:
        row_index = row_data.get("row_index")
        if row_index is None or row_index >= len(existing_table.rows):
            continue

        existing_row = existing_table.rows[row_index]
        cells_data = row_data.get("cells", [])

        for cell_data in cells_data:
            column_index = cell_data.get("column")
            if column_index is None:
                column_index = cell_data.get("cell_index")
            if column_index is None or column_index >= len(existing_row.cells):
                continue

            existing_cell = existing_row.cells[column_index]
            reconstruct_cell_paragraphs(existing_cell, cell_data)

            nested_tables_data = cell_data.get("nested_tables", [])
            if nested_tables_data:
                existing_nested_tables = existing_cell.tables
                for nested_index, nested_data in enumerate(nested_tables_data):
                    if nested_index < len(existing_nested_tables):
                        reconstruct_existing_nested_table(
                            existing_nested_tables[nested_index],
                            nested_data,
                            level + 1
                        )


# ============================================================
# RECONSTRUCT TOP-LEVEL TABLE
# ============================================================

def reconstruct_existing_table(existing_table, table_data):
    """
    Reconstruct a top-level table by modifying the original table in-place.
    """
    rows_data = table_data.get("rows", [])

    for row_data in rows_data:
        row_index = row_data.get("row_index")
        if row_index is None or row_index >= len(existing_table.rows):
            continue

        existing_row = existing_table.rows[row_index]
        cells_data = row_data.get("cells", [])

        for cell_data in cells_data:
            column_index = cell_data.get("column")
            if column_index is None:
                column_index = cell_data.get("cell_index")
            if column_index is None or column_index >= len(existing_row.cells):
                continue

            existing_cell = existing_row.cells[column_index]
            reconstruct_cell_paragraphs(existing_cell, cell_data)

            nested_tables_data = cell_data.get("nested_tables", [])
            if nested_tables_data:
                original_nested_tables = existing_cell.tables
                for nested_index, nested_data in enumerate(nested_tables_data):
                    if nested_index < len(original_nested_tables):
                        reconstruct_existing_nested_table(
                            original_nested_tables[nested_index],
                            nested_data,
                            level=1
                        )


# ============================================================
# TABLE RECONSTRUCTION
# ============================================================

def reconstruct_tables(document, elements):
    print("\n========== TABLE RECONSTRUCTION ==========")
    table_elements = [e for e in elements if e.get("type") == "table"]
    original_tables = document.tables

    print("Original top-level tables:", len(original_tables))
    print("Translated top-level tables:", len(table_elements))

    for table_index, table in enumerate(original_tables):
        translated_table = None

        for element in table_elements:
            if element.get("table_index") == table_index:
                translated_table = element
                break

        if translated_table is None:
            if table_index < len(table_elements):
                translated_table = table_elements[table_index]

        if translated_table is None:
            print(f"Skipping original table {table_index}")
            continue

        print(f"\nReconstructing top-level table {table_index}")
        reconstruct_existing_table(table, translated_table)


# ============================================================
# IMAGE FONT
# ============================================================

def get_image_font_path():
    return get_font_path()


# ============================================================
# IMAGE FONT SIZE
# ============================================================

def calculate_font_size(draw, text, box_width, box_height, font_path):
    if not font_path or not text:
        return ImageFont.load_default()

    font_size = max(8, int(box_height * 0.80))

    while font_size >= 8:
        try:
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            if text_width <= box_width and text_height <= box_height:
                return font
            font_size -= 1
        except Exception:
            break
            
    try:
        return ImageFont.truetype(font_path, 8)
    except Exception:
        return ImageFont.load_default()


# ============================================================
# BACKGROUND COLOR
# ============================================================

def get_background_color(image, x1, y1, x2, y2):
    try:
        pixels = []
        sample_points = [
            (max(0, x1 - 2), max(0, y1)),
            (max(0, x1 - 2), min(image.height - 1, y2)),
            (min(image.width - 1, x2 + 2), max(0, y1)),
            (min(image.width - 1, x2 + 2), min(image.height - 1, y2))
        ]

        for point in sample_points:
            pixel = image.getpixel(point)
            if isinstance(pixel, tuple) and len(pixel) >= 3:
                pixels.append(pixel[:3])

        if pixels:
            r = sum(p[0] for p in pixels) // len(pixels)
            g = sum(p[1] for p in pixels) // len(pixels)
            b = sum(p[2] for p in pixels) // len(pixels)
            return (r, g, b)
    except Exception:
        pass
    return "white"


# ============================================================
# IMAGE RECONSTRUCTION
# ============================================================

def reconstruct_image(original_image_path, image_element, output_image_path):
    try:
        image = Image.open(original_image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        ocr_details = image_element.get("ocr_details", [])

        if not ocr_details:
            image.save(output_image_path)
            return True

        font_path = get_image_font_path()
        if font_path:
            print(f"Using image font: {font_path}")
        else:
            print("Devanagari image font not found.")

        for item in ocr_details:
            translated_text = item.get("translated_text", "")
            if not translated_text:
                translated_text = item.get("text", "")

            bbox = item.get("bbox")
            if not bbox or not translated_text:
                continue

            x1 = max(0, min(int(p[0]) for p in bbox))
            y1 = max(0, min(int(p[1]) for p in bbox))
            x2 = max(x1 + 1, max(int(p[0]) for p in bbox))
            y2 = max(y1 + 1, max(int(p[1]) for p in bbox))
            
            x1 = min(image.width - 1, x1)
            y1 = min(image.height - 1, y1)
            x2 = min(image.width - 1, x2)
            y2 = min(image.height - 1, y2)

            box_width = max(1, x2 - x1)
            box_height = max(1, y2 - y1)

            background_color = get_background_color(image, x1, y1, x2, y2)
            draw.rectangle([x1, y1, x2, y2], fill=background_color)

            font = calculate_font_size(draw, translated_text, box_width, box_height, font_path)
            text_bbox = draw.textbbox((0, 0), translated_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            text_x = x1 + (box_width - text_width) / 2 - text_bbox[0]
            text_y = y1 + (box_height - text_height) / 2 - text_bbox[1]

            draw.text((text_x, text_y), translated_text, fill="black", font=font)

        image.save(output_image_path)
        print(f"Reconstructed image saved: {output_image_path}")
        return True
    except Exception as e:
        print(f"Image reconstruction failed: {e}")
        return False


# ============================================================
# EXTRACT IMAGES FROM DOCX
# ============================================================

def extract_images_from_docx(docx_path, temp_folder):
    extracted_images = []
    os.makedirs(temp_folder, exist_ok=True)
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            for file_name in z.namelist():
                if not file_name.startswith("word/media/"):
                    continue

                image_name = os.path.basename(file_name)
                output_path = os.path.join(temp_folder, image_name)

                with open(output_path, "wb") as f:
                    f.write(z.read(file_name))

                extracted_images.append({
                    "name": image_name,
                    "path": output_path,
                    "zip_name": file_name
                })
        return extracted_images
    except Exception as e:
        print(f"Image extraction failed: {e}")
        return []


# ============================================================
# REPLACE IMAGES INSIDE DOCX
# ============================================================

def replace_images_in_docx(original_docx_path, output_docx_path, reconstructed_images):
    try:
        reconstructed_map = {
            item["original_name"]: item["reconstructed_path"]
            for item in reconstructed_images
        }
        temp_docx = output_docx_path + ".tmp"

        with zipfile.ZipFile(original_docx_path, "r") as zin:
            with zipfile.ZipFile(temp_docx, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename.startswith("word/media/"):
                        image_name = os.path.basename(item.filename)
                        reconstructed_path = reconstructed_map.get(image_name)

                        if reconstructed_path and os.path.exists(reconstructed_path):
                            with open(reconstructed_path, "rb") as image_file:
                                data = image_file.read()

                    zout.writestr(item, data)

        os.replace(temp_docx, output_docx_path)
        return True
    except Exception as e:
        print(f"Failed to replace images in DOCX: {e}")
        return False


# ============================================================
# IMAGE RECONSTRUCTION PIPELINE
# ============================================================

def reconstruct_images_pipeline(original_docx_path, elements, temp_folder):
    print("\n========== IMAGE RECONSTRUCTION ==========")
    image_elements = [
        element for element in elements
        if element.get("type") == "image_text"
    ]
    print("Translated image elements:", len(image_elements))

    if not image_elements:
        return []

    extracted_images = extract_images_from_docx(original_docx_path, temp_folder)
    if not extracted_images:
        return []

    reconstructed_images = []
    for index, image_element in enumerate(image_elements):
        image_name = image_element.get("image_name", "")
        matching_image = next(
            (ext for ext in extracted_images
             if ext["name"] == image_name or ext["name"].replace("image", "image_") == image_name),
            None
        )

        if matching_image is None and index < len(extracted_images):
            matching_image = extracted_images[index]

        if matching_image is None:
            continue

        original_image_path = matching_image["path"]
        reconstructed_image_path = os.path.join(
            temp_folder,
            f"reconstructed_{index + 1}_{matching_image['name']}"
        )

        success = reconstruct_image(original_image_path, image_element, reconstructed_image_path)
        if success:
            reconstructed_images.append({
                "original_name": matching_image["name"],
                "reconstructed_path": reconstructed_image_path
            })
    return reconstructed_images

def translate_footnotes_xml(document):
    """
    Directly manipulate footnotes.xml to translate standard footers 
    because python-docx does not extract them natively.
    """
    translations = {
        "This Synopsis is not an authoritative record of the proceedings of the Rajya Sabha.": "यह सारांश राज्यसभा की कार्यवाही का आधिकारिक प्रामाणिक रिकॉर्ड नहीं है।"
    }
    
    for rel in document.part.rels.values():
        if "footnotes" in rel.reltype:
            # FIX: Use ._element instead of .element
            footnote_part = rel.target_part
            if not hasattr(footnote_part, '_element'):
                continue
                
            for p in footnote_part._element.xpath('.//w:p'):
                # Extract all text nodes in the footnote paragraph
                text_nodes = [t for t in p.xpath('.//w:t') if t.text]
                if not text_nodes:
                    continue
                
                # Combine text (to handle split runs)
                full_text = "".join(t.text for t in text_nodes)
                
                # Replace with Hindi translation if matched
                for eng, hin in translations.items():
                    if eng in full_text:
                        for t in text_nodes:
                            t.text = ""  # Clear old English fragments
                        # Put the full Hindi translated text in the first node
                        text_nodes[0].text = full_text.replace(eng, hin)


# ============================================================
# MAIN DOCX RECONSTRUCTION
# ============================================================

def reconstruct_docx(original_docx_path, translated_json_path, output_docx_path):
    print("\n==========================================")
    print("STARTING DOCX RECONSTRUCTION")
    print("==========================================")

    if not os.path.exists(original_docx_path):
        raise FileNotFoundError(f"Original DOCX not found: {original_docx_path}")

    if not os.path.exists(translated_json_path):
        raise FileNotFoundError(f"Translated JSON not found: {translated_json_path}")

    document = Document(original_docx_path)

    with open(translated_json_path, "r", encoding="utf-8") as file:
        translated_data = json.load(file)

    elements = translated_data.get("elements", [])
    print("Total JSON elements:", len(elements))

    base_dir = os.path.dirname(os.path.abspath(original_docx_path))
    temp_folder = os.path.join(
        base_dir,
        "temp",
        os.path.splitext(os.path.basename(original_docx_path))[0]
    )
    os.makedirs(temp_folder, exist_ok=True)

    reconstruct_paragraphs(document, elements)
    reconstruct_tables(document, elements)
    reconstructed_images = reconstruct_images_pipeline(original_docx_path, elements, temp_folder)

    translate_footnotes_xml(document)
    output_dir = os.path.dirname(os.path.abspath(output_docx_path))
    os.makedirs(output_dir, exist_ok=True)
    document.save(output_docx_path)

    if reconstructed_images:
        print("\n========== REPLACING DOCX IMAGES ==========")
        success = replace_images_in_docx(output_docx_path, output_docx_path, reconstructed_images)
        if success:
            print("Final DOCX updated with reconstructed images.")

    print("\n==========================================")
    print("DOCX RECONSTRUCTION COMPLETED")
    print("==========================================")
    print(f"Output: {output_docx_path}")

    return output_docx_path