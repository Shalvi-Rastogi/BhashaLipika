from docx import Document
from docx.shared import RGBColor, Pt
import json
import os
import zipfile
import shutil
import tempfile

from docx.oxml.shared import OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# FONT
# ============================================================

def get_font_path():
    """
    Find a Unicode font available on Windows.
    Nirmala UI supports Hindi/Devanagari.
    """
    possible_fonts = [
        r"C:\Windows\Fonts\Nirmala.ttf",
        r"C:\Windows\Fonts\NirmalaUI.ttf",
        r"C:\Windows\Fonts\Nirmala.ttc",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return font_path

    return None


# ============================================================
# FONT SIZE CALCULATION
# ============================================================

def calculate_font_size(
    draw,
    text,
    box_width,
    box_height,
    font_path
):
    """
    Calculate a font size based on the original
    OCR bounding-box dimensions.
    """
    font_size = max(8, int(box_height * 0.75))

    if font_path is None:
        return None

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
    """
    Estimate the background color around the OCR text.
    """
    try:
        pixels = []
        sample_points = [
            (max(0, x1 - 2), max(0, y1)),
            (max(0, x1 - 2), min(image.height - 1, y2)),
            (min(image.width - 1, x2 + 2), max(0, y1)),
            (min(image.width - 1, x2 + 2), min(image.height - 1, y2)),
        ]

        for point in sample_points:
            pixels.append(image.getpixel(point))

        if pixels:
            r = sum(pixel[0] for pixel in pixels) // len(pixels)
            g = sum(pixel[1] for pixel in pixels) // len(pixels)
            b = sum(pixel[2] for pixel in pixels) // len(pixels)
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
            print("No OCR details found.")
            image.save(output_image_path)
            return True

        font_path = get_font_path()
        if font_path:
            print(f"Using font: {font_path}")
        else:
            print("Unicode font not found. Using default PIL font.")

        for item in ocr_details:
            original_text = item.get("text", "")
            translated_text = item.get("translated_text", "")

            if not translated_text:
                translated_text = item.get("text", "")

            bbox = item.get("bbox")

            if not bbox or not translated_text:
                continue

            x1 = min(int(point[0]) for point in bbox)
            y1 = min(int(point[1]) for point in bbox)
            x2 = max(int(point[0]) for point in bbox)
            y2 = max(int(point[1]) for point in bbox)

            box_width = max(1, x2 - x1)
            box_height = max(1, y2 - y1)

            background_color = get_background_color(image, x1, y1, x2, y2)
            draw.rectangle([x1, y1, x2, y2], fill=background_color)

            font = calculate_font_size(draw, translated_text, box_width, box_height, font_path)
            if font is None:
                font = ImageFont.load_default()

            text_bbox = draw.textbbox((0, 0), translated_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            text_x = x1 + (box_width - text_width) / 2
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
        reconstructed_map = {item["original_name"]: item["reconstructed_path"] for item in reconstructed_images}
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
# APPLY RUN STYLES
# ============================================================
# ============================================================
# APPLY RUN STYLES (100% CORRECT OOXML ORDER FOR MS WORD)
# ============================================================
# ============================================================
# APPLY RUN STYLES (UPDATED WITH HEAVY FONT DETECTION)
# ============================================================
def apply_style_to_run(run, style_dict):
    if not style_dict:
        return
    
    # --- NEW LOGIC: The "Arial Black" / Heavy Font Trap ---
    font_name = style_dict.get("font_name", "")
    is_bold = style_dict.get("bold")
    
    # Force bold to True if the font name contains "Black" or "Bold"
    if font_name and ("Black" in font_name or "Bold" in font_name):
        is_bold = True
        
    # 1. Standard Apply (English Styles + Font Color/Size)
    if is_bold:
        run.bold = True
    if style_dict.get("italic"):
        run.italic = True
    if style_dict.get("underline"):
        run.underline = True
        
    font_size = style_dict.get("font_size")
    if font_size:
        run.font.size = Pt(font_size)
        
    font_color = style_dict.get("font_color")
    if isinstance(font_color, dict) and font_color.get("type") == "rgb":
        hex_val = font_color.get("value")
        if hex_val:
            try:
                run.font.color.rgb = RGBColor.from_string(hex_val)
            except ValueError:
                pass

    # 2. Inject Complex Script (Hindi) Tags in STRICT OOXML Order
    rPr = run._element.get_or_add_rPr()
    
    if is_bold:
        bCs = OxmlElement('w:bCs')
        bCs.set(qn('w:val'), '1')
        b = rPr.find(qn('w:b'))
        if b is not None:
            b.addnext(bCs)
        else:
            rPr.insert(0, bCs)
            
    if style_dict.get("italic"):
        iCs = OxmlElement('w:iCs')
        iCs.set(qn('w:val'), '1')
        i = rPr.find(qn('w:i'))
        if i is not None:
            i.addnext(iCs)
        else:
            rPr.insert(0, iCs)
            
    if font_size:
        szCs = OxmlElement('w:szCs')
        szCs.set(qn('w:val'), str(int(font_size * 2)))
        sz = rPr.find(qn('w:sz'))
        if sz is not None:
            sz.addnext(szCs)
        else:
            rPr.append(szCs)


# ============================================================
# PARAGRAPH RECONSTRUCTION (UPDATED)
# ============================================================

def reconstruct_paragraphs(document, elements):
    print("\n========== PARAGRAPH RECONSTRUCTION ==========")

    text_elements = [
        element for element in elements
        if element.get("type") in ["paragraph", "heading", "list_item"]
    ]

    paragraphs = document.paragraphs
    print("Original paragraphs:", len(paragraphs))
    print("Translated text elements:", len(text_elements))

    original_paragraphs = [
        paragraph for paragraph in paragraphs
        if paragraph.text.strip()
    ]

    for paragraph, element in zip(original_paragraphs, text_elements):
        
        # Clear existing paragraph formatting cleanly
        paragraph.clear()

        runs_data = element.get("runs", [])
        
        # Agar JSON mein runs majood hain, toh ek-ek karke unhe jodein
        if runs_data:
            for run_data in runs_data:
                run_text = run_data.get("text", "")
                if not run_text:
                    continue
                
                style = run_data.get("style", {})
                
                # Handle newlines inside the specific run
                lines = run_text.split('\n')
                for index, line in enumerate(lines):
                    new_run = paragraph.add_run(line)
                    apply_style_to_run(new_run, style) # Apply exact style for this run
                    
                    if index < len(lines) - 1:
                        new_run.add_break()
        else:
            # Fallback: Agar runs nahi hain toh pura text ek sath daal dein
            translated_text = element.get("text", "")
            if translated_text:
                lines = translated_text.split('\n')
                for index, line in enumerate(lines):
                    paragraph.add_run(line)
                    if index < len(lines) - 1:
                        paragraph.runs[-1].add_break()
# ============================================================
# TABLE RECONSTRUCTION (UPDATED TO SUPPORT STYLES/BREAKS)
# ============================================================

def reconstruct_tables(document, elements):
    print("\n========== TABLE RECONSTRUCTION ==========")

    table_elements = [
        element for element in elements
        if element.get("type") == "table"
    ]

    print("Original tables:", len(document.tables))
    print("Translated tables:", len(table_elements))

    for table_index, table in enumerate(document.tables):
        translated_table = None

        for element in table_elements:
            if element.get("table_index") == table_index:
                translated_table = element
                break

        if translated_table is None:
            continue

        translated_cells = [
            cell for row in translated_table.get("rows", [])
            for cell in row.get("cells", [])
        ]

        for row_index, row in enumerate(table.rows):
            for column_index, cell in enumerate(row.cells):
                
                translated_cell_data = None
                
                for translated_cell in translated_cells:
                    if (translated_cell.get("row") == row_index and
                        translated_cell.get("column") == column_index):
                        translated_cell_data = translated_cell
                        break

                if not translated_cell_data:
                    continue

                if cell.paragraphs:
                    target_paragraph_index = next(
                        (index for index, paragraph in enumerate(cell.paragraphs) if paragraph.text.strip()), 0
                    )

                    paragraph = cell.paragraphs[target_paragraph_index]
                    paragraph.clear()
                    
                    # Extract runs specifically for the cell
                    cell_paragraphs_data = translated_cell_data.get("paragraphs", [])
                    cell_runs_data = []
                    if cell_paragraphs_data and len(cell_paragraphs_data) > 0:
                        cell_runs_data = cell_paragraphs_data[0].get("runs", [])

                    if cell_runs_data:
                        for run_data in cell_runs_data:
                            run_text = run_data.get("text", "")
                            if not run_text:
                                continue
                            
                            style = run_data.get("style", {})
                            lines = run_text.split('\n')
                            
                            for i, line in enumerate(lines):
                                new_run = paragraph.add_run(line)
                                apply_style_to_run(new_run, style)
                                if i < len(lines) - 1:
                                    new_run.add_break()
                    else:
                        # Fallback for tables without runs
                        translated_text = translated_cell_data.get("text", "")
                        lines = translated_text.split('\n')
                        for i, line in enumerate(lines):
                            run = paragraph.add_run(line)
                            if i < len(lines) - 1:
                                run.add_break()

                    # Clear other paragraphs in the cell
                    for index, other_paragraph in enumerate(cell.paragraphs):
                        if index == target_paragraph_index:
                            continue
                        other_paragraph.clear()

# ============================================================
# RECONSTRUCT IMAGES PIPELINE
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
        matching_image = next((ext for ext in extracted_images if ext["name"] == image_name or ext["name"].replace("image", "image_") == image_name), None)

        if matching_image is None and index < len(extracted_images):
            matching_image = extracted_images[index]

        if matching_image is None:
            continue

        original_image_path = matching_image["path"]
        reconstructed_image_path = os.path.join(temp_folder, f"reconstructed_{index + 1}_{matching_image['name']}")

        success = reconstruct_image(original_image_path, image_element, reconstructed_image_path)
        if success:
            reconstructed_images.append({
                "original_name": matching_image["name"],
                "reconstructed_path": reconstructed_image_path
            })

    return reconstructed_images


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

    base_dir = os.path.dirname(os.path.abspath(original_docx_path))
    temp_folder = os.path.join(base_dir, "temp", os.path.splitext(os.path.basename(original_docx_path))[0])
    os.makedirs(temp_folder, exist_ok=True)

    reconstruct_paragraphs(document, elements)
    reconstruct_tables(document, elements)
    reconstructed_images = reconstruct_images_pipeline(original_docx_path, elements, temp_folder)

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

    return output_docx_path