import os
import json
import traceback
import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from docx import Document

from app.extractors.Docx.document_parser import parse_document
from app.reconstructors.docx_reconstructor import reconstruct_docx


router = APIRouter()


# =========================================================
# FOLDERS
# =========================================================

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# =========================================================
# ALLOWED FILE TYPES
# =========================================================

ALLOWED_EXTENSIONS = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".pptx": "PPTX",
    ".xlsx": "XLSX",
    ".rtf": "RTF"
}


# =========================================================
# C-DAC TRANSLATION API
# =========================================================

TRANSLATION_API_URL = (
    "https://nlpsangraha.ebhasha.in/getTranslation"
)


# =========================================================
# TARGET LANGUAGE MAPPING
# =========================================================

LANGUAGE_MAP = {
    "en": "eng-latn",
    "hi": "hin-deva",
    "mr": "mar-deva",
    "ur": "urd-arab"
}


# =========================================================
# TRANSLATE ONE TEXT (UPDATED FOR NEWLINES)
# =========================================================

# =========================================================
# TRANSLATE ONE TEXT (SMART PUNCTUATION PRESERVER)
# =========================================================

def translate_text(
    text,
    src_lang="eng-latn",
    tgt_lang="hin-deva"
):

    # Don't translate empty text
    if not text or not text.strip():
        return text
    if not any(vowel in text.lower() for vowel in 'aeiou'):
        return text
    # Handle Newlines (\n) to prevent merging
    if "\n" in text:
        lines = text.split("\n")
        translated_lines = []
        for line in lines:
            if line.strip():
                translated_lines.append(translate_text(line, src_lang, tgt_lang))
            else:
                translated_lines.append("")
        return "\n".join(translated_lines)

    # -----------------------------------------------------
    # FIX: Smart Punctuation Separation
    # Extracts leading/trailing symbols (like ": ") so API 
    # doesn't swallow them or add random full stops.
    # -----------------------------------------------------
    match = re.match(r'^([^\w]*)(.*?[\w])([^\w]*)$', text)
    
    if match:
        leading_chars = match.group(1)
        core_text = match.group(2)
        trailing_chars = match.group(3)
    else:
        # If there are no words/numbers (e.g., text is just " : ")
        # Don't translate it, just return original.
        return text

    # Only send the core text to the API
    payload = {
        "ip_text": core_text,
        "srcLang": src_lang,
        "tgtLang": tgt_lang,
        "delimiter": "",
        "nSuggestions": "1"
    }

    translated_core = core_text
    
    for attempt in range(3):
        try:
            response = requests.post(
                TRANSLATION_API_URL,
                json=payload,
                timeout=60,
                verify=False
            )
            response.raise_for_status()

            output = response.json().get("Output")
            if output:
                translated_core = output.strip()
                break

        except Exception as error:
            if attempt == 2:
                print("Translation API error:", str(error))
            time.sleep(2 ** attempt)

    # Clean up unwanted '।' (Purna Viram) added by the API
    # Keep it ONLY if the original English text ended with a period '.'
    if not core_text.endswith('.') and translated_core.endswith('।'):
        translated_core = translated_core.rstrip('।').strip()

    # Re-attach the exact leading and trailing symbols/spaces
    return leading_chars + translated_core + trailing_chars


# =========================================================
# TRANSLATE EXTRACTED JSON
# =========================================================

def translate_json(
    data,
    src_lang="eng-latn",
    tgt_lang="hin-deva",
    translation_cache=None
):

    if translation_cache is None:
        translation_cache = {}

    if isinstance(data, dict):

        # -----------------------------------------
        # Translate main text field
        # -----------------------------------------

        if (
            "text" in data
            and isinstance(data["text"], str)
        ):

            original_text = data["text"]

            cache_key = (original_text, src_lang, tgt_lang)
            if cache_key not in translation_cache:
                translation_cache[cache_key] = translate_text(
                    original_text,
                    src_lang,
                    tgt_lang
                )
            data["text"] = translation_cache[cache_key]


        # -----------------------------------------
        # Translate text inside runs
        # -----------------------------------------

        if (
            "runs" in data
            and isinstance(data["runs"], list)
        ):

            for run in data["runs"]:

                if (
                    isinstance(run, dict)
                    and "text" in run
                    and isinstance(run["text"], str)
                ):
                    original_text = run["text"]
                    cache_key = (original_text, src_lang, tgt_lang)
                    if cache_key not in translation_cache:
                        translation_cache[cache_key] = translate_text(
                            original_text,
                            src_lang,
                            tgt_lang
                        )
                    run["text"] = translation_cache[cache_key]


        # -----------------------------------------
        # Process nested objects
        # -----------------------------------------

        for key, value in data.items():

            if key not in ["text", "runs", "original_text"]:

                data[key] = translate_json(
                    value,
                    src_lang,
                    tgt_lang,
                    translation_cache
                )

        return data


    elif isinstance(data, list):

        return [
            translate_json(
                item,
                src_lang,
                tgt_lang,
                translation_cache
            )
            for item in data
        ]


    return data


def collect_translation_texts(data, texts=None):
    """Collect canonical text fields without structural duplicates."""

    if texts is None:
        texts = set()

    if isinstance(data, dict):
        text = data.get("text")
        if isinstance(text, str) and text.strip():
            texts.add(text)

        for key, value in data.items():
            if key not in ["text", "runs", "original_text"]:
                collect_translation_texts(value, texts)

    elif isinstance(data, list):
        for item in data:
            collect_translation_texts(item, texts)

    return texts


# =========================================================
# UPLOAD API
# =========================================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    target_language: str = Form(...)
):

    try:

        # =================================================
        # 1. CHECK FILE EXTENSION
        # =================================================

        extension = os.path.splitext(
            file.filename
        )[1].lower()

        if extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(
                status_code=400,
                detail="Unsupported file type"
            )


        file_type = ALLOWED_EXTENSIONS[extension]


        # =================================================
        # 2. SAVE UPLOADED FILE
        # =================================================

        file_path = os.path.join(
            UPLOAD_FOLDER,
            file.filename
        )

        with open(
            file_path,
            "wb"
        ) as buffer:

            buffer.write(
                await file.read()
            )

        print(
            f"File saved: {file_path}"
        )

        print(
            f"Detected file type: {file_type}"
        )


        # =================================================
        # 3. CHECK TARGET LANGUAGE
        # =================================================

        tgt_lang = LANGUAGE_MAP.get(
            target_language.lower()
        )

        if not tgt_lang:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported target language: "
                    f"{target_language}"
                )
            )

        print(
            f"Selected target language: "
            f"{target_language}"
        )

        print(
            f"C-DAC target language code: "
            f"{tgt_lang}"
        )


        # =================================================
        # 4. DOCX PROCESSING
        # =================================================

        if file_type == "DOCX":

            # ---------------------------------------------
            # Open DOCX
            # ---------------------------------------------

            print(
                "Opening DOCX document..."
            )

            document = Document(
                file_path
            )


            # ---------------------------------------------
            # Extract document
            # ---------------------------------------------

            print(
                "Calling parse_document()..."
            )

            result = parse_document(
                file_path,
                document
            )

            print(
                "Document parsed successfully!"
            )


            # =================================================
            # 5. SAVE EXTRACTED JSON
            # =================================================

            base_name = os.path.splitext(
                file.filename
            )[0]

            json_filename = (
                f"{base_name}.json"
            )

            json_path = os.path.join(
                OUTPUT_FOLDER,
                json_filename
            )

            with open(
                json_path,
                "w",
                encoding="utf-8"
            ) as json_file:

                json.dump(
                    result,
                    json_file,
                    indent=4,
                    ensure_ascii=False
                )

            print(
                f"JSON saved: {json_path}"
            )


            # =================================================
            # 6. TRANSLATION
            # =================================================

            print(
                "Starting translation..."
            )

            translation_cache = {}
            translation_texts = collect_translation_texts(result)

            with ThreadPoolExecutor(max_workers=4) as executor:
                translated_texts = executor.map(
                    lambda text: translate_text(
                        text,
                        "eng-latn",
                        tgt_lang
                    ),
                    translation_texts
                )

            translation_cache.update(
                zip(translation_texts, translated_texts)
            )

            translated_result = translate_json(
                result,
                src_lang="eng-latn",
                tgt_lang=tgt_lang,
                translation_cache={
                    (text, "eng-latn", tgt_lang): translated
                    for text, translated in translation_cache.items()
                }
            )

            print(
                "Translation completed!"
            )


            # =================================================
            # 7. SAVE TRANSLATED JSON
            # =================================================

            translated_json_filename = (
                f"{base_name}"
                f"_translated_"
                f"{target_language.lower()}.json"
            )

            translated_json_path = os.path.join(
                OUTPUT_FOLDER,
                translated_json_filename
            )

            with open(
                translated_json_path,
                "w",
                encoding="utf-8"
            ) as json_file:

                json.dump(
                    translated_result,
                    json_file,
                    indent=4,
                    ensure_ascii=False
                )

            print(
                "Translated JSON saved:"
            )

            print(
                translated_json_path
            )


            # =================================================
            # 8. RECONSTRUCTION
            # =================================================

            print(
                "Starting document reconstruction..."
            )

            reconstructed_docx_filename = (
                f"{base_name}"
                f"_reconstructed_"
                f"{target_language.lower()}.docx"
            )

            reconstructed_docx_path = os.path.join(
                OUTPUT_FOLDER,
                reconstructed_docx_filename
            )


            reconstruct_docx(
                file_path,
                translated_json_path,
                reconstructed_docx_path
            )


            print(
                "Document reconstruction completed!"
            )

            print(
                "Reconstructed DOCX saved:"
            )

            print(
                reconstructed_docx_path
            )


            # =================================================
            # 9. RETURN RESPONSE
            # =================================================

            return {

                "message":
                    "File uploaded, extracted, "
                    "translated and reconstructed successfully",

                "filename":
                    file.filename,

                "file_type":
                    file_type,

                "target_language":
                    target_language,

                "target_language_code":
                    tgt_lang,

                "json_file":
                    json_filename,

                "translated_json_file":
                    translated_json_filename,

                "reconstructed_docx_file":
                    reconstructed_docx_filename,

                "data":
                    result,

                "translated_data":
                    translated_result
            }


        # =================================================
        # 10. OTHER FILE TYPES
        # =================================================

        return {

            "message":
                f"{file_type} upload successful. "
                "Extraction/reconstruction is not "
                "implemented yet.",

            "filename":
                file.filename,

            "file_type":
                file_type,

            "target_language":
                target_language
        }


    # =====================================================
    # HTTP EXCEPTION
    # =====================================================

    except HTTPException:

        raise


    # =====================================================
    # GENERAL EXCEPTION
    # =====================================================

    except Exception as e:

        print(
            "\n========== ERROR =========="
        )

        traceback.print_exc()

        print(
            "===========================\n"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )