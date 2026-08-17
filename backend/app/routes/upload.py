import os
import json
import traceback
import requests

from fastapi import APIRouter, UploadFile, File, HTTPException
from docx import Document

from app.extractors.Docx.document_parser import parse_document

router = APIRouter()

# Folders
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".pptx": "PPTX",
    ".xlsx": "XLSX",
    ".rtf": "RTF"
}

# C-DAC Translation API
TRANSLATION_API_URL = "https://nlpsangraha.ebhasha.in/getTranslation"


def translate_text(text, src_lang="eng-latn", tgt_lang="hin-deva"):
    """
    Send text to C-DAC translation API and return translated text.
    """

    # Don't send empty text
    if not text or not text.strip():
        return text

    payload = {
        "ip_text": text,
        "srcLang": src_lang,
        "tgtLang": tgt_lang,
        "delimiter": "",
        "nSuggestions": "1"
    }

    try:
        response = requests.post(
            TRANSLATION_API_URL,
            json=payload,
            timeout=60,
            verify=False
        )

        response.raise_for_status()

        result = response.json()

        translated_text = result.get("Output")

        if translated_text:
            return translated_text

        print("Translation API returned no Output:", result)
        return text

    except Exception as e:
        print("Translation API error:", str(e))
        return text


def translate_json(data, src_lang="eng-latn", tgt_lang="hin-deva"):
    """
    Translate all extracted text while preserving
    the existing JSON structure and formatting information.
    """

    if isinstance(data, dict):

        # Translate the main text field
        if "text" in data and isinstance(data["text"], str):
            original_text = data["text"]

            data["text"] = translate_text(
                original_text,
                src_lang,
                tgt_lang
            )

        # Translate text inside runs
        if "runs" in data and isinstance(data["runs"], list):

            for run in data["runs"]:

                if isinstance(run, dict) and "text" in run:
                    original_text = run["text"]

                    run["text"] = translate_text(
                        original_text,
                        src_lang,
                        tgt_lang
                    )

        # Process remaining nested objects
        for key, value in data.items():

            if key not in ["text", "runs"]:
                data[key] = translate_json(
                    value,
                    src_lang,
                    tgt_lang
                )

        return data

    elif isinstance(data, list):

        return [
            translate_json(
                item,
                src_lang,
                tgt_lang
            )
            for item in data
        ]

    return data


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    try:

        # -----------------------------
        # Check file extension
        # -----------------------------

        extension = os.path.splitext(file.filename)[1].lower()

        if extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(
                status_code=400,
                detail="Unsupported file type"
            )

        # -----------------------------
        # Save uploaded file
        # -----------------------------

        file_path = os.path.join(
            UPLOAD_FOLDER,
            file.filename
        )

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        print(f"File saved: {file_path}")

        file_type = ALLOWED_EXTENSIONS[extension]

        print(f"Detected file type: {file_type}")

        # -----------------------------
        # DOCX Extraction
        # -----------------------------

        if file_type == "DOCX":

            print("Opening DOCX document...")

            document = Document(file_path)

            print("Calling parse_document()...")

            result = parse_document(
                file_path,
                document
            )

            print("Document parsed successfully!")

            # -----------------------------
            # Save extracted JSON
            # -----------------------------

            json_filename = (
                os.path.splitext(file.filename)[0]
                + ".json"
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

            print(f"JSON saved: {json_path}")

            # -----------------------------
            # TRANSLATION
            # -----------------------------

            print("Starting translation...")

            translated_result = translate_json(
                result,
                src_lang="eng-latn",
                tgt_lang="hin-deva"
            )

            print("Translation completed!")

            # -----------------------------
            # Save translated JSON
            # -----------------------------

            translated_json_filename = (
                os.path.splitext(file.filename)[0]
                + "_translated.json"
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
                f"Translated JSON saved: "
                f"{translated_json_path}"
            )

           
            return {

                "message":
                    "File uploaded, extracted and translated successfully",

                "filename":
                    file.filename,

                "file_type":
                    file_type,

                "json_file":
                    json_filename,

                "translated_json_file":
                    translated_json_filename,

                "data":
                    result,

                "translated_data":
                    translated_result
            }

        # -----------------------------
        # Other file types
        # -----------------------------

        return {

            "message":
                f"{file_type} upload successful. "
                "Extraction not implemented yet."

        }

    except HTTPException:
        raise

    except Exception as e:

        print("\n========== ERROR ==========")

        traceback.print_exc()

        print("===========================\n")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )