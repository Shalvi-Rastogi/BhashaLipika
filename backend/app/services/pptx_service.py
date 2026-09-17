import os
import json
from concurrent.futures import ThreadPoolExecutor

from app.extractors.PPTX.slide_iterator import extract_pptx_to_json
from app.reconstructors.pptx_reconstructor import reconstruct_pptx

# Dhyan dein: Humne yahan "translate_func" as parameter add kiya hai
def process_pptx_pipeline(file_path, filename, target_language, tgt_lang_code, output_folder, translate_func):
    
    base_name = os.path.splitext(filename)[0]
    json_filename = f"{base_name}.json"
    json_path = os.path.join(output_folder, json_filename)
    image_output_dir = os.path.join(output_folder, f"{base_name}_images")

    # 1. Extract
    extract_pptx_to_json(file_path, json_path, image_output_dir)
    with open(json_path, "r", encoding="utf-8") as f:
        pptx_data = json.load(f)

    # 2. Collect Texts
    texts_to_translate = set()
    for slide_id, shapes in pptx_data.items():
        for shape in shapes:
            if shape.get("type") == "text_frame" and shape.get("original_text", "").strip():
                texts_to_translate.add(shape["original_text"])
            elif shape.get("type") == "table":
                for row in shape.get("original_data", []):
                    for cell in row:
                        if cell.strip(): 
                            texts_to_translate.add(cell)
            elif shape.get("type") == "image":
                if shape.get("original_text", "").strip():
                    texts_to_translate.add(shape["original_text"])

    translation_texts = list(texts_to_translate)
    pptx_translation_cache = {}
    
    # 3. Translate using the passed function (translate_func)
    with ThreadPoolExecutor(max_workers=4) as executor:
        translated_texts = list(executor.map(
            lambda text: translate_func(text, "eng-latn", tgt_lang_code), 
            translation_texts
        ))

    for orig, trans in zip(translation_texts, translated_texts):
        pptx_translation_cache[orig] = trans

    # 4. Apply Translations
    for slide_id, shapes in pptx_data.items():
        for shape in shapes:
            if shape.get("type") == "text_frame":
                orig = shape.get("original_text", "")
                shape["translated_text"] = pptx_translation_cache.get(orig, orig)
            elif shape.get("type") == "table":
                shape["translated_data"] = [
                    [pptx_translation_cache.get(cell, cell) if cell.strip() else "" for cell in row]
                    for row in shape.get("original_data", [])
                ]
            elif shape.get("type") == "image":
                orig = shape.get("original_text", "")
                shape["translated_text"] = pptx_translation_cache.get(
                    orig,
                    orig
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