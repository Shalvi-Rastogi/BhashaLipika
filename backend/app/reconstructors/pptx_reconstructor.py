import json
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
                                    
    # 4. Save the final reconstructed file
    prs.save(output_pptx_path)
    print(f"Success: Reconstructed PPTX saved to {output_pptx_path}")
    
    return output_pptx_path