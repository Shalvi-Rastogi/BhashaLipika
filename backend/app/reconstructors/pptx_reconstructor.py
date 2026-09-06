import json
from pptx import Presentation

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
        shape_dict = {item['shape_index']: item for item in translated_data[slide_id]}
        
        for shape_index, shape in enumerate(slide.shapes):
            if shape_index in shape_dict:
                data = shape_dict[shape_index]
                
                # --- Replace Text Frame Content ---
                if data['type'] == 'text_frame' and shape.has_text_frame:
                    translated_text = data.get('translated_text', '')
                    
                    if translated_text:
                        # Directly text replace karna
                        shape.text_frame.text = translated_text
                        
                # --- Replace Table Content ---
                elif data['type'] == 'table' and shape.has_table:
                    trans_table = data.get('translated_data', [])
                    
                    if trans_table:
                        for row_idx, row in enumerate(shape.table.rows):
                            for col_idx, cell in enumerate(row.cells):
                                # Bounds check to avoid index errors if structure changed
                                if row_idx < len(trans_table) and col_idx < len(trans_table[row_idx]):
                                    cell.text_frame.text = trans_table[row_idx][col_idx]
                                    
    # 4. Save the final reconstructed file
    prs.save(output_pptx_path)
    print(f"Success: Reconstructed PPTX saved to {output_pptx_path}")
    
    return output_pptx_path