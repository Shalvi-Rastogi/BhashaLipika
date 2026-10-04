import os
import json
from concurrent.futures import ThreadPoolExecutor

from app.extractors.XLSX.sheet_iterator import (
    extract_xlsx_to_json
)

from app.reconstructors.xlsx_reconstructor import (
    reconstruct_xlsx
)


# ============================================================
# XLSX TRANSLATION PIPELINE
# ============================================================

def process_xlsx_pipeline(
    file_path,
    filename,
    target_language,
    tgt_lang_code,
    output_folder,
    translate_func,
    source_language="eng-latn",
    source_language_name=None,
):

    print("\n========================================")
    print("XLSX TRANSLATION PIPELINE STARTED")
    print("========================================")

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    base_name = os.path.splitext(
        filename
    )[0]
    source_language_key = (
        source_language_name
        or source_language.split("-")[0]
    )

    # ========================================================
    # FILE 1
    # ORIGINAL EXTRACTED JSON
    # ========================================================

    json_filename = (
        f"{base_name}.json"
    )

    json_path = os.path.join(
        output_folder,
        json_filename
    )

    print(
        f"\n[XLSX] Extracting: {filename}"
    )

    xlsx_data = extract_xlsx_to_json(
        file_path,
        json_path
    )

    # ========================================================
    # COLLECT TEXTS
    # ========================================================

    texts_to_translate = set()

    def collect_texts(data):

        if isinstance(data, dict):

            # ------------------------------------------------
            # OCR text inside image boxes must also be translated.
            # ------------------------------------------------

            ocr_items = data.get("ocr_data")
            if isinstance(ocr_items, list):
                for item in ocr_items:
                    if not isinstance(item, dict):
                        continue

                    ocr_text = item.get("text")
                    if isinstance(ocr_text, str):
                        clean_text = ocr_text.strip()
                        if clean_text:
                            texts_to_translate.add(clean_text)

            # ------------------------------------------------
            # Text fields
            # ------------------------------------------------

            text_value = data.get(
                "original_text"
            )

            if not isinstance(
                text_value,
                str
            ):

                text_value = data.get(
                    "text"
                )

            if isinstance(
                text_value,
                str
            ):

                clean_text = text_value.strip()

                if clean_text:
                    texts_to_translate.add(
                        clean_text
                    )

            # ------------------------------------------------
            # Continue recursively
            # ------------------------------------------------

            for value in data.values():
                collect_texts(value)

        elif isinstance(data, list):

            for item in data:
                collect_texts(item)

    collect_texts(
        xlsx_data
    )

    translation_texts = list(
        texts_to_translate
    )

    print(
        f"\n[XLSX] Unique texts found for translation: "
        f"{len(translation_texts)}"
    )

    # ========================================================
    # TRANSLATION
    # ========================================================

    translation_cache = {}

    def safe_translate(text):

        clean_line = text.strip()

        if not clean_line:
            return ""

        try:

            print(
                f"[XLSX TRANSLATE] "
                f"{ascii(clean_line[:100])}"
            )

            translated = translate_func(
                clean_line,
                source_language,
                tgt_lang_code
            )

            if not isinstance(
                translated,
                str
            ):

                translated = str(
                    translated
                )

            translated = translated.strip()

            # ------------------------------------------------
            # Fallback used in your existing pipeline
            # ------------------------------------------------

            if (
                translated.lower()
                == clean_line.lower()
            ):

                alt_line = (
                    clean_line.replace(
                        "-",
                        " "
                    )
                    + " ."
                )

                alt_trans = translate_func(
                    alt_line,
                    source_language,
                    tgt_lang_code
                )

                if not isinstance(
                    alt_trans,
                    str
                ):

                    alt_trans = str(
                        alt_trans
                    )

                if (
                    alt_trans.strip().lower()
                    != alt_line.lower()
                ):

                    translated = (
                        alt_trans
                        .replace(
                            " .",
                            ""
                        )
                        .replace(
                            ".",
                            ""
                        )
                        .replace(
                            "।",
                            ""
                        )
                        .strip()
                    )

            if not translated:
                return clean_line

            return translated

        except Exception as e:

            print(
                f"[XLSX TRANSLATION ERROR] "
                f"{ascii(clean_line[:80])} -> {e}"
            )
            return clean_line

    if translation_texts:

        with ThreadPoolExecutor(
            max_workers=4
        ) as executor:

            translated_texts = list(
                executor.map(
                    safe_translate,
                    translation_texts
                )
            )

        for original, translated in zip(
            translation_texts,
            translated_texts
        ):

            translation_cache[
                original
            ] = translated

    # ========================================================
    # APPLY TRANSLATIONS TO JSON
    # ========================================================

    def apply_translations(data):

        if isinstance(data, dict):

            # Translate nested OCR text blocks inside image objects.
            ocr_items = data.get("ocr_data")
            if isinstance(ocr_items, list):
                for item in ocr_items:
                    if not isinstance(item, dict):
                        continue

                    ocr_text = item.get("text")
                    if isinstance(ocr_text, str):
                        clean_text = ocr_text.strip()
                        if clean_text:
                            item["translated_text"] = (
                                translation_cache.get(
                                    clean_text,
                                    clean_text
                                )
                            )

            text_value = data.get(
                "original_text"
            )

            if not isinstance(
                text_value,
                str
            ):

                text_value = data.get(
                    "text"
                )

            if isinstance(
                text_value,
                str
            ):

                original = text_value.strip()

                if original:

                    data["translated_text"] = (
                        translation_cache.get(
                            original,
                            original
                        )
                    )

            for value in data.values():

                # Prevent accidental recursion
                # into strings.
                if isinstance(
                    value,
                    (dict, list)
                ):

                    apply_translations(
                        value
                    )

        elif isinstance(data, list):

            for item in data:

                if isinstance(
                    item,
                    (dict, list)
                ):

                    apply_translations(
                        item
                    )

    apply_translations(
        xlsx_data
    )

    # ========================================================
    # FILE 2
    # TRANSLATED JSON
    # ========================================================

    translated_json_filename = (
        f"{base_name}_translated_"
        f"{source_language_key}_to_{target_language}.json"
    )

    translated_json_path = os.path.join(
        output_folder,
        translated_json_filename
    )

    with open(
        translated_json_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            xlsx_data,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\n[XLSX] Translated JSON saved: "
        f"{translated_json_path}"
    )

    # ========================================================
    # FILE 3
    # RECONSTRUCTED XLSX
    # ========================================================

    reconstructed_filename = (
        f"{base_name}_reconstructed_"
        f"{source_language_key}_to_{target_language}.xlsx"
    )

    reconstructed_path = os.path.join(
        output_folder,
        reconstructed_filename
    )

    print(
        "\n[XLSX] Starting reconstruction..."
    )

    reconstruct_xlsx(
        original_file_path=file_path,

        translated_json_path=translated_json_path,

        output_file_path=reconstructed_path
    )

    print(
        f"\n[XLSX] Reconstructed file: "
        f"{reconstructed_path}"
    )

    print("\n========================================")
    print("XLSX PIPELINE COMPLETED")
    print("========================================")

    # ========================================================
    # RETURN SAME STRUCTURE EXPECTED BY upload.py
    # ========================================================

    return {

        "json_file": json_filename,

        "translated_json_file":
            translated_json_filename,

        "reconstructed_file":
            reconstructed_filename,

        "data": xlsx_data
    }