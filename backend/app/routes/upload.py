import os
import json
import copy
import traceback
import requests
import time
import re
import hashlib
import threading
import unicodedata

from sqlalchemy import text as sql_text

from concurrent.futures import ThreadPoolExecutor

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Form
)

from docx import Document

from app.utils.doc_converter import (
    convert_doc_to_docx,
    convert_docx_to_doc
)

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

# =========================================================
# XLSX IMPORT
# =========================================================

from app.services.xlsx_service import process_xlsx_pipeline

from app.utils.xls_converter import (
    convert_xls_to_xlsx,
    convert_xlsx_to_xls
)

# =========================================================
# PDF IMPORT
# =========================================================

from app.services.pdf_service import process_pdf_pipeline


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
    ".doc": "DOC",
    ".docx": "DOCX",
    ".pptx": "PPTX",
    ".xls": "XLS",
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
# TRANSLATION MEMORY (POSTGRESQL)
# =========================================================

_translation_memory_initialized = False
_translation_memory_lock = threading.Lock()


def _translation_hash(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def _ensure_translation_memory_table():
    """
    Create translation_memory once,
    without storing complete documents.
    """

    global _translation_memory_initialized

    if _translation_memory_initialized:
        return

    with _translation_memory_lock:

        if _translation_memory_initialized:
            return

        db = SessionLocal()

        try:

            db.execute(
                sql_text(
                    """
                    CREATE TABLE IF NOT EXISTS translation_memory (
                        id SERIAL PRIMARY KEY,
                        text_hash VARCHAR(64) NOT NULL,
                        source_text TEXT NOT NULL,
                        source_language VARCHAR(32) NOT NULL,
                        target_language VARCHAR(32) NOT NULL,
                        translated_text TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (
                            text_hash,
                            source_language,
                            target_language
                        )
                    )
                    """
                )
            )

            db.commit()

            _translation_memory_initialized = True

            print(
                "[DB] translation_memory table is ready."
            )

        except Exception:

            db.rollback()

            print(
                "[DB] Could not initialize "
                "translation_memory. "
                "API will still be used."
            )

            traceback.print_exc()

        finally:

            db.close()


def get_cached_translation(
    source_text,
    src_lang,
    tgt_lang
):
    """
    Fetch only the translated text
    from PostgreSQL.
    """

    _ensure_translation_memory_table()

    db = SessionLocal()

    try:

        return db.execute(
            sql_text(
                """
                SELECT translated_text
                FROM translation_memory
                WHERE text_hash = :text_hash
                  AND source_language = :source_language
                  AND target_language = :target_language
                LIMIT 1
                """
            ),
            {
                "text_hash":
                    _translation_hash(source_text),

                "source_language":
                    src_lang,

                "target_language":
                    tgt_lang
            }
        ).scalar_one_or_none()

    except Exception:

        db.rollback()

        print(
            "[DB LOOKUP FAILED] "
            "Falling back to translation API."
        )

        traceback.print_exc()

        return None

    finally:

        db.close()


def save_translation(
    source_text,
    src_lang,
    tgt_lang,
    translated_text
):
    """
    Store only a reusable
    text/translation pair.
    """

    if not source_text or not source_text.strip():
        return

    _ensure_translation_memory_table()

    db = SessionLocal()

    try:

        db.execute(
            sql_text(
                """
                INSERT INTO translation_memory
                    (
                        text_hash,
                        source_text,
                        source_language,
                        target_language,
                        translated_text
                    )
                VALUES
                    (
                        :text_hash,
                        :source_text,
                        :source_language,
                        :target_language,
                        :translated_text
                    )
                ON CONFLICT (
                    text_hash,
                    source_language,
                    target_language
                )
                DO UPDATE SET
                    translated_text =
                        EXCLUDED.translated_text
                """
            ),
            {
                "text_hash":
                    _translation_hash(source_text),

                "source_text":
                    source_text,

                "source_language":
                    src_lang,

                "target_language":
                    tgt_lang,

                "translated_text":
                    translated_text
            }
        )

        db.commit()

        print(
            "[DB SAVE] Translation saved to PostgreSQL."
        )

    except Exception:

        db.rollback()

        print(
            "[DB SAVE FAILED] "
            "Continuing with in-memory translation."
        )

        traceback.print_exc()

    finally:

        db.close()


# =========================================================
# TRANSLATE ONE TEXT
# =========================================================

def _is_usable_translation(
    translated_text,
):
    if not isinstance(translated_text, str) or not translated_text.strip():
        return False

    normalized = " ".join(translated_text.split())

    if "<unk>" in normalized.casefold():
        return False
    if "@" in normalized and re.search(r"@(?=\s|$|@)", normalized):
        return False

    return True


def _translation_memory_source_key(source_language, use_english_pivot):
    if use_english_pivot:
        return f"{source_language}:via-eng"
    return source_language


def _translate_from_english_pivot(english_text, source_text, src_lang, tgt_lang):
    translated_text = _request_translation(
        english_text,
        "eng-latn",
        tgt_lang
    )
    if _is_usable_translation(translated_text):
        return translated_text

    clauses = re.split(r"(?<=[,;:.!?])\s+", english_text.strip())
    if len(clauses) > 1:
        translated_clauses = [
            _request_translation(clause, "eng-latn", tgt_lang)
            for clause in clauses
            if clause.strip()
        ]
        if all(
            _is_usable_translation(clause)
            for clause in translated_clauses
        ):
            return " ".join(translated_clauses)

    direct_translation = _request_translation(
        source_text,
        src_lang,
        tgt_lang
    )
    if (
        _is_usable_translation(direct_translation)
        and " ".join(direct_translation.split()).casefold()
        != " ".join(source_text.split()).casefold()
    ):
        return direct_translation

    raise RuntimeError(
        f"Translation API returned malformed output for "
        f"{src_lang} to {tgt_lang}."
    )


def _request_translation(text, src_lang, tgt_lang):
    payload = {
        "ip_text": text,
        "srcLang": src_lang,
        "tgtLang": tgt_lang,
        "delimiter": "",
        "nSuggestions": "1"
    }

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
            print("[API RESPONSE]:", ascii(response_json))

            output = response_json.get("Output")
            if isinstance(output, str) and output.strip():
                return output.strip()

            print("API returned empty Output.")

        except Exception as error:
            print(f"Translation attempt {attempt + 1}/3 failed:")
            print(str(error))

            if attempt < 2:
                time.sleep(2 ** attempt)

    raise RuntimeError(
        f"Translation API failed for {src_lang} to {tgt_lang}."
    )


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
    # Handle tabs
    # -----------------------------------------------------

    if "\t" in text:

        return "\t".join(
            translate_text(
                segment,
                src_lang,
                tgt_lang
            )
            if segment.strip()
            else segment
            for segment in text.split("\t")
        )

    # -----------------------------------------------------
    # Preserve dotted abbreviations
    # -----------------------------------------------------

    if re.fullmatch(
        r"[A-Za-z](?:\.[A-Za-z])+\.?",
        text.strip()
    ):
        return text

    if src_lang == tgt_lang:
        return text

    use_english_pivot = (
        src_lang != "eng-latn"
        and tgt_lang != "eng-latn"
    )
    translation_memory_source = _translation_memory_source_key(
        src_lang,
        use_english_pivot
    )

    # -----------------------------------------------------
    # PostgreSQL translation-memory lookup
    # -----------------------------------------------------

    cached_translation = get_cached_translation(
        text,
        translation_memory_source,
        tgt_lang
    )

    if cached_translation is not None:
        if (
            not _is_usable_translation(
                cached_translation,
            )
        ):
            print(
                "[DB HIT] Ignoring stale or malformed translation."
            )
        else:
            print(
                "[DB HIT] "
                "Using cached translation; "
                "API call skipped."
            )

            return cached_translation

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

    def is_word_character(character):
        category = unicodedata.category(character)
        return (
            character == "_"
            or character.isalnum()
            or category.startswith("M")
        )

    first_word_character = next(
        (
            index
            for index, character in enumerate(text)
            if is_word_character(character)
        ),
        None
    )

    if first_word_character is None:

        return text

    last_word_character = next(
        index
        for index in range(len(text) - 1, first_word_character - 1, -1)
        if is_word_character(text[index])
    )

    leading_chars = text[:first_word_character]
    core_text = text[first_word_character:last_word_character + 1]
    trailing_chars = text[last_word_character + 1:]

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
        ascii(core_text)
    )

    # -----------------------------------------------------
    # Translate through English because the direct Hindi-to-Marathi
    # endpoint currently returns Hindi unchanged or malformed output.
    # -----------------------------------------------------

    translated_core = core_text

    try:
        if use_english_pivot:
            english_text = _request_translation(
                core_text,
                src_lang,
                "eng-latn"
            )
            if not _is_usable_translation(
                english_text,
            ):
                raise RuntimeError(
                    f"Translation API returned an invalid English "
                    f"pivot for {src_lang} to {tgt_lang}."
                )

            translated_core = _translate_from_english_pivot(
                english_text,
                core_text,
                src_lang,
                tgt_lang
            )
        else:
            translated_core = _request_translation(
                core_text,
                src_lang,
                tgt_lang
            )
            if not _is_usable_translation(
                translated_core,
            ):
                raise RuntimeError(
                    f"Translation API returned an invalid result "
                    f"for {src_lang} to {tgt_lang}."
                )
    except Exception as exc:
        print(
            "[TRANSLATION FALLBACK] "
            f"{src_lang} -> {tgt_lang} failed for "
            f"{ascii(core_text[:80])}; returning original text. "
            f"Error: {exc}"
        )
        return text

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

    terminal_punctuation = (".", "!", "?", "।", "۔", "؟")
    translated_has_terminal_punctuation = translated_core.rstrip().endswith(
        terminal_punctuation
    )

    punctuation_map = {
        "eng-latn": {"।": ".", "۔": ".", "؟": "?"},
        "hin-deva": {"۔": "।", "؟": "?"},
        "mar-deva": {"۔": "।", "؟": "?"},
        "urd-arab": {"।": "۔", "?": "؟"},
    }
    for source_mark, target_mark in punctuation_map.get(
        tgt_lang,
        {}
    ).items():
        trailing_chars = trailing_chars.replace(
            source_mark,
            target_mark
        )

    if (
        translated_has_terminal_punctuation
        and trailing_chars.rstrip().endswith(terminal_punctuation)
    ):
        trailing_chars = re.sub(
            r"[.,!?।؟]+(?=\s*$)",
            "",
            trailing_chars
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
        ascii(text),
        "->",
        ascii(final_text)
    )

    # -----------------------------------------------------
    # Store translation
    # -----------------------------------------------------

    save_translation(
        text,
        translation_memory_source,
        tgt_lang,
        final_text
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

        # =================================================
        # IMAGE OCR TEXT
        # =================================================

        if data.get("type") == "image_text":

            original_text = data.get(
                "text",
                ""
            )

            if (
                isinstance(
                    original_text,
                    str
                )
                and original_text.strip()
            ):

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

                data["translated_text"] = (
                    translation_cache[
                        cache_key
                    ]
                )

            ocr_details = data.get(
                "ocr_details",
                []
            )

            if isinstance(
                ocr_details,
                list
            ):

                for item in ocr_details:

                    if not isinstance(
                        item,
                        dict
                    ):
                        continue

                    original_ocr_text = item.get(
                        "text",
                        ""
                    )

                    if (
                        not isinstance(
                            original_ocr_text,
                            str
                        )
                        or not original_ocr_text.strip()
                    ):
                        continue

                    cache_key = (
                        original_ocr_text,
                        src_lang,
                        tgt_lang
                    )

                    if cache_key not in translation_cache:

                        translation_cache[
                            cache_key
                        ] = translate_text(
                            original_ocr_text,
                            src_lang,
                            tgt_lang
                        )

                    item["translated_text"] = (
                        translation_cache[
                            cache_key
                        ]
                    )

            # Avoid translating image OCR
            # fields twice.

            for key in list(data.keys()):

                if key in [
                    "text",
                    "translated_text",
                    "ocr_details"
                ]:
                    continue

                data[key] = translate_json(
                    data[key],
                    src_lang,
                    tgt_lang,
                    translation_cache
                )

            return data

        # =================================================
        # Translate main "text" field
        # =================================================

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

        # =================================================
        # Translate runs
        # =================================================

        if (
            "runs" in data
            and isinstance(
                data["runs"],
                list
            )
            and data.get("type") not in {
                "paragraph",
                "heading",
                "list_item"
            }
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

        # =================================================
        # Translate textbox paragraphs
        # =================================================

        if (
            data.get("type") == "textbox"
            and isinstance(
                data.get("paragraphs"),
                list
            )
        ):

            translated_paragraphs = []

            for paragraph_text in data["paragraphs"]:

                if not isinstance(
                    paragraph_text,
                    str
                ):

                    translated_paragraphs.append(
                        paragraph_text
                    )

                    continue

                if not paragraph_text.strip():

                    translated_paragraphs.append(
                        paragraph_text
                    )

                    continue

                cache_key = (
                    paragraph_text,
                    src_lang,
                    tgt_lang
                )

                if cache_key not in translation_cache:

                    translation_cache[
                        cache_key
                    ] = translate_text(
                        paragraph_text,
                        src_lang,
                        tgt_lang
                    )

                translated_paragraphs.append(
                    translation_cache[
                        cache_key
                    ]
                )

            data["paragraphs"] = (
                translated_paragraphs
            )

        # =================================================
        # Recursively process other fields
        # =================================================

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

    # =====================================================
    # DICTIONARY
    # =====================================================

    if isinstance(data, dict):

        # -------------------------------------------------
        # Collect textbox paragraph text
        # -------------------------------------------------

        if (
            data.get("type") == "textbox"
            and isinstance(
                data.get("paragraphs"),
                list
            )
        ):

            for paragraph_text in data["paragraphs"]:

                if (
                    isinstance(
                        paragraph_text,
                        str
                    )
                    and paragraph_text.strip()
                ):

                    texts.add(
                        paragraph_text.strip()
                    )

        # -------------------------------------------------
        # Collect normal text
        # -------------------------------------------------

        text = data.get("text")

        if (
            isinstance(
                text,
                str
            )
            and text.strip()
        ):

            texts.add(
                text.strip()
            )

        # -------------------------------------------------
        # Recursively collect other fields
        # -------------------------------------------------

        for key, value in data.items():

            if key in [
                "text",
                "runs",
                "original_text",
                "paragraphs"
            ]:
                continue

            collect_translation_texts(
                value,
                texts
            )

    # =====================================================
    # LIST
    # =====================================================

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
    source_language: str = Form("en"),
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

        if file_type in [
            "DOC",
            "DOCX"
        ]:

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
        # 3. CHECK SOURCE AND TARGET LANGUAGES
        # =================================================

        source_language = (
            source_language.lower().strip()
        )
        target_language = (
            target_language.lower().strip()
        )

        src_lang = LANGUAGE_MAP.get(
            source_language
        )
        tgt_lang = LANGUAGE_MAP.get(
            target_language
        )

        if not src_lang:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported source language: "
                    f"{source_language}"
                )
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
            f"Selected source language: "
            f"{source_language}"
        )

        print(
            f"C-DAC source language code: "
            f"{src_lang}"
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
                source_language=source_language,
                target_language=target_language,
                status="uploaded"
            )

            db.add(db_document)

            db.commit()

            db.refresh(db_document)

            document_id = db_document.id

            print(
                "\nDocument saved in PostgreSQL."
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

        if file_type in [
            "DOC",
            "DOCX"
        ]:

            # ---------------------------------------------
            # Convert legacy DOC to DOCX
            # ---------------------------------------------

            if file_type == "DOC":

                print(
                    "\nConverting DOC to DOCX..."
                )

                file_path = convert_doc_to_docx(
                    file_path,
                    UPLOAD_FOLDER
                )

                print(
                    f"DOC converted successfully: "
                    f"{file_path}"
                )

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

            # ---------------------------------------------
            # UPDATE STATUS: EXTRACTED
            # ---------------------------------------------

            update_document_status(
                document_id,
                "extracted"
            )

            # ---------------------------------------------
            # DEBUG: CHECK HEADING EXTRACTION
            # ---------------------------------------------

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

            # ---------------------------------------------
            # SAVE EXTRACTED JSON
            # ---------------------------------------------

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

            # ---------------------------------------------
            # TRANSLATION
            # ---------------------------------------------

            print(
                "\n========== TRANSLATION =========="
            )

            print(
                "Starting translation..."
            )

            translation_cache = {}

            translation_texts = (
                collect_translation_texts(
                    result
                )
            )

            print(
                f"Unique texts to translate: "
                f"{len(translation_texts)}"
            )

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

            # ---------------------------------------------
            # Translate unique texts concurrently
            # ---------------------------------------------

            with ThreadPoolExecutor(
                max_workers=4
            ) as executor:

                translated_texts = list(
                    executor.map(
                        lambda text:
                            translate_text(
                                text,
                                src_lang,
                                tgt_lang
                            ),
                        translation_texts
                    )
                )

            # ---------------------------------------------
            # Build cache
            # ---------------------------------------------

            for original, translated in zip(
                translation_texts,
                translated_texts
            ):

                cache_key = (
                    original,
                    src_lang,
                    tgt_lang
                )

                translation_cache[
                    cache_key
                ] = translated

            # ---------------------------------------------
            # Apply translations recursively
            # ---------------------------------------------

            translated_result = translate_json(
                copy.deepcopy(result),
                src_lang=src_lang,
                tgt_lang=tgt_lang,
                translation_cache=translation_cache
            )

            print(
                "\nTranslation completed!"
            )

            # ---------------------------------------------
            # UPDATE STATUS: TRANSLATED
            # ---------------------------------------------

            update_document_status(
                document_id,
                "translated"
            )

            # ---------------------------------------------
            # DEBUG: CHECK TRANSLATED HEADING
            # ---------------------------------------------

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

            # ---------------------------------------------
            # SAVE TRANSLATED JSON
            # ---------------------------------------------

            translated_json_filename = (
                f"{base_name}"
                f"_translated_"
                f"{source_language}_to_"
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

            # ---------------------------------------------
            # RECONSTRUCTION
            # ---------------------------------------------

            print(
                "\n========== RECONSTRUCTION =========="
            )

            print(
                "Starting document reconstruction..."
            )

            reconstructed_docx_filename = (
                f"{base_name}"
                f"_reconstructed_"
                f"{source_language}_to_"
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

            # ---------------------------------------------
            # CONVERT BACK TO DOC
            # ---------------------------------------------

            if file_type == "DOC":

                print(
                    "\nConverting reconstructed DOCX "
                    "back to DOC..."
                )

                final_file_path = convert_docx_to_doc(
                    reconstructed_docx_path,
                    OUTPUT_FOLDER
                )

                final_filename = os.path.basename(
                    final_file_path
                )

            else:

                final_file_path = (
                    reconstructed_docx_path
                )

                final_filename = (
                    reconstructed_docx_filename
                )

            # ---------------------------------------------
            # UPDATE STATUS: COMPLETED
            # ---------------------------------------------

            update_document_status(
                document_id,
                "completed",
                final_filename
            )

            # ---------------------------------------------
            # RETURN RESPONSE
            # ---------------------------------------------

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

                "source_language":
                    source_language,

                "target_language_code":
                    tgt_lang,

                "status":
                    "completed",

                "json_file":
                    json_filename,

                "translated_json_file":
                    translated_json_filename,

                "reconstructed_docx_file":
                    final_filename,

                "data":
                    result,

                "translated_data":
                    translated_result
            }

        # =================================================
        # 7. PPTX PROCESSING
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
                translate_func=translate_text,
                source_language=src_lang,
                source_language_name=source_language
            )

            # ---------------------------------------------
            # UPDATE STATUS: COMPLETED
            # ---------------------------------------------

            output_filename = None

            if isinstance(
                result,
                dict
            ):

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

                "source_language":
                    source_language,

                "target_language_code":
                    tgt_lang,

                "status":
                    "completed",

                **result
            }

        # =================================================
        # 8. XLSX / XLS PROCESSING
        # =================================================

        elif file_type in [
            "XLS",
            "XLSX"
        ]:

            print(
                f"\nProcessing "
                f"{file_type} spreadsheet..."
            )

            pipeline_file_path = file_path
            pipeline_filename = file.filename

            # ---------------------------------------------
            # Convert XLS to XLSX
            # ---------------------------------------------

            if file_type == "XLS":

                print(
                    "Converting XLS to XLSX..."
                )

                conversion_dir = os.path.join(
                    UPLOAD_FOLDER,
                    f"xls_to_xlsx_{document_id}"
                )

                pipeline_file_path = (
                    convert_xls_to_xlsx(
                        file_path,
                        conversion_dir
                    )
                )

                pipeline_filename = (
                    os.path.basename(
                        pipeline_file_path
                    )
                )

            # ---------------------------------------------
            # XLSX PIPELINE
            # ---------------------------------------------

            result = process_xlsx_pipeline(
                file_path=pipeline_file_path,
                filename=pipeline_filename,
                target_language=target_language,
                tgt_lang_code=tgt_lang,
                output_folder=OUTPUT_FOLDER,
                translate_func=translate_text,
                source_language=src_lang,
                source_language_name=source_language
            )

            # ---------------------------------------------
            # Convert reconstructed XLSX back to XLS
            # ---------------------------------------------

            if file_type == "XLS":

                reconstructed_xlsx_filename = (
                    result.get(
                        "reconstructed_file"
                    )
                )

                if not reconstructed_xlsx_filename:

                    raise RuntimeError(
                        "XLSX reconstruction "
                        "did not return "
                        "an output file."
                    )

                reconstructed_xlsx_path = (
                    os.path.join(
                        OUTPUT_FOLDER,
                        reconstructed_xlsx_filename
                    )
                )

                final_file_path = (
                    convert_xlsx_to_xls(
                        reconstructed_xlsx_path,
                        OUTPUT_FOLDER
                    )
                )

                final_filename = (
                    os.path.basename(
                        final_file_path
                    )
                )

                result[
                    "reconstructed_xlsx_file"
                ] = reconstructed_xlsx_filename

                result[
                    "reconstructed_file"
                ] = final_filename

            # ---------------------------------------------
            # UPDATE STATUS: COMPLETED
            # ---------------------------------------------

            output_filename = None

            if isinstance(
                result,
                dict
            ):

                output_filename = (
                    result.get(
                        "reconstructed_file"
                    )
                    or result.get(
                        "output_filename"
                    )
                )

            update_document_status(
                document_id,
                "completed",
                output_filename
            )

            return {

                "message":
                    f"{file_type} file uploaded, "
                    "extracted, translated and "
                    "reconstructed successfully",

                "document_id":
                    document_id,

                "filename":
                    file.filename,

                "file_type":
                    file_type,

                "target_language":
                    target_language,

                "source_language":
                    source_language,

                "target_language_code":
                    tgt_lang,

                "status":
                    "completed",

                **result
            }

        # =================================================
        # 9. PDF PROCESSING
        # =================================================

        elif file_type == "PDF":

            print(
                "\n=========================================="
            )

            print(
                "Processing PDF document..."
            )

            print(
                "PDF detector will identify whether "
                "the PDF is Native or Scanned."
            )

            print(
                "=========================================="
            )

            # ---------------------------------------------
            # PDF PIPELINE
            #
            # The PDF service will handle:
            #
            # 1. PDF type detection
            # 2. Native PDF extraction
            # 3. Scanned PDF extraction
            # 4. Original JSON creation
            # 5. Translation
            # 6. Translated JSON creation
            # 7. PDF reconstruction
            #
            # ---------------------------------------------

            result = process_pdf_pipeline(
                file_path=file_path,
                filename=file.filename,
                target_language=target_language,
                tgt_lang_code=tgt_lang,
                output_folder=OUTPUT_FOLDER,
                translate_func=translate_text,
                source_language=src_lang,
                source_language_name=source_language
            )

            # ---------------------------------------------
            # GET RECONSTRUCTED PDF FILE
            # ---------------------------------------------

            output_filename = None

            if isinstance(
                result,
                dict
            ):

                output_filename = (
                    result.get(
                        "reconstructed_pdf_file"
                    )
                    or result.get(
                        "reconstructed_file"
                    )
                    or result.get(
                        "output_filename"
                    )
                )

            # ---------------------------------------------
            # UPDATE POSTGRESQL STATUS
            # ---------------------------------------------

            update_document_status(
                document_id,
                "completed",
                output_filename
            )

            # ---------------------------------------------
            # RETURN PDF RESPONSE
            # ---------------------------------------------

            return {

                "message":
                    "PDF file uploaded, extracted, "
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

                "source_language":
                    source_language,

                "target_language_code":
                    tgt_lang,

                "status":
                    "completed",

                **result
            }

        # =================================================
        # 10. OTHER FILE TYPES
        # =================================================

        else:

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

        # Update database if record
        # was already created

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

        # ---------------------------------------------
        # UPDATE DATABASE: FAILED
        # ---------------------------------------------

        if document_id is not None:

            update_document_status(
                document_id,
                "failed"
            )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )