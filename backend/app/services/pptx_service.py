import os
import json
import re
from concurrent.futures import ThreadPoolExecutor

from app.extractors.PPTX.slide_iterator import extract_pptx_to_json
from app.reconstructors.pptx_reconstructor import reconstruct_pptx

def process_pptx_pipeline(file_path, filename, target_language, tgt_lang_code, output_folder, translate_func):
    
    base_name = os.path.splitext(filename)[0]
    json_filename = f"{base_name}.json"
    json_path = os.path.join(output_folder, json_filename)
    image_output_dir = os.path.join(output_folder, f"{base_name}_images")

    # 1. Extract
    extract_pptx_to_json(file_path, json_path, image_output_dir)
    with open(json_path, "r", encoding="utf-8") as f:
        pptx_data = json.load(f)

    # Basic cleaning
    def clean_string(text):
        if not isinstance(text, str):
            return text
        cleaned = text.replace('\x0b', '\n').replace('\xa0', ' ').replace('\r', '')
        # Remove strict invisible unicode characters
        cleaned = re.sub(r'[^\x00-\x7F\n]+', '', cleaned)
        return cleaned.strip()

    # 2. Collect Texts
    texts_to_translate = set()
    for slide_id, shapes in pptx_data.items():
        for shape in shapes:
            if shape.get("type") == "text_frame" and shape.get("original_text", "").strip():
                cleaned = clean_string(shape["original_text"])
                if cleaned: texts_to_translate.add(cleaned)
                    
            elif shape.get("type") == "table":
                for row in shape.get("original_data", []):
                    for cell in row:
                        cleaned = clean_string(cell)
                        if cleaned: texts_to_translate.add(cleaned)
                            
            elif shape.get("type") == "image":
                if shape.get("original_text", "").strip():
                    cleaned = clean_string(shape["original_text"])
                    if cleaned: texts_to_translate.add(cleaned)
                for ocr_item in shape.get("ocr_data", []):
                    cleaned = clean_string(ocr_item.get("text", ""))
                    if cleaned: texts_to_translate.add(cleaned)

    translation_texts = list(texts_to_translate)
    pptx_translation_cache = {}
    
    def safe_translate(text):
        lines = text.split('\n')
        translated_lines = []
        for line in lines:
            clean_line = line.strip()
            if not clean_line:
                translated_lines.append("")
                continue
                
            # Pehli koshish (Normal Translation)
            trans = translate_func(clean_line, "eng-latn", tgt_lang_code)

            if trans.strip().lower() == clean_line.lower():
                alt_line = clean_line.replace("-", " ") + " ."
                alt_trans = translate_func(alt_line, "eng-latn", tgt_lang_code)
            
                if alt_trans.strip().lower() != alt_line.lower():
                    trans = alt_trans.replace(" .", "").replace(".", "").replace("।", "").strip()
                    
            translated_lines.append(trans)
        return '\n'.join(translated_lines)

    # 3. Translate using the safe_translate function
    with ThreadPoolExecutor(max_workers=4) as executor:
        translated_texts = list(executor.map(safe_translate, translation_texts))

    for orig, trans in zip(translation_texts, translated_texts):
        pptx_translation_cache[orig] = trans

    # 4. Apply Translations
    for slide_id, shapes in pptx_data.items():
        for shape in shapes:
            if shape.get("type") == "text_frame":
                orig_clean = clean_string(shape.get("original_text", ""))
                shape["translated_text"] = pptx_translation_cache.get(orig_clean, orig_clean)
                
            elif shape.get("type") == "table":
                shape["translated_data"] = [
                    [pptx_translation_cache.get(clean_string(cell), clean_string(cell)) if cell.strip() else "" for cell in row]
                    for row in shape.get("original_data", [])
                ]
                
            elif shape.get("type") == "image":
                orig_clean = clean_string(shape.get("original_text", ""))
                shape["translated_text"] = pptx_translation_cache.get(orig_clean, orig_clean)
                for ocr_item in shape.get("ocr_data", []):
                    orig_ocr_text = clean_string(ocr_item.get("text", ""))
                    ocr_item["translated_text"] = (
                        pptx_translation_cache.get(orig_ocr_text, orig_ocr_text)
                        if orig_ocr_text else ""
                    )

    translated_json_filename = f"{base_name}_translated_{target_language}.json"
    translated_json_path = os.path.join(output_folder, translated_json_filename)
    with open(translated_json_path, "w", encoding="utf-8") as f:
        json.dump(pptx_data, f, indent=4, ensure_ascii=False)

    # 5. Reconstruct
    reconstructed_filename = f"{base_name}_reconstructed_{target_language}.pptx"
    reconstructed_path = os.path.join(output_folder, reconstructed_filename)
    reconstruct_pptx(file_path, translated_json_path, reconstructed_path)

    return {
        "json_file": json_filename,
        "translated_json_file": translated_json_filename,
        "reconstructed_pptx_file": reconstructed_filename,
        "data": pptx_data
    }