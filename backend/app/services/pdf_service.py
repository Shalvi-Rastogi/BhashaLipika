import os
import re
import json

from concurrent.futures import ThreadPoolExecutor

from app.extractors.PDF.pdf_detector import detect_pdf_type
from app.extractors.PDF.native.native_pdf_extractor import extract_native_pdf_to_json
from app.reconstructors.PDF.native_pdf_reconstructor import reconstruct_native_pdf


def _fix_colon(original_text, translated, target_language):
    
    if target_language in ("hi", "mr") and ":" in original_text and "ः" in translated:
        translated = re.sub(r"ः(?=\s|$)", ":", translated)
    return translated


def process_pdf_pipeline(
    file_path,
    filename,
    target_language,
    tgt_lang_code,
    output_folder,
    translate_func,
):
    base_name = os.path.splitext(filename)[0]

    print("\n====================================")
    print(f"[PDF] Processing: {filename}")

    # 1. DETECT PDF TYPE
    pdf_type = detect_pdf_type(file_path)
    print(f"[PDF] Detected type: {pdf_type}")

    if pdf_type != "native":
        # raise ValueError(
        #     "Scanned PDF detected. Scanned PDF pipeline is not implemented yet."
        # )
        print("[PDF] Continuing with image extraction test...")

    # 2. ORIGINAL JSON 
    json_filename = f"{base_name}.json"
    json_path = os.path.join(output_folder, json_filename)

    pdf_data = extract_native_pdf_to_json(file_path, json_path)

    # 3. COLLECT TEXT FOR TRANSLATION
    texts = set()

    for page in pdf_data.get("pages", []):
        for element in page.get("elements", []):
            if element.get("type") == "text":
                text = element.get("original_text", "")
                if isinstance(text, str) and text.strip():
                    texts.add(text.strip())
            elif element.get("type") == "table":
                for row in element.get("rows", []):
                    for cell in row.get("cells", []):
                        text = cell.get("original_text", "")
                        if isinstance(text, str) and text.strip():
                            texts.add(text.strip())
        # Text detected inside images using OCR
        for image in page.get("images", []):

            for ocr_item in image.get("ocr_data", []):

                text = ocr_item.get("text", "")

                if isinstance(text, str) and text.strip():
                    texts.add(text.strip())

    texts = list(texts)
    print(f"[PDF] Texts found for translation: {len(texts)}")

    # 4. TRANSLATE (parallel)
    def translate_one(text):
        try:
            result = translate_func(text, "eng-latn", tgt_lang_code)

            if not result:
                print(f"[PDF] Empty translation for: {text!r}")
                return text

            return result

        except Exception as e:
            print(f"[PDF] Translation failed for '{text[:40]}': {e}")
            return text

    with ThreadPoolExecutor(max_workers=4) as executor:
        translated_texts = list(executor.map(translate_one, texts))

    translation_cache = dict(zip(texts, translated_texts))
    print(f"[PDF] Translation cache created: {len(translation_cache)} entries")

    # 5. APPLY TRANSLATIONS
    for page in pdf_data.get("pages", []):
        for element in page.get("elements", []):
            if element.get("type") == "text":
                original_text = element.get("original_text", "")
                if not isinstance(original_text, str) or not original_text.strip():
                    continue

                translated = translation_cache.get(original_text.strip(), original_text)
                element["translated_text"] = _fix_colon(
                    original_text, translated, target_language
                )
            elif element.get("type") == "table":
                for row in element.get("rows", []):
                    for cell in row.get("cells", []):
                        original_text = cell.get("original_text", "")
                        if not isinstance(original_text, str) or not original_text.strip():
                            continue

                        translated = translation_cache.get(
                            original_text.strip(), original_text
                        )
                        cell["translated_text"] = _fix_colon(
                            original_text, translated, target_language
                        )
        # Apply translations to OCR text inside images
        for image in page.get("images", []):

            translated_ocr = []

            for ocr_item in image.get("ocr_data", []):

                original_text = ocr_item.get("text", "")

                if not isinstance(original_text, str):
                    continue

                original_text = original_text.strip()

                if not original_text:
                    continue

                translated = translation_cache.get(
                    original_text,
                    original_text
                )

                translated = _fix_colon(
                    original_text,
                    translated,
                    target_language
                )

                translated_ocr.append({
                    "text": original_text,
                    "confidence": ocr_item.get("confidence", 0),
                    "bbox": ocr_item.get("bbox"),
                    "translated_text": translated
                })

            image["translated_text"] = translated_ocr

    # 6. TRANSLATED JSON
    translated_json_filename = f"{base_name}_translated_{target_language}.json"
    translated_json_path = os.path.join(output_folder, translated_json_filename)

    with open(translated_json_path, "w", encoding="utf-8") as file:
        json.dump(pdf_data, file, indent=4, ensure_ascii=False)

    print(f"[PDF] Translated JSON created: {translated_json_path}")

    # 7. RECONSTRUCT PDF
    reconstructed_filename = f"{base_name}_reconstructed_{target_language}.pdf"
    reconstructed_path = os.path.join(output_folder, reconstructed_filename)

    print("[PDF] Starting reconstruction...")

    reconstruct_native_pdf(
        original_pdf_path=file_path,
        translated_json_path=translated_json_path,
        output_pdf_path=reconstructed_path,
        target_language=target_language,
    )

    print(f"[PDF] Reconstruction completed: {reconstructed_path}")
    print("====================================")

    # 8. RETURN
    return {
        "pdf_type": pdf_type,
        "json_file": json_filename,
        "translated_json_file": translated_json_filename,
        "reconstructed_pdf_file": reconstructed_filename,
        "data": pdf_data,
    }