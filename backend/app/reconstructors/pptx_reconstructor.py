import json
import os
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.enum.text import MSO_AUTO_SIZE, MSO_ANCHOR
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

def _replace_text_preserve_format(target, translated_text):
    # Safely determine if 'target' is a Shape or already a TextFrame
    if hasattr(target, 'paragraphs'):
        text_frame = target
    elif hasattr(target, 'has_text_frame') and target.has_text_frame:
        text_frame = target.text_frame
    else:
        return
        
    translated_lines = str(translated_text).split('\n')
    original_paragraphs = text_frame.paragraphs
    
    # Fallback ke liye pehle paragraph ka font save kar rahe hain
    fallback_font_name, fallback_font_size, fallback_font_bold = None, None, None
    if original_paragraphs and original_paragraphs[0].runs:
        fallback_font_name = original_paragraphs[0].runs[0].font.name
        fallback_font_size = original_paragraphs[0].runs[0].font.size
        fallback_font_bold = original_paragraphs[0].runs[0].font.bold

    # 1. Line-by-line (Paragraph-by-paragraph) update karenge taaki bullet state preserve rahe
    for i, para in enumerate(original_paragraphs):
        if i < len(translated_lines):
            # Original font capture karo THIS paragraph ke liye
            orig_font_name, orig_font_size, orig_font_bold = fallback_font_name, fallback_font_size, fallback_font_bold
            for run in para.runs:
                if run.text.strip():
                    if run.font.size: orig_font_size = run.font.size
                    if run.font.name: orig_font_name = run.font.name
                    if run.font.bold is not None: orig_font_bold = run.font.bold
                    break

            # Text update karo (Bullet properties waise hi rahengi jaisi original mein thi)
            para.text = translated_lines[i]

            # Font wapas lagao
            for run in para.runs:
                if orig_font_size: run.font.size = orig_font_size
                if orig_font_name: run.font.name = orig_font_name
                if orig_font_bold is not None: run.font.bold = orig_font_bold
        else:
            # Agar text chhota hai aur original me zyada paragraphs the, unhe clear karo
            para.text = ""
            
    # 2. Agar API ne zyada lines di hain, toh unhe 'Soft Return' (\x0b) ke sath jodenge 
    # Taaki un par naya bullet na ban jaye
    if len(translated_lines) > len(original_paragraphs) and original_paragraphs:
        extra_lines = translated_lines[len(original_paragraphs):]
        last_para = original_paragraphs[-1]
        
        # \x0b (Shift+Enter) use karne se bina naye bullet ke line change hoti hai
        last_para.text = last_para.text + '\x0b' + '\x0b'.join(extra_lines)
        
        # Font fix for the new extra text
        for run in last_para.runs:
            if fallback_font_size: run.font.size = fallback_font_size
            if fallback_font_name: run.font.name = fallback_font_name
            if fallback_font_bold is not None: run.font.bold = fallback_font_bold

def _set_cell_text(cell, text):
    text_frame = cell.text_frame
    
    # Font size wapas capture kar rahe hain
    orig_font_size, orig_font_name, orig_font_bold = None, None, None
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            if run.font.size is not None and orig_font_size is None:
                orig_font_size = run.font.size
            if run.font.name is not None and orig_font_name is None:
                orig_font_name = run.font.name
            if run.font.bold is not None and orig_font_bold is None:
                orig_font_bold = run.font.bold

    text_frame.text = str(text)

    # Font size wapas apply kar rahe hain
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            if orig_font_size: run.font.size = orig_font_size
            if orig_font_name: run.font.name = orig_font_name
            if orig_font_bold is not None: run.font.bold = orig_font_bold


def _get_image_font(font_size):
    font_paths = (
        "C:/Windows/Fonts/Nirmala.ttf",
        "C:/Windows/Fonts/NirmalaUI.ttf",
        "C:/Windows/Fonts/Nirmala.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
    )
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except OSError:
                continue
    return ImageFont.load_default()

def _fit_image_text(draw, text, box, max_font_size):
    x1, y1, x2, y2 = box
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)
    for font_size in range(max_font_size, 5, -1):
        font = _get_image_font(font_size)
        measured = draw.textbbox((0, 0), text, font=font)
        if measured[2] - measured[0] <= box_width and measured[3] - measured[1] <= box_height:
            return font
    return _get_image_font(6)

def reconstruct_image(image_path, ocr_data, translated_text, output_path):
    try:
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        translated_lines = [line.strip() for line in translated_text.splitlines()]

        for index, item in enumerate(ocr_data):
            text = item.get("text", "")
            bbox = item.get("bbox", [])
            if not text or not bbox:
                continue

            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            
            box = (x1, y1, x2, y2)
            draw.rectangle(box, fill="white")

            new_text = item.get("translated_text", "").strip()
            if not new_text:
                new_text = translated_lines[index] if index < len(translated_lines) else ""
            if not new_text.strip():
                continue

            box_height = max(10, y2 - y1)
            font = _fit_image_text(draw, new_text, box, max(10, int(box_height * 0.8)))
            text_bbox = draw.textbbox((0, 0), new_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = x1 + max(0, (x2 - x1 - text_width) // 2)
            text_y = y1 + max(0, (y2 - y1 - text_height) // 2) - text_bbox[1]

            draw.text((text_x, text_y), new_text, fill="black", font=font)

        image.save(output_path)
        return output_path
    except Exception as e:
        print(f"Error reconstructing image: {e}")
        return image_path

def _replace_picture_image(shape, image_path):
    """Replace only the picture payload and preserve the original shape transform."""
    image_part, _ = shape.part.get_or_add_image_part(image_path)
    relationship_id = shape.part.relate_to(image_part, RT.IMAGE)
    shape._element.blipFill.blip.embed = relationship_id

def _resolve_image_path(image_path, translated_json_path):
    if os.path.exists(image_path):
        return image_path

    normalized_path = image_path.replace("\\", os.sep).replace("/", os.sep)
    image_name = os.path.basename(normalized_path)
    json_directory = os.path.dirname(os.path.abspath(translated_json_path))
    candidates = (
        os.path.join(json_directory, image_name),
        os.path.join(os.path.dirname(json_directory), normalized_path),
    )
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return image_path

def _table_cell_bounds(table_shape, row_index, column_index):
    left = table_shape.left + sum(
        table_shape.table.columns[index].width for index in range(column_index)
    )
    top = table_shape.top + sum(
        table_shape.table.rows[index].height for index in range(row_index)
    )
    width = table_shape.table.columns[column_index].width
    height = table_shape.table.rows[row_index].height
    return left, top, left + width, top + height

def _fit_nested_tables(slide, slide_width, slide_height):
    table_shapes = [shape for shape in slide.shapes if shape.has_table]
    if len(table_shapes) < 2:
        return

    slide_right = slide_width
    slide_bottom = slide_height
    margin = Pt(2)

    for inner_table in table_shapes:
        center_x = inner_table.left + inner_table.width // 2
        center_y = inner_table.top + inner_table.height // 2
        containing_cells = []

        for outer_table in table_shapes:
            if outer_table is inner_table:
                continue
            for row_index, _ in enumerate(outer_table.table.rows):
                for column_index, _ in enumerate(outer_table.table.columns):
                    bounds = _table_cell_bounds(outer_table, row_index, column_index)
                    if bounds[0] <= center_x <= bounds[2] and bounds[1] <= center_y <= bounds[3]:
                        containing_cells.append(bounds)

        if not containing_cells:
            continue

        cell_left, cell_top, cell_right, cell_bottom = min(
            containing_cells,
            key=lambda bounds: (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]),
        )
        left = max(cell_left + margin, 0)
        top = max(cell_top + margin, 0)
        right = min(cell_right - margin, slide_right)
        bottom = min(cell_bottom - margin, slide_bottom)
        if right > left and bottom > top:
            inner_table.left = left
            inner_table.top = top
            inner_table.width = right - left
            inner_table.height = bottom - top
            if len(inner_table.table.columns) == 2:
                first_column_width = round(inner_table.width * 0.55)
                inner_table.table.columns[0].width = first_column_width
                inner_table.table.columns[1].width = inner_table.width - first_column_width
                inner_table.width = right - left
            row_height = inner_table.height // len(inner_table.table.rows)
            for row_index, row in enumerate(inner_table.table.rows):
                if row_index == len(inner_table.table.rows) - 1:
                    row.height = inner_table.height - row_height * row_index
                else:
                    row.height = row_height

def reconstruct_pptx(original_pptx_path, translated_json_path, output_pptx_path):
    print(f"Loading original PPTX: {original_pptx_path}")
    prs = Presentation(original_pptx_path)
    
    print(f"Loading translated JSON: {translated_json_path}")
    with open(translated_json_path, 'r', encoding='utf-8') as f:
        translated_data = json.load(f)
        
    for slide_index, slide in enumerate(prs.slides):
        slide_id = f"slide_{slide_index + 1}"
        if slide_id not in translated_data:
            continue
            
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
                    # Using the new format preserver
                    _replace_text_preserve_format(shape.text_frame, translated_text)
                    shape.text_frame.word_wrap = True

            # --- Replace Table Content ---
            elif item['type'] == 'table' and shape.has_table:
                trans_table = item.get('translated_data', [])
                if trans_table:
                    for row_idx, row in enumerate(shape.table.rows):
                        for col_idx, cell in enumerate(row.cells):
                            if row_idx < len(trans_table) and col_idx < len(trans_table[row_idx]):
                                _set_cell_text(cell, trans_table[row_idx][col_idx])
                                
            # --- Replace Image With Translated Image ---
            elif item['type'] == 'image':
                image_path = item.get('image_path')
                ocr_data = item.get('ocr_data', [])
                translated_text = item.get('translated_text', '')

                if image_path and ocr_data and translated_text:
                    image_path = _resolve_image_path(image_path, translated_json_path)
                    translated_image_path = os.path.join(
                        os.path.dirname(image_path),
                        f"translated_{os.path.basename(image_path)}"
                    )

                    reconstruct_image(image_path, ocr_data, translated_text, translated_image_path)

                    try:
                        _replace_picture_image(shape, translated_image_path)
                    except Exception as e:
                        print(f"Error replacing PPT image: {e}")                                    

        _fit_nested_tables(slide, prs.slide_width, prs.slide_height)

    prs.save(output_pptx_path)
    print(f"Success: Reconstructed PPTX saved to {output_pptx_path}")
    return output_pptx_path