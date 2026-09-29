import os
import json

from concurrent.futures import ThreadPoolExecutor

from app.extractors.PDF.pdf_detector import (
    detect_pdf_type
)

from app.extractors.PDF.native.native_pdf_extractor import (
    extract_native_pdf_to_json
)

from app.reconstructors.PDF.native_pdf_reconstructor import (
    reconstruct_native_pdf
)


def process_pdf_pipeline(
    file_path,
    filename,
    target_language,
    tgt_lang_code,
    output_folder,
    translate_func
):

    base_name = os.path.splitext(
        filename
    )[0]

    print(
        "\n===================================="
    )

    print(
        f"[PDF] Processing: {filename}"
    )

    # =====================================================
    # 1. DETECT PDF TYPE
    # =====================================================

    pdf_type = detect_pdf_type(
        file_path
    )

    print(
        f"[PDF] Detected type: {pdf_type}"
    )

    if pdf_type != "native":

        raise ValueError(
            "Scanned PDF detected. "
            "Scanned PDF pipeline is not implemented yet."
        )

    # =====================================================
    # 2. ORIGINAL JSON
    # =====================================================

    json_filename = (
        f"{base_name}.json"
    )

    json_path = os.path.join(
        output_folder,
        json_filename
    )

    extract_native_pdf_to_json(
        file_path,
        json_path
    )

    # =====================================================
    # 3. LOAD JSON
    # =====================================================

    with open(
        json_path,
        "r",
        encoding="utf-8"
    ) as file:

        pdf_data = json.load(
            file
        )

    # =====================================================
    # 4. COLLECT TEXT
    # =====================================================

    texts = set()

    for page in pdf_data.get(
        "pages",
        []
    ):

        for element in page.get(
            "elements",
            []
        ):

            if element.get(
                "type"
            ) != "text":
                continue

            text = element.get(
                "original_text",
                ""
            )

            if (
                isinstance(text, str)
                and text.strip()
            ):

                texts.add(
                    text.strip()
                )

    texts = list(texts)

    print(
        f"[PDF] Texts found for translation: "
        f"{len(texts)}"
    )

    # =====================================================
    # 5. TRANSLATE
    # =====================================================

    translation_cache = {}

    def translate_one(text):

        try:

            result = translate_func(
                text,
                "eng-latn",
                tgt_lang_code
            )

            if not result:
                return text

            return result

        except Exception as e:

            print(
                f"[PDF] Translation failed "
                f"for '{text[:40]}': {e}"
            )

            return text

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:

        translated_texts = list(
            executor.map(
                translate_one,
                texts
            )
        )

    for original, translated in zip(
        texts,
        translated_texts
    ):

        translation_cache[
            original
        ] = translated

    # =====================================================
    # 6. APPLY TRANSLATIONS
    # =====================================================

    for page in pdf_data.get(
        "pages",
        []
    ):

        for element in page.get(
            "elements",
            []
        ):

            original_text = element.get(
                "original_text",
                ""
            )

            if original_text.strip():

                element[
                    "translated_text"
                ] = translation_cache.get(
                    original_text.strip(),
                    original_text
                )

    # =====================================================
    # 7. TRANSLATED JSON
    # =====================================================

    translated_json_filename = (
        f"{base_name}_translated_{target_language}.json"
    )

    translated_json_path = os.path.join(
        output_folder,
        translated_json_filename
    )

    with open(
        translated_json_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            pdf_data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"[PDF] Translated JSON created: "
        f"{translated_json_path}"
    )

    # =====================================================
    # 8. RECONSTRUCT PDF
    # =====================================================

    reconstructed_filename = (
        f"{base_name}_reconstructed_"
        f"{target_language}.pdf"
    )

    reconstructed_path = os.path.join(
        output_folder,
        reconstructed_filename
    )

    reconstruct_native_pdf(
        original_pdf_path=file_path,
        translated_json_path=translated_json_path,
        output_pdf_path=reconstructed_path,
        target_language=target_language
    )

    # =====================================================
    # 9. RETURN RESULT
    # =====================================================

    print(
        "===================================="
    )

    return {

        "pdf_type": pdf_type,

        "json_file":
            json_filename,

        "translated_json_file":
            translated_json_filename,

        "reconstructed_pdf_file":
            reconstructed_filename,

        "data":
            pdf_data
    }