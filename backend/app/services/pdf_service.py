import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.extractors.PDF.native.native_pdf_extractor import (
    extract_native_pdf_to_json
)
from app.reconstructors.PDF.native_pdf_reconstructor import (
    reconstruct_native_pdf
)

# Agar tumhare paas detect_pdf_type hai to uska import yahan add karo, e.g.:
# from app.extractors.PDF.pdf_type_detector import detect_pdf_type


# =========================================================
# LANGUAGE MAPPING
# =========================================================

LANGUAGE_CODES = {
    "en": "eng-latn",
    "english": "eng-latn",
    "hi": "hin-deva",
    "hindi": "hin-deva",
    "mr": "mar-deva",
    "marathi": "mar-deva",
    "ur": "urd-arab",
    "urdu": "urd-arab",
}


# =========================================================
# BASIC HELPERS
# =========================================================

def _clean_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()


def _normalise_translation(result):
    """translate_func ka result (str/dict/list) -> final string."""

    if result is None:
        return ""

    if isinstance(result, str):
        return result.strip()

    if isinstance(result, dict):
        for key in (
            "translated_text", "translation", "translated",
            "text", "output", "result",
        ):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for value in result.values():
            if isinstance(value, str) and value.strip():
                return value.strip()

    if isinstance(result, list):
        for item in result:
            value = _normalise_translation(item)
            if value:
                return value

    return ""


def _fix_colon(original, translated, target_language=None):
    """Hindi/Marathi translation mein ':' ki jagah 'ः' aa jata hai, usse fix karta hai."""
    if ":" in original and "ः" in translated:
        return translated.replace("ः", ":")
    return translated


# =========================================================
# COLLECT TEXT
# =========================================================

def _collect_translatable_texts(document_data):
    texts = set()

    for page in document_data.get("pages", []):
        for element in page.get("elements", []):
            element_type = element.get("type")

            if element_type == "text":
                segments = element.get("segments") or []

                if segments:
                    for segment in segments:
                        text = _clean_text(segment.get("text", ""))
                        if text:
                            texts.add(text)
                else:
                    text = _clean_text(element.get("original_text", ""))
                    if text:
                        texts.add(text)

            elif element_type == "table":
                for row in element.get("rows", []):
                    for cell in row.get("cells", []):
                        text = _clean_text(cell.get("original_text", ""))
                        if text:
                            texts.add(text)

    return list(texts)


# =========================================================
# TRANSLATION
# =========================================================

def _translate_text(text, translate_func, source_language, target_language):
    try:
        result = translate_func(text, source_language, target_language)
        translated = _normalise_translation(result)

        if not translated:
            print(f"[PDF] Empty translation for: {text!r}")
            return text

        return translated

    except Exception as e:
        print(f"[PDF] Translation failed for '{text[:40]}': {e}")
        return text


def _translate_unique_texts(texts, translate_func, source_language, target_language):
    translation_cache = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_text = {
            executor.submit(
                _translate_text,
                text,
                translate_func,
                source_language,
                target_language,
            ): text
            for text in texts
        }

        for future in as_completed(future_to_text):
            original_text = future_to_text[future]

            try:
                translated_text = future.result()
            except Exception as error:
                print(f"[PDF][ERROR] Future failed for {original_text[:80]!r}: {error}")
                translated_text = original_text

            translation_cache[original_text] = translated_text or original_text

            print(
                f"[PDF] TRANSLATED: {original_text[:50]!r} -> "
                f"{translation_cache[original_text][:50]!r}"
            )

    return translation_cache


# =========================================================
# APPLY TRANSLATIONS TO JSON
# =========================================================

def _apply_translations(document_data, translation_cache, target_language=None):

    for page in document_data.get("pages", []):
        for element in page.get("elements", []):
            element_type = element.get("type")

            # ---------------- TEXT ----------------
            if element_type == "text":
                segments = element.get("segments") or []

                if segments:
                    translated_segments = []

                    for segment in segments:
                        original_segment = _clean_text(segment.get("text", ""))

                        if not original_segment:
                            segment["translated_text"] = ""
                            continue

                        translated_segment = translation_cache.get(
                            original_segment, original_segment
                        )
                        translated_segment = _fix_colon(
                            original_segment, translated_segment, target_language
                        )

                        segment["translated_text"] = translated_segment
                        translated_segments.append(translated_segment)

                    element["translated_text"] = " ".join(
                        x.strip() for x in translated_segments if x and x.strip()
                    )

                else:
                    original_text = _clean_text(element.get("original_text", ""))
                    translated_text = translation_cache.get(
                        original_text, original_text
                    )
                    element["translated_text"] = _fix_colon(
                        original_text, translated_text, target_language
                    )

            # ---------------- TABLE ----------------
            elif element_type == "table":
                for row in element.get("rows", []):
                    for cell in row.get("cells", []):
                        original_text = _clean_text(cell.get("original_text", ""))

                        if not original_text:
                            cell["translated_text"] = ""
                            continue

                        translated = translation_cache.get(
                            original_text, original_text
                        )
                        cell["translated_text"] = _fix_colon(
                            original_text, translated, target_language
                        )

    return document_data


