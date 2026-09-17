import json
import os
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Pt


def _shape_at_path(shapes, shape_path):
    """Resolve a top-level or grouped shape path from extracted JSON."""
    current_shapes = shapes
    shape = None

    try:
        for path_position, index in enumerate(shape_path):
            shape = current_shapes[int(index)]
            if path_position < len(shape_path) - 1:
                current_shapes = shape.shapes
    except (AttributeError, IndexError, TypeError, ValueError):
        return None

    return shape


def _shape_path(shape_index):
    if isinstance(shape_index, int):
        return (shape_index,)
    return tuple(str(part) for part in str(shape_index).split("."))


def _set_cell_text(cell, text):
    """Replace cell text while keeping translated text inside its cell."""
    text_frame = cell.text_frame
    text_frame.word_wrap = True
    text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    text_frame.margin_left = Pt(2)
    text_frame.margin_right = Pt(2)
    text_frame.margin_top = Pt(1)
    text_frame.margin_bottom = Pt(1)
    text_frame.text = text

    # Table rows have fixed heights, so explicitly reduce long translations.
    longest_line = max((len(line) for line in text.splitlines()), default=0)
    font_size = 7 if longest_line > 14 or len(text) > 20 else 8 if longest_line > 9 or len(text) > 12 else 9
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(font_size)

def reconstruct_image(image_path, ocr_data, translated_text, output_path):
    """
    Create a translated version of an image using OCR bounding boxes.
    Original detected text is covered and translated text is drawn in its place.
    """

    try:
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)

        translated_lines = translated_text.splitlines()

        for index, item in enumerate(ocr_data):
            text = item.get("text", "")
            bbox = item.get("bbox", [])

            if not text or not bbox:
                continue

            # Bounding box coordinates
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]

            x1 = min(xs)
            y1 = min(ys)
            x2 = max(xs)
            y2 = max(ys)

            # Cover original text
            draw.rectangle(
                [x1, y1, x2, y2],
                fill="white"
            )

            # Use corresponding translated line
            if index < len(translated_lines):
                new_text = translated_lines[index]
            else:
                new_text = ""

            if not new_text.strip():
                continue

            # Calculate approximate font size from OCR box height
            box_height = max(10, y2 - y1)
            font_size = max(10, int(box_height * 0.8))

            try:
                font = ImageFont.truetype(
                    "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
                    font_size
                )
            except Exception:
                font = ImageFont.load_default()

            # Draw translated text
            draw.text(
                (x1, y1),
                new_text,
                fill="black",
                font=font
            )

        image.save(output_path)

        print(f"Translated image saved: {output_path}")

        return output_path

    except Exception as e:
        print(f"Error reconstructing image: {e}")
        return image_path

def reconstruct_pptx(original_pptx_path, translated_json_path, output_pptx_path):
    """
    Reads the original PPTX and the translated JSON, 
    replaces the text/tables with translated content, 
    and saves the final reconstructed PPTX.
    """
    print(f"Loading original PPTX: {original_pptx_path}")
    # 1. Load original presentation to preserve layout, design, and images
    prs = Presentation(original_pptx_path)
    
    # 2. Load the translated JSON data
    print(f"Loading translated JSON: {translated_json_path}")
    with open(translated_json_path, 'r', encoding='utf-8') as f:
        translated_data = json.load(f)
        
    # 3. Iterate through slides and replace content
    for slide_index, slide in enumerate(prs.slides):
        slide_id = f"slide_{slide_index + 1}"
        
        # Agar is slide ka data JSON mein nahi hai, toh skip karein
        if slide_id not in translated_data:
            continue
            
        # Shape index ke hisaab se lookup dictionary banayein taaki matching fast ho
        shape_dict = {
            str(item['shape_index']): item
            for item in translated_data[slide_id]
        }
        
        for shape_index, item in shape_dict.items():
            shape = _shape_at_path(slide.shapes, _shape_path(shape_index))
            if shape is None:
                continue

            # --- Replace Text Frame Content ---
            if item['type'] == 'text_frame' and shape.has_text_frame:
                translated_text = item.get('translated_text', '')

                if translated_text:
                    shape.text_frame.text = translated_text
                    shape.text_frame.word_wrap = True
                    shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

            # --- Replace Table Content ---
            elif item['type'] == 'table' and shape.has_table:
                trans_table = item.get('translated_data', [])

                if trans_table:
                    for row_idx, row in enumerate(shape.table.rows):
                        for col_idx, cell in enumerate(row.cells):
                            # Bounds check to avoid index errors if structure changed
                            if row_idx < len(trans_table) and col_idx < len(trans_table[row_idx]):
                                _set_cell_text(cell, trans_table[row_idx][col_idx])
                        # --- Replace Image With Translated Image ---
            elif item['type'] == 'image':
                image_path = item.get('image_path')
                ocr_data = item.get('ocr_data', [])
                translated_text = item.get('translated_text', '')

                if image_path and ocr_data and translated_text:
                    translated_image_path = os.path.join(
                        os.path.dirname(image_path),
                        f"translated_{os.path.basename(image_path)}"
                    )

                    reconstruct_image(
                        image_path,
                        ocr_data,
                        translated_text,
                        translated_image_path
                    )

                    try:
                        # Preserve original image position and size
                        left = shape.left
                        top = shape.top
                        width = shape.width
                        height = shape.height

                        # Remove original image
                        sp = shape._element
                        sp.getparent().remove(sp)

                        # Add translated image in exactly the same position
                        slide.shapes.add_picture(
                            translated_image_path,
                            left,
                            top,
                            width,
                            height
                        )

                    except Exception as e:
                        print(f"Error replacing PPT image: {e}")                                    
    # 4. Save the final reconstructed file
    prs.save(output_pptx_path)
    print(f"Success: Reconstructed PPTX saved to {output_pptx_path}")
    
    return output_pptx_path