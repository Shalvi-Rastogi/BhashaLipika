import os
import json
import traceback
import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from docx import Document

from app.database.database import SessionLocal
from app.database.models import Document as DocumentModel

from app.extractors.Docx.document_parser import parse_document
from app.reconstructors.docx_reconstructor import reconstruct_docx
from app.services.pptx_service import process_pptx_pipeline

from app.utils.doc_converter import (
    convert_doc_to_docx,
    convert_docx_to_doc,
)


router = APIRouter()


# ============================================================
# FOLDERS
# ============================================================

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

MAX_DOCX_FILE_SIZE = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

ALLOWED_EXTENSIONS = {
    ".pdf": "PDF",
    ".doc": "DOC",
    ".docx": "DOCX",
    ".pptx": "PPTX",
    ".xlsx": "XLSX",
    ".rtf": "RTF",
}


# ============================================================
# TRANSLATION API
# ============================================================

TRANSLATION_API_URL = "https://nlpsangraha.ebhasha.in/getTranslation"

LANGUAGE_MAP = {
    "en": "eng-latn",
    "hi": "hin-deva",
    "mr": "mar-deva",
    "ur": "urd-arab",
}


# ============================================================
# TRANSLATE TEXT
# ============================================================

def translate_text(
    text: str,
    source_lang: str,
    target_lang: str
) -> str:

    if not text or not text.strip():
        return text

    original_text = text

    # Preserve leading/trailing whitespace
    leading = text[:len(text) - len(text.lstrip())]
    trailing = text[len(text.rstrip()):]

    core_text = text.strip()

    # Protect dotted abbreviations
    protected = {}

    def protect_dots(match):
        key = f"__DOT_{len(protected)}__"
        protected[key] = match.group(0)
        return key

    core_text = re.sub(
        r"\b(?:[A-Za-z]\.){2,}",
        protect_dots,
        core_text
    )

    source_code = LANGUAGE_MAP.get(source_lang, source_lang)
    target_code = LANGUAGE_MAP.get(target_lang, target_lang)

    payload = {
        "SourceLanguage": source_code,
        "TargetLanguage": target_code,
        "Input": core_text,
    }

    max_retries = 3

    for attempt in range(max_retries):

        try:

            response = requests.post(
                TRANSLATION_API_URL,
                json=payload,
                timeout=60,
                verify=False
            )

            response.raise_for_status()

            result = response.json()

            translated = result.get("Output", core_text)

            if translated is None:
                translated = core_text

            translated = str(translated)

            # Restore abbreviations
            for key, value in protected.items():
                translated = translated.replace(key, value)

            # Avoid unwanted danda if original didn't end with period
            if (
                translated.endswith("।")
                and not core_text.endswith(".")
                and not core_text.endswith("।")
            ):
                translated = translated[:-1]

            return leading + translated + trailing

        except Exception as e:

            print(
                f"Translation attempt {attempt + 1}/{max_retries} failed: {e}"
            )

            if attempt < max_retries - 1:
                time.sleep(2)

    # If translation fails, return original text
    print("Translation failed. Returning original text.")

    return original_text


# ============================================================
# TRANSLATE JSON
# ============================================================

def translate_json(
    obj,
    source_lang: str,
    target_lang: str,
    translation_cache: dict
):

    if isinstance(obj, dict):

        # ----------------------------------------------------
        # IMAGE OCR TEXT
        # ----------------------------------------------------

        if obj.get("type") == "image_text":

            original_text = obj.get("text", "")

            if original_text and original_text.strip():

                if original_text not in translation_cache:
                    translation_cache[original_text] = translate_text(
                        original_text,
                        source_lang,
                        target_lang
                    )

                obj["translated_text"] = translation_cache[
                    original_text
                ]

            # Translate OCR regions
            regions = obj.get("regions", [])

            for region in regions:

                if isinstance(region, dict):

                    region_text = region.get("text", "")

                    if region_text and region_text.strip():

                        if region_text not in translation_cache:
                            translation_cache[region_text] = translate_text(
                                region_text,
                                source_lang,
                                target_lang
                            )

                        region["translated_text"] = translation_cache[
                            region_text
                        ]

            return obj

        # ----------------------------------------------------
        # NORMAL TEXT
        # ----------------------------------------------------

        if "text" in obj and isinstance(obj["text"], str):

            original_text = obj["text"]

            if original_text.strip():

                if original_text not in translation_cache:
                    translation_cache[original_text] = translate_text(
                        original_text,
                        source_lang,
                        target_lang
                    )

                obj["translated_text"] = translation_cache[
                    original_text
                ]

        # ----------------------------------------------------
        # RUNS
        # ----------------------------------------------------

        if "runs" in obj and isinstance(obj["runs"], list):

            for run in obj["runs"]:

                if isinstance(run, dict):

                    run_text = run.get("text", "")

                    if run_text and run_text.strip():

                        if run_text not in translation_cache:
                            translation_cache[run_text] = translate_text(
                                run_text,
                                source_lang,
                                target_lang
                            )

                        run["translated_text"] = translation_cache[
                            run_text
                        ]

        # ----------------------------------------------------
        # RECURSIVE PROCESSING
        # ----------------------------------------------------

        for key, value in obj.items():

            if key in {
                "text",
                "translated_text",
                "runs",
                "regions"
            }:
                continue

            if isinstance(value, (dict, list)):

                obj[key] = translate_json(
                    value,
                    source_lang,
                    target_lang,
                    translation_cache
                )

        return obj

    # ========================================================
    # LIST
    # ========================================================

    elif isinstance(obj, list):

        return [
            translate_json(
                item,
                source_lang,
                target_lang,
                translation_cache
            )
            for item in obj
        ]

    return obj


# ============================================================
# COLLECT TEXTS
# ============================================================

def collect_translation_texts(obj, texts=None):

    if texts is None:
        texts = set()

    if isinstance(obj, dict):

        if "text" in obj and isinstance(obj["text"], str):

            text = obj["text"].strip()

            if text:
                texts.add(text)

        if "runs" in obj and isinstance(obj["runs"], list):

            for run in obj["runs"]:

                if isinstance(run, dict):

                    text = run.get("text", "")

                    if isinstance(text, str) and text.strip():
                        texts.add(text.strip())

        for value in obj.values():

            if isinstance(value, (dict, list)):
                collect_translation_texts(value, texts)

    elif isinstance(obj, list):

        for item in obj:
            collect_translation_texts(item, texts)

    return texts


# ============================================================
# DEBUG HELPER
# ============================================================

def find_text_in_json(obj, target):

    if isinstance(obj, dict):

        if obj.get("text") == target:
            return obj

        for value in obj.values():

            result = find_text_in_json(value, target)

            if result:
                return result

    elif isinstance(obj, list):

        for item in obj:

            result = find_text_in_json(item, target)

            if result:
                return result

    return None


# ============================================================
# UPDATE DATABASE STATUS
# ============================================================

def update_document_status(
    document_id,
    status,
    output_filename=None
):

    if document_id is None:
        return

    db = SessionLocal()

    try:

        document = db.query(DocumentModel).filter(
            DocumentModel.id == document_id
        ).first()

        if document:

            document.status = status

            if output_filename is not None:
                document.output_filename = output_filename

            db.commit()

            print(
                f"Database updated: "
                f"ID={document_id}, "
                f"status={status}"
            )

    except Exception as e:

        db.rollback()

        print(
            f"Database status update failed: {e}"
        )

    finally:

        db.close()


# ============================================================
# UPLOAD ROUTE
# ============================================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    target_language: str = Form(...)
):

    document_id = None

    try:

        # ====================================================
        # 1. VALIDATE FILE
        # ====================================================

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )

        original_filename = file.filename

        extension = os.path.splitext(
            original_filename
        )[1].lower()

        if extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file type: {extension}. "
                    f"Allowed types: "
                    f"{', '.join(ALLOWED_EXTENSIONS.keys())}"
                )
            )

        file_type = ALLOWED_EXTENSIONS[extension]

        # ====================================================
        # 2. VALIDATE TARGET LANGUAGE
        # ====================================================

        if target_language not in LANGUAGE_MAP:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported target language: "
                    f"{target_language}. "
                    f"Supported languages: "
                    f"{', '.join(LANGUAGE_MAP.keys())}"
                )
            )

        # ====================================================
        # 3. CREATE DATABASE RECORD
        # ====================================================

        db = SessionLocal()

        try:

            db_document = DocumentModel(
                original_filename=original_filename,
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
                f"PostgreSQL record created: "
                f"ID={document_id}"
            )

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

        # ====================================================
        # 4. SAVE UPLOADED FILE
        # ====================================================

        input_path = os.path.join(
            UPLOAD_FOLDER,
            original_filename
        )

        with open(input_path, "wb") as buffer:

            while True:

                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                buffer.write(chunk)

        # ====================================================
        # 5. FILE SIZE VALIDATION
        # ====================================================

        if extension in [".doc", ".docx"]:

            file_size = os.path.getsize(input_path)

            if file_size > MAX_DOCX_FILE_SIZE:

                update_document_status(
                    document_id,
                    "failed"
                )

                raise HTTPException(
                    status_code=400,
                    detail="DOC/DOCX file size exceeds 5 MB"
                )

        # ====================================================
        # 6. DOC / DOCX PIPELINE
        # ====================================================

        if extension in [".doc", ".docx"]:

            # ------------------------------------------------
            # Convert DOC → DOCX if required
            # ------------------------------------------------

            if extension == ".doc":

                working_docx_path = convert_doc_to_docx(
                    input_path
                )

            else:

                working_docx_path = input_path

            # ------------------------------------------------
            # Parse document
            # ------------------------------------------------

            document = Document(
                working_docx_path
            )

            extracted_json = parse_document(
                document
            )

            # ------------------------------------------------
            # Save extracted JSON
            # ------------------------------------------------

            base_name = os.path.splitext(
                original_filename
            )[0]

            extracted_json_filename = (
                f"{base_name}_extracted.json"
            )

            extracted_json_path = os.path.join(
                OUTPUT_FOLDER,
                extracted_json_filename
            )

            with open(
                extracted_json_path,
                "w",
                encoding="utf-8"
            ) as json_file:

                json.dump(
                    extracted_json,
                    json_file,
                    ensure_ascii=False,
                    indent=2
                )

            print(
                f"Extraction completed: "
                f"{extracted_json_filename}"
            )

            # ------------------------------------------------
            # Collect unique texts
            # ------------------------------------------------

            texts = collect_translation_texts(
                extracted_json
            )

            print(
                f"Unique texts to translate: "
                f"{len(texts)}"
            )

            # ------------------------------------------------
            # Translate texts concurrently
            # ------------------------------------------------

            translation_cache = {}

            with ThreadPoolExecutor(
                max_workers=4
            ) as executor:

                results = executor.map(
                    lambda text: (
                        text,
                        translate_text(
                            text,
                            "en",
                            target_language
                        )
                    ),
                    texts
                )

                for original_text, translated_text in results:

                    translation_cache[
                        original_text
                    ] = translated_text

            print(
                "Translation completed"
            )

            # ------------------------------------------------
            # Apply translations to JSON
            # ------------------------------------------------

            translated_json = translate_json(
                extracted_json,
                "en",
                target_language,
                translation_cache
            )

            # ------------------------------------------------
            # Save translated JSON
            # ------------------------------------------------

            translated_json_filename = (
                f"{base_name}_translated_{target_language}.json"
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
                    translated_json,
                    json_file,
                    ensure_ascii=False,
                    indent=2
                )

            print(
                f"Translated JSON saved: "
                f"{translated_json_filename}"
            )

            # ------------------------------------------------
            # Reconstruction
            # ------------------------------------------------

            reconstructed_docx_filename = (
                f"{base_name}_reconstructed_{target_language}.docx"
            )

            reconstructed_docx_path = os.path.join(
                OUTPUT_FOLDER,
                reconstructed_docx_filename
            )

            reconstruct_docx(
                working_docx_path,
                translated_json,
                reconstructed_docx_path
            )

            print(
                f"Reconstruction completed: "
                f"{reconstructed_docx_filename}"
            )

            # ------------------------------------------------
            # Convert DOCX → DOC if original was DOC
            # ------------------------------------------------

            if extension == ".doc":

                final_filename = (
                    f"{base_name}_reconstructed_"
                    f"{target_language}.doc"
                )

                final_path = os.path.join(
                    OUTPUT_FOLDER,
                    final_filename
                )

                convert_docx_to_doc(
                    reconstructed_docx_path,
                    final_path
                )

            else:

                final_filename = reconstructed_docx_filename

            # ------------------------------------------------
            # Update database
            # ------------------------------------------------

            update_document_status(
                document_id,
                "completed",
                final_filename
            )

            # ------------------------------------------------
            # Response
            # ------------------------------------------------

            return {
                "message": "Document processed successfully",
                "document_id": document_id,
                "original_filename": original_filename,
                "target_language": target_language,
                "extracted_json": extracted_json_filename,
                "translated_json": translated_json_filename,
                "output_file": final_filename
            }

        # ====================================================
        # 7. PPTX PIPELINE
        # ====================================================

        elif extension == ".pptx":

            result = process_pptx_pipeline(
                input_path,
                target_language
            )

            output_filename = None

            if isinstance(result, dict):

                output_filename = result.get(
                    "output_file"
                )

            if output_filename:

                update_document_status(
                    document_id,
                    "completed",
                    output_filename
                )

            else:

                update_document_status(
                    document_id,
                    "completed"
                )

            return {
                "message": "PPTX processed successfully",
                "document_id": document_id,
                "result": result
            }

        # ====================================================
        # 8. OTHER FILE TYPES
        # ====================================================

        else:

            update_document_status(
                document_id,
                "uploaded"
            )

            return {
                "message": (
                    f"{file_type} upload successful. "
                    "Processing for this format is not "
                    "implemented yet."
                ),
                "document_id": document_id,
                "filename": original_filename
            }

    # ========================================================
    # HTTP EXCEPTION
    # ========================================================

    except HTTPException:

        if document_id is not None:

            update_document_status(
                document_id,
                "failed"
            )

        raise

    # ========================================================
    # GENERAL EXCEPTION
    # ========================================================

    except Exception as e:

        print(
            "UPLOAD PROCESSING ERROR:"
        )

        traceback.print_exc()

        if document_id is not None:

            update_document_status(
                document_id,
                "failed"
            )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )