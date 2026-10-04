import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


# =========================================================
# PDF IMPORTS
# =========================================================

from app.extractors.PDF.pdf_detector import detect_pdf_type

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

OCR_LANGUAGE_CODES = {
    "eng-latn": "en",
    "hin-deva": "hi",
    "mar-deva": "mr",
    "urd-arab": "ur",
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


def _fix_colon(original_text, translated_text, target_language=None):
    """Fix colon rendering issues that appear after translation."""

    if not isinstance(original_text, str):
        return translated_text

    if not isinstance(translated_text, str):
        return translated_text

    if ":" in original_text and "ः" in translated_text:
        return translated_text.replace("ः", ":")

    return translated_text


# =========================================================
# TRANSLATION HELPER
# =========================================================

def _translate_text(
    text,
    translate_func,
    source_language,
    target_language,
):
    """
    Ek text ko translation API/function ke through translate karta hai.
    """

    text = _clean_text(text)

    if not text:
        return ""

    # Same language
    if source_language == target_language:
        return text

    try:

        result = translate_func(
            text,
            source_language,
            target_language
        )

        translated = _normalise_translation(result)

        if translated:
            return translated

        raise RuntimeError(
            f"PDF translator returned an empty result for "
            f"{ascii(text[:80])}."
        )

    except Exception as error:

        print(
            f"[PDF][ERROR] Translation failed for "
            f"{ascii(text[:80])}: {error}"
        )

        raise RuntimeError(
            f"PDF translation failed for {ascii(text[:80])}."
        ) from error


# =========================================================
# COLLECT TEXT
# =========================================================

def _collect_translatable_texts(document_data):
    """
    PDF JSON se:
      1. normal text elements
      2. segment text
      3. table cell text
      4. image OCR text

    sab collect karta hai.

    Duplicate text ko sirf ek baar translate kiya jayega.
    """

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

        for image in page.get("images", []):
            for ocr_item in image.get("ocr_data", []):
                text = _clean_text(ocr_item.get("text", ""))
                if text:
                    texts.add(text)

    return texts


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

    if not texts:
        return translation_cache

    print(
        f"[PDF] Total unique texts to translate: {len(texts)}"
    )

    failures = []

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

                print(
                    f"[PDF][ERROR] Future failed for "
                    f"{original_text[:80]!r}: {error}"
                )

                failures.append((original_text, error))
                continue

            if not translated_text:
                failures.append(
                    (
                        original_text,
                        RuntimeError("Translator returned an empty result.")
                    )
                )
                continue

            translation_cache[original_text] = translated_text

            print(
                f"[PDF] TRANSLATED: "
                f"{ascii(original_text[:50])} -> "
                f"{ascii(translation_cache[original_text][:50])}"
            )

    if failures:
        failed_text, error = failures[0]
        raise RuntimeError(
            f"PDF translation failed for {len(failures)} text item(s); "
            f"first failed item: {ascii(failed_text[:80])}."
        ) from error

    return translation_cache


# =========================================================
# APPLY TRANSLATIONS TO JSON
# =========================================================

def _apply_translations(
    document_data,
    translation_cache,
):
    """
    Translation cache ko actual JSON structure me put karta hai.

    Important:
    segments ke translated_text ko bhi yahin populate kiya jata hai.
    Table cells aur image OCR ka translated_text bhi yahin populate hota hai.
    """

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

        for image in page.get("images", []):
            translated_texts = []

            for ocr_item in image.get("ocr_data", []):
                original_text = _clean_text(ocr_item.get("text", ""))

                if not original_text:
                    ocr_item["translated_text"] = ""
                    continue

                translated_text = translation_cache.get(
                    original_text,
                    original_text
                )

                if (
                    ":" in original_text
                    and "ः" in translated_text
                ):
                    translated_text = translated_text.replace("ः", ":")

                ocr_item["translated_text"] = translated_text
                translated_texts.append(ocr_item)

            image["translated_text"] = translated_texts

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
    source_language="eng-latn",
    source_language_name=None,
):
    """
    Complete Native PDF pipeline:

    1. Original PDF
          ↓
    2. Original extracted JSON
          ↓
    3. Translation
          ↓
    4. Translated JSON
          ↓
    5. Reconstructed translated PDF
    """

    # 1. DETECT PDF TYPE
    pdf_type = detect_pdf_type(file_path)
    print(f"[PDF] Detected type: {pdf_type}")

    if pdf_type != "native":
        # raise ValueError(
        #     "Scanned PDF detected. Scanned PDF pipeline is not implemented yet."
        # )
        print("[PDF] Continuing with image extraction test...")

    if translate_func is None:
        raise ValueError(
            "translate_func is required for PDF translation."
        )

    # =========================================================
    # OUTPUT DIRECTORY
    # =========================================================

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
    print(f"[PDF] Source code : {source_language}")
    print(f"[PDF] Target      : {language_key}")
    print(f"[PDF] Target code : {tgt_lang_code}")
    print("=" * 70)

    # ---------- PDF type check (optional) ----------
    # pdf_type = detect_pdf_type(file_path)
    # print(f"[PDF] Detected type: {pdf_type}")
    # if pdf_type != "native":
    #     raise ValueError("Scanned PDF pipeline is not implemented yet.")

    base_name = os.path.splitext(
        os.path.basename(filename)
    )[0]
    source_language_key = (
        source_language_name
        or source_language.split("-")[0]
    )

    original_json_path = os.path.join(
        output_folder,
        f"{base_name}_original.json"
    )

    original_json_path = os.path.join(output_folder, f"{base_name}_original.json")
    translated_json_path = os.path.join(
        output_folder,
        f"{base_name}_translated_"
        f"{source_language_key}_to_{language_key}.json"
    )
    reconstructed_pdf_path = os.path.join(
        output_folder,
        f"{base_name}_reconstructed_"
        f"{source_language_key}_to_{language_key}.pdf"
    )

    # ---------- Step 1: Extract ----------
    print("[PDF] Step 1: Extracting native PDF...")
    document_data = extract_native_pdf_to_json(file_path, original_json_path)
    print(f"[PDF] Original JSON created: {original_json_path}")

    ocr_language = OCR_LANGUAGE_CODES.get(source_language, "en")
    ocr_languages = [ocr_language]
    if ocr_language != "en":
        ocr_languages.append("en")

    document_data = extract_native_pdf_to_json(
        file_path,
        original_json_path,
        ocr_languages=ocr_languages
    )

    print(
        f"[PDF] Original JSON created: "
        f"{original_json_path}"
    )

    # =========================================================
    # STEP 2: COLLECT TEXT
    # =========================================================

    print("[PDF] Step 2: Collecting text...")
    texts = _collect_translatable_texts(document_data)
    print(f"[PDF] Text items found: {len(texts)}")

    # ---------- Step 3: Translate ----------
    print("[PDF] Step 3: Translating text...")
    translation_cache = _translate_unique_texts(
        texts=texts,
        translate_func=translate_func,
        source_language=source_language,
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

    translated_count = 0
    total_count = 0

    for page in document_data.get("pages", []):

        for element in page.get("elements", []):

            if element.get("type") == "text":

                segments = element.get("segments") or []

                if segments:

                    for segment in segments:

                        if segment.get("text", "").strip():

                            total_count += 1

                            if segment.get(
                                "translated_text",
                                ""
                            ).strip():

                                translated_count += 1

                elif element.get(
                    "original_text",
                    ""
                ).strip():

                    total_count += 1

                    if element.get(
                        "translated_text",
                        ""
                    ).strip():

                        translated_count += 1

            elif element.get("type") == "table":

                for row in element.get("rows", []):

                    for cell in row.get("cells", []):
                        text = cell.get("original_text", "")
                        if isinstance(text, str) and text.strip():
                            total_count += 1
                            if cell.get("translated_text", "").strip():
                                translated_count += 1

        for image in page.get("images", []):

            for ocr_item in image.get("ocr_data", []):

                text = ocr_item.get("text", "")

                if isinstance(text, str) and text.strip():
                    total_count += 1

                    translated_text = ocr_item.get(
                        "translated_text",
                        ""
                    )

                    if isinstance(
                        translated_text,
                        str
                    ) and translated_text.strip():
                        translated_count += 1

    print(
        f"[PDF] Translation coverage: "
        f"{translated_count}/{total_count}"
    )

    # =========================================================
    # STEP 5: SAVE TRANSLATED JSON
    # =========================================================

    print(
        "[PDF] Step 5: Saving translated JSON..."
    )

    with open(
        translated_json_path,
        "w",
        encoding="utf-8"
    ) as json_file:

        json.dump(
            document_data,
            json_file,
            indent=4,
            ensure_ascii=False
        )

    # =========================================================
    # STEP 6: RECONSTRUCT PDF
    # =========================================================

    print(
        "[PDF] Step 6: Reconstructing translated PDF..."
    )

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

    return {
        "json_file": os.path.basename(original_json_path),
        "translated_json_file": os.path.basename(translated_json_path),
        "reconstructed_pdf_file": os.path.basename(reconstructed_pdf_path),
        "reconstructed_file": os.path.basename(reconstructed_pdf_path),
        "output_filename": os.path.basename(reconstructed_pdf_path),
        "data": document_data,
    }
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