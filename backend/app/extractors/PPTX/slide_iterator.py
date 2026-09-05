import json
import os
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from .shape_extractor import extract_text_from_shape
from .table_extractor import extract_table_data
from .image_extractor import extract_image

def extract_pptx_to_json(pptx_path, output_json_path, image_output_dir="extracted_images"):
    """Main iterator that traverses slides and routes extraction to appropriate modules."""
    prs = Presentation(pptx_path)
    presentation_data = {}

    if not os.path.exists(image_output_dir):
        os.makedirs(image_output_dir)

    for slide_index, slide in enumerate(prs.slides):
        slide_id = f"slide_{slide_index + 1}"
        presentation_data[slide_id] = []

        for shape_index, shape in enumerate(slide.shapes):
            
            # 1. Extract Text
            if shape.has_text_frame:
                text_data = extract_text_from_shape(shape, shape_index)
                if text_data:
                    presentation_data[slide_id].append(text_data)
            
            # 2. Extract Tables
            elif shape.has_table:
                table_data = extract_table_data(shape, shape_index)
                if table_data:
                    presentation_data[slide_id].append(table_data)
            
            # 3. Extract Images
            elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                image_data = extract_image(shape, shape_index, slide_index + 1, image_output_dir)
                if image_data:
                    presentation_data[slide_id].append(image_data)

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(presentation_data, f, ensure_ascii=False, indent=4)
    
    print(f"Extraction complete. JSON saved to {output_json_path}")
    return output_json_path