# =========================================================
# COVERAGE CHECK
# =========================================================

def _count_coverage(document_data):
    translated_count = 0
    total_count = 0

    for page in document_data.get("pages", []):
        for element in page.get("elements", []):
            element_type = element.get("type")

            if element_type == "text":
                segments = element.get("segments") or []

                if segments:
                    for segment in segments:
                        if segment.get("text", "").strip():
                            total_count += 1
                            if segment.get("translated_text", "").strip():
                                translated_count += 1

                elif element.get("original_text", "").strip():
                    total_count += 1
                    if element.get("translated_text", "").strip():
                        translated_count += 1

            elif element_type == "table":
                for row in element.get("rows", []):
                    for cell in row.get("cells", []):
                        if cell.get("original_text", "").strip():
                            total_count += 1
                            if cell.get("translated_text", "").strip():
                                translated_count += 1

    return translated_count, total_count


# =========================================================
# MAIN PIPELINE
# =========================================================
# NOTE: function ka naam aur parameters wahi rakho jo tumhare router/caller
# use kar raha hai (git se check kar lena: git show HEAD:app/services/pdf_service.py)

def process_pdf_pipeline(
    file_path,
    filename,
    target_language="hi",
    tgt_lang_code=None,
    output_folder=None,
    translate_func=None,
):
    # ---------- Output dir ----------
    if output_folder is None:
        output_folder = os.path.dirname(file_path)
    os.makedirs(output_folder, exist_ok=True)

    # ---------- Language ----------
    language_key = (target_language or "hi").lower().strip()

    if tgt_lang_code is None:
        tgt_lang_code = LANGUAGE_CODES.get(language_key)

    if not tgt_lang_code:
        raise ValueError(f"Unsupported target language: {target_language}")

    print("=" * 70)
    print("[PDF] Starting PDF pipeline")
    print(f"[PDF] Input       : {file_path}")
    print(f"[PDF] Target      : {language_key}")
    print(f"[PDF] Target code : {tgt_lang_code}")
    print("=" * 70)

    # ---------- PDF type check (optional) ----------
    # pdf_type = detect_pdf_type(file_path)
    # print(f"[PDF] Detected type: {pdf_type}")
    # if pdf_type != "native":
    #     raise ValueError("Scanned PDF pipeline is not implemented yet.")

    # ---------- File names ----------
    base_name = os.path.splitext(os.path.basename(filename))[0]

    original_json_path = os.path.join(output_folder, f"{base_name}_original.json")
    translated_json_path = os.path.join(
        output_folder, f"{base_name}_translated_{language_key}.json"
    )
    reconstructed_pdf_path = os.path.join(
        output_folder, f"{base_name}_reconstructed_{language_key}.pdf"
    )

    # ---------- Step 1: Extract ----------
    print("[PDF] Step 1: Extracting native PDF...")
    document_data = extract_native_pdf_to_json(file_path, original_json_path)
    print(f"[PDF] Original JSON created: {original_json_path}")

    # ---------- Step 2: Collect ----------
    print("[PDF] Step 2: Collecting text...")
    texts = _collect_translatable_texts(document_data)
    print(f"[PDF] Text items found: {len(texts)}")

    # ---------- Step 3: Translate ----------
    print("[PDF] Step 3: Translating text...")
    translation_cache = _translate_unique_texts(
        texts=texts,
        translate_func=translate_func,
        source_language="eng-latn",
        target_language=tgt_lang_code,
    )

    if not translation_cache and texts:
        raise RuntimeError(
            "PDF translation failed: no translations were returned by translate_func."
        )

    # ---------- Step 4: Apply ----------
    print("[PDF] Step 4: Applying translations to JSON...")
    document_data = _apply_translations(
        document_data, translation_cache, language_key
    )

    translated_count, total_count = _count_coverage(document_data)
    print(f"[PDF] Translation coverage: {translated_count}/{total_count}")

    # ---------- Step 5: Save JSON ----------
    print("[PDF] Step 5: Saving translated JSON...")
    with open(translated_json_path, "w", encoding="utf-8") as json_file:
        json.dump(document_data, json_file, indent=4, ensure_ascii=False)
    print(f"[PDF] Translated JSON created: {translated_json_path}")

    # ---------- Step 6: Reconstruct ----------
    print("[PDF] Step 6: Reconstructing translated PDF...")
    reconstruct_native_pdf(
        original_pdf_path=file_path,
        translated_json_path=translated_json_path,
        output_pdf_path=reconstructed_pdf_path,
        target_language=language_key,
    )
    print(f"[PDF] Reconstructed PDF created: {reconstructed_pdf_path}")

    print("=" * 70)
    print("[PDF] PIPELINE COMPLETED")
    print("=" * 70)

    return {
        "status": "success",
        "document_name": filename,
        "pdf_type": "native",
        "target_language": language_key,
        "original_json": original_json_path,
        "translated_json": translated_json_path,
        "reconstructed_pdf": reconstructed_pdf_path,
        "translation_count": translated_count,
        "total_translatable_items": total_count,
        "data": document_data,
    }