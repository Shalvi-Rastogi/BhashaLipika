import os
import json
import traceback
import requests
import time
import re

from concurrent.futures import ThreadPoolExecutor

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Form
)

from docx import Document

# =========================================================
# POSTGRESQL IMPORTS
# =========================================================

from app.database.database import SessionLocal
from app.database.models import Document as DocumentModel

# =========================================================
# PROJECT IMPORTS
# =========================================================

from app.extractors.Docx.document_parser import parse_document
from app.reconstructors.docx_reconstructor import reconstruct_docx

# =========================================================
# PPTX IMPORT
# =========================================================

from app.services.pptx_service import process_pptx_pipeline


router = APIRouter()


# =========================================================
# FOLDERS
# =========================================================

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

MAX_DOCX_FILE_SIZE = 5 * 1024 * 1024

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


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
# TRANSLATE ONE TEXT
# =========================================================

def translate_text(
    text,
    src_lang="eng-latn",
    tgt_lang="hin-deva"
):
    """
    Translate a single text using C-DAC API.

    Handles:
        - empty text
        - newlines
        - punctuation
        - spaces
        - API retry
    """

    # -----------------------------------------------------
    # Empty / whitespace-only text
    # -----------------------------------------------------

    if not text or not text.strip():
        return text

    # -----------------------------------------------------
    # Preserve dotted abbreviations
    # -----------------------------------------------------

    if re.fullmatch(
        r"[A-Za-z](?:\.[A-Za-z])+\.?",
        text.strip()
    ):
        return text

    # -----------------------------------------------------
    # Handle newlines
    # -----------------------------------------------------

    if "\n" in text:

        lines = text.split("\n")

        translated_lines = []

        for line in lines:

            if line.strip():

                translated_lines.append(
                    translate_text(
                        line,
                        src_lang,
                        tgt_lang
                    )
                )

            else:

                translated_lines.append("")

        return "\n".join(
            translated_lines
        )

    # -----------------------------------------------------
    # Smart punctuation separation
    # -----------------------------------------------------

    match = re.match(
        r'^([^\w]*)(.*?[\w])([^\w]*)$',
        text,
        flags=re.UNICODE
    )

    if match:

        leading_chars = match.group(1)
        core_text = match.group(2)
        trailing_chars = match.group(3)

    else:

        return text

    # -----------------------------------------------------
    # Debug log
    # -----------------------------------------------------

    print(
        "\n[TRANSLATE REQUEST]"
    )

    print(
        "Source:",
        src_lang
    )

    print(
        "Target:",
        tgt_lang
    )

    print(
        "Text:",
        repr(core_text)
    )

    # -----------------------------------------------------
    # API payload
    # -----------------------------------------------------

    payload = {
        "ip_text": core_text,
        "srcLang": src_lang,
        "tgtLang": tgt_lang,
        "delimiter": "",
        "nSuggestions": "1"
    }

    translated_core = core_text

    # -----------------------------------------------------
    # API request with retry
    # -----------------------------------------------------

    for attempt in range(3):

        try:

            response = requests.post(
                TRANSLATION_API_URL,
                json=payload,
                timeout=60,
                verify=False
            )

            response.raise_for_status()

            response_json = response.json()

            print(
                "[API RESPONSE]:",
                response_json
            )

            output = response_json.get(
                "Output"
            )

            if output:

                translated_core = (
                    output.strip()
                )

                break

            else:

                print(
                    "API returned empty Output."
                )

        except Exception as error:

            print(
                f"Translation attempt "
                f"{attempt + 1}/3 failed:"
            )

            print(
                str(error)
            )

            if attempt < 2:

                time.sleep(
                    2 ** attempt
                )

    # -----------------------------------------------------
    # Remove unwanted Devanagari full stop
    # -----------------------------------------------------

    if (
        not core_text.endswith(".")
        and translated_core.endswith("।")
    ):

        translated_core = (
            translated_core
            .rstrip("।")
            .strip()
        )

    # -----------------------------------------------------
    # Restore punctuation / spaces
    # -----------------------------------------------------

    final_text = (
        leading_chars
        + translated_core
        + trailing_chars
    )

    # -----------------------------------------------------
    # Debug log
    # -----------------------------------------------------

    print(
        "[TRANSLATION RESULT]"
    )

    print(
        repr(text),
        "->",
        repr(final_text)
    )

    return final_text


# =========================================================
# TRANSLATE JSON RECURSIVELY
# =========================================================

def translate_json(
    data,
    src_lang="eng-latn",
    tgt_lang="hin-deva",
    translation_cache=None
):
    """
    Recursively translate all text fields
    in extracted document JSON.
    """

    if translation_cache is None:

        translation_cache = {}

    # =====================================================
    # DICTIONARY
    # =====================================================

    if isinstance(data, dict):

        # -------------------------------------------------
        # Translate main "text" field
        # -------------------------------------------------

        if (
            "text" in data
            and isinstance(
                data["text"],
                str
            )
        ):

            original_text = data["text"]

            if original_text.strip():

                cache_key = (
                    original_text,
                    src_lang,
                    tgt_lang
                )

                if cache_key not in translation_cache:

                    translation_cache[
                        cache_key
                    ] = translate_text(
                        original_text,
                        src_lang,
                        tgt_lang
                    )

                data["text"] = (
                    translation_cache[
                        cache_key
                    ]
                )

        # -------------------------------------------------
        # Translate runs
        # -------------------------------------------------

        if (
            "runs" in data
            and isinstance(
                data["runs"],
                list
            )
        ):

            for run in data["runs"]:

                if not isinstance(
                    run,
                    dict
                ):
                    continue

                if (
                    "text" in run
                    and isinstance(
                        run["text"],
                        str
                    )
                ):

                    original_text = (
                        run["text"]
                    )

                    if not original_text.strip():
                        continue

                    cache_key = (
                        original_text,
                        src_lang,
                        tgt_lang
                    )

                    if cache_key not in translation_cache:

                        translation_cache[
                            cache_key
                        ] = translate_text(
                            original_text,
                            src_lang,
                            tgt_lang
                        )

                    run["text"] = (
                        translation_cache[
                            cache_key
                        ]
                    )

        # -------------------------------------------------
        # Recursively process other fields
        # -------------------------------------------------

        for key in list(data.keys()):

            if key in [
                "text",
                "runs",
                "original_text"
            ]:

                continue

            data[key] = translate_json(
                data[key],
                src_lang,
                tgt_lang,
                translation_cache
            )

        return data

    # =====================================================
    # LIST
    # =====================================================

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

    # =====================================================
    # OTHER DATA TYPES
    # =====================================================

    return data


# =========================================================
# COLLECT CANONICAL TEXTS
# =========================================================

def collect_translation_texts(
    data,
    texts=None
):
    """
    Collect canonical text fields
    without structural duplicates.
    """

    if texts is None:

        texts = set()

    if isinstance(data, dict):

        text = data.get("text")

        if (
            isinstance(text, str)
            and text.strip()
        ):

            texts.add(
                text.strip()
            )

        for key, value in data.items():

            if key not in [
                "text",
                "runs",
                "original_text"
            ]:

                collect_translation_texts(
                    value,
                    texts
                )

    elif isinstance(data, list):

        for item in data:

            collect_translation_texts(
                item,
                texts
            )

    return texts


# =========================================================
# DEBUG: FIND PARTICULAR TEXT
# =========================================================

def find_text_in_json(
    data,
    target_text
):
    """
    Debug helper.
    """

    found = False

    if isinstance(data, dict):

        for key, value in data.items():

            if (
                isinstance(value, str)
                and value == target_text
            ):

                print(
                    f"[FOUND] "
                    f"{target_text!r} "
                    f"inside key: {key}"
                )

                found = True

            elif isinstance(
                value,
                (dict, list)
            ):

                if find_text_in_json(
                    value,
                    target_text
                ):

                    found = True

    elif isinstance(data, list):

        for item in data:

            if find_text_in_json(
                item,
                target_text
            ):

                found = True

    return found


# =========================================================
# DATABASE STATUS UPDATE HELPER
# =========================================================

def update_document_status(
    document_id,
    status,
    output_filename=None
):
    """
    Update document processing status
    in PostgreSQL.
    """

    db = SessionLocal()

    try:

        db_document = db.get(
            DocumentModel,
            document_id
        )

        if db_document is None:

            print(
                f"WARNING: Document ID "
                f"{document_id} not found "
                f"in PostgreSQL."
            )

            return

        db_document.status = status

        if output_filename is not None:

            db_document.output_filename = (
                output_filename
            )

        db.commit()

        print(
            f"PostgreSQL updated: "
            f"ID={document_id}, "
            f"status={status}"
        )

    except Exception:

        db.rollback()

        traceback.print_exc()

    finally:

        db.close()


# =========================================================
# UPLOAD API
# =========================================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    target_language: str = Form(...)
):

    document_id = None

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

        file_type = (
            ALLOWED_EXTENSIONS[
                extension
            ]
        )

        # =================================================
        # 2. DOCX FILE SIZE CHECK
        # =================================================

        if file_type == "DOCX":

            file_content = await file.read()

            if len(file_content) > MAX_DOCX_FILE_SIZE:

                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Only files up to 5 MB "
                        "can be handled."
                    )
                )

            await file.seek(0)

        # =================================================
        # 3. CHECK TARGET LANGUAGE
        # =================================================

        target_language = (
            target_language.lower().strip()
        )

        tgt_lang = LANGUAGE_MAP.get(
            target_language
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
        # 4. SAVE DOCUMENT METADATA IN POSTGRESQL
        # =================================================

        db = SessionLocal()

        try:

            db_document = DocumentModel(
                original_filename=file.filename,
                file_type=file_type,
                source_language="en",
                target_language=target_language,
                status="uploaded"
            )

            db.add(db_document)

            db.commit()

            db.refresh(db_document)

            document_id = db_document.id

            print(
                f"\nDocument saved in PostgreSQL."
            )

            print(
                f"Document ID: {document_id}"
            )

        except Exception:

            db.rollback()

            raise

        finally:

            db.close()

        # =================================================
        # 5. SAVE UPLOADED FILE
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
            f"\nFile saved: {file_path}"
        )

        print(
            f"Detected file type: {file_type}"
        )

        # =================================================
        # 6. DOCX PROCESSING
        # =================================================

        if file_type == "DOCX":

            # ---------------------------------------------
            # Open DOCX
            # ---------------------------------------------

            print(
                "\nOpening DOCX document..."
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
            # UPDATE STATUS: EXTRACTED
            # =================================================

            update_document_status(
                document_id,
                "extracted"
            )

            # =================================================
            # DEBUG: CHECK HEADING EXTRACTION
            # =================================================

            print(
                "\n========== HEADING EXTRACTION CHECK =========="
            )

            heading_found = find_text_in_json(
                result,
                "NESTED TABLE SAMPLE DOCUMENT"
            )

            if heading_found:

                print(
                    "Heading was successfully "
                    "extracted into JSON."
                )

            else:

                print(
                    "WARNING: Heading was NOT found "
                    "in extracted JSON."
                )

            print(
                "=============================================="
            )

            # =================================================
            # 7. SAVE EXTRACTED JSON
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
                f"\nJSON saved: {json_path}"
            )

            # =================================================
            # 8. TRANSLATION
            # =================================================

            print(
                "\n========== TRANSLATION =========="
            )

            print(
                "Starting translation..."
            )

            translation_cache = {}

            # -------------------------------------------------
            # Collect unique text
            # -------------------------------------------------

            translation_texts = (
                collect_translation_texts(
                    result
                )
            )

            print(
                f"Unique texts to translate: "
                f"{len(translation_texts)}"
            )

            # -------------------------------------------------
            # Check heading specifically
            # -------------------------------------------------

            heading_text = (
                "NESTED TABLE SAMPLE DOCUMENT"
            )

            if heading_text in translation_texts:

                print(
                    "\n[HEADING FOUND IN "
                    "TRANSLATION QUEUE]"
                )

                print(
                    repr(heading_text)
                )

            else:

                print(
                    "\n[WARNING] Heading is NOT "
                    "present in translation queue:"
                )

                print(
                    repr(heading_text)
                )

            # -------------------------------------------------
            # Translate unique texts concurrently
            # -------------------------------------------------

            with ThreadPoolExecutor(
                max_workers=4
            ) as executor:

                translated_texts = list(
                    executor.map(
                        lambda text:
                            translate_text(
                                text,
                                "eng-latn",
                                tgt_lang
                            ),
                        translation_texts
                    )
                )

            # -------------------------------------------------
            # Build cache
            # -------------------------------------------------

            for original, translated in zip(
                translation_texts,
                translated_texts
            ):

                cache_key = (
                    original,
                    "eng-latn",
                    tgt_lang
                )

                translation_cache[
                    cache_key
                ] = translated

            # -------------------------------------------------
            # Apply translations recursively
            # -------------------------------------------------

            translated_result = translate_json(
                result,
                src_lang="eng-latn",
                tgt_lang=tgt_lang,
                translation_cache=translation_cache
            )

            print(
                "\nTranslation completed!"
            )

            # =================================================
            # UPDATE STATUS: TRANSLATED
            # =================================================

            update_document_status(
                document_id,
                "translated"
            )

            # =================================================
            # DEBUG: CHECK TRANSLATED HEADING
            # =================================================

            print(
                "\n========== TRANSLATED HEADING CHECK =========="
            )

            find_text_in_json(
                translated_result,
                "NESTED TABLE SAMPLE DOCUMENT"
            )

            print(
                "Looking for translated heading..."
            )

            if isinstance(
                translated_result,
                dict
            ):

                elements = (
                    translated_result.get(
                        "elements",
                        []
                    )
                )

                if isinstance(
                    elements,
                    list
                ):

                    for index, element in enumerate(
                        elements[:10]
                    ):

                        if not isinstance(
                            element,
                            dict
                        ):
                            continue

                        element_text = element.get(
                            "text",
                            ""
                        )

                        if element_text:

                            print(
                                f"Element {index}: "
                                f"{element_text!r}"
                            )

            print(
                "=============================================="
            )

            # =================================================
            # 9. SAVE TRANSLATED JSON
            # =================================================

            translated_json_filename = (
                f"{base_name}"
                f"_translated_"
                f"{target_language}.json"
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
                "\nTranslated JSON saved:"
            )

            print(
                translated_json_path
            )

            # =================================================
            # 10. RECONSTRUCTION
            # =================================================

            print(
                "\n========== RECONSTRUCTION =========="
            )

            print(
                "Starting document reconstruction..."
            )

            reconstructed_docx_filename = (
                f"{base_name}"
                f"_reconstructed_"
                f"{target_language}.docx"
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
            # UPDATE STATUS: COMPLETED
            # =================================================

            update_document_status(
                document_id,
                "completed",
                reconstructed_docx_filename
            )

            # =================================================
            # 11. RETURN RESPONSE
            # =================================================

            return {

                "message":
                    "File uploaded, extracted, "
                    "translated and reconstructed "
                    "successfully",

                "document_id":
                    document_id,

                "filename":
                    file.filename,

                "file_type":
                    file_type,

                "target_language":
                    target_language,

                "target_language_code":
                    tgt_lang,

                "status":
                    "completed",

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
        # 12. PPTX PROCESSING
        # =================================================

        elif file_type == "PPTX":

            print(
                "\nProcessing PPTX document..."
            )

            result = process_pptx_pipeline(
                file_path=file_path,
                filename=file.filename,
                target_language=target_language,
                tgt_lang_code=tgt_lang,
                output_folder=OUTPUT_FOLDER,
                translate_func=translate_text
            )

            # =================================================
            # UPDATE STATUS: COMPLETED
            # =================================================

            output_filename = None

            if isinstance(result, dict):

                output_filename = (
                    result.get(
                        "reconstructed_pptx_file"
                    )
                    or result.get(
                        "output_filename"
                    )
                    or result.get(
                        "output_file"
                    )
                )

            update_document_status(
                document_id,
                "completed",
                output_filename
            )

            return {

                "message":
                    "PPTX File uploaded, extracted, "
                    "translated and reconstructed "
                    "successfully",

                "document_id":
                    document_id,

                "filename":
                    file.filename,

                "file_type":
                    file_type,

                "target_language":
                    target_language,

                "target_language_code":
                    tgt_lang,

                "status":
                    "completed",

                **result
            }

        # =================================================
        # 13. OTHER FILE TYPES
        # =================================================

        update_document_status(
            document_id,
            "uploaded"
        )

        return {

            "message":
                f"{file_type} upload successful. "
                "Extraction/reconstruction is not "
                "implemented yet.",

            "document_id":
                document_id,

            "filename":
                file.filename,

            "file_type":
                file_type,

            "target_language":
                target_language,

            "status":
                "uploaded"
        }

    # =====================================================
    # HTTP EXCEPTION
    # =====================================================

    except HTTPException:

        # Update database if record was already created
        if document_id is not None:

            update_document_status(
                document_id,
                "failed"
            )

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

        # -------------------------------------------------
        # UPDATE DATABASE: FAILED
        # -------------------------------------------------

        if document_id is not None:

            update_document_status(
                document_id,
                "failed"
            )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )