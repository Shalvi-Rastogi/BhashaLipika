import os
import json
from concurrent.futures import ThreadPoolExecutor

from app.extractors.XLSX.sheet_iterator import extract_xlsx_to_json 
from app.reconstructors.xlsx_reconstructor import reconstruct_xlsx

def process_xlsx_pipeline(file_path, filename, target_language, tgt_lang_code, output_folder, translate_func):
    
    base_name = os.path.splitext(filename)[0]
    json_filename = f"{base_name}.json"
    json_path = os.path.join(output_folder, json_filename)

    # 1. Extract
    extract_xlsx_to_json(file_path, json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        xlsx_data = json.load(f)

    # 2. Collect Texts from DOCX-like structure
    texts_to_translate = set()
    for sheet in xlsx_data.get("sheets", []):
        for cell in sheet.get("cells", []):
            text_val = cell.get("text")
            if isinstance(text_val, str) and text_val.strip():
                texts_to_translate.add(text_val.strip())
                
    translation_texts = list(texts_to_translate)
    translation_cache = {}

    # 3. Translate (PPTX wala strict logic for C-DAC API)
    def safe_translate(text):
        clean_line = text.strip()
        if not clean_line:
            return ""
        trans = translate_func(clean_line, "eng-latn", tgt_lang_code)
        
        if trans.strip().lower() == clean_line.lower():
            alt_line = clean_line.replace("-", " ") + " ."
            alt_trans = translate_func(alt_line, "eng-latn", tgt_lang_code)
            if alt_trans.strip().lower() != alt_line.lower():
                trans = alt_trans.replace(" .", "").replace(".", "").replace("।", "").strip()
        return trans

    with ThreadPoolExecutor(max_workers=4) as executor:
        translated_texts = list(executor.map(safe_translate, translation_texts))

    for orig, trans in zip(translation_texts, translated_texts):
        translation_cache[orig] = trans

    # 4. Apply Translations back
    for sheet in xlsx_data.get("sheets", []):
        for cell in sheet.get("cells", []):
            text_val = cell.get("text")
            if isinstance(text_val, str) and text_val.strip():
                orig = text_val.strip()
                translated_val = translation_cache.get(orig, orig)
                
                # Main text field aur runs dono update karein
                cell["translated_text"] = translated_val
                for run in cell.get("runs", []):
                    if run.get("text") == orig:
                        run["translated_text"] = translated_val

    translated_json_filename = f"{base_name}_translated_{target_language}.json"
    translated_json_path = os.path.join(output_folder, translated_json_filename)
    with open(translated_json_path, "w", encoding="utf-8") as f:
        json.dump(xlsx_data, f, indent=4, ensure_ascii=False)

    # 5. Reconstruct
    reconstructed_filename = f"{base_name}_reconstructed_{target_language}.xlsx"
    reconstructed_path = os.path.join(output_folder, reconstructed_filename)
    reconstruct_xlsx(file_path, translated_json_path, reconstructed_path)

    return {
        "json_file": json_filename,
        "translated_json_file": translated_json_filename,
        "reconstructed_file": reconstructed_filename,
        "data": xlsx_data
    }