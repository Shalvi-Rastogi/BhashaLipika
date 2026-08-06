import os
import json
import traceback

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
        # Save uploaded file temporarily
        # -----------------------------
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

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
            result = parse_document(file_path, document)

            print("Document parsed successfully!")

            # -----------------------------
            # Save extracted JSON
            # -----------------------------
            json_filename = os.path.splitext(file.filename)[0] + ".json"
            json_path = os.path.join(OUTPUT_FOLDER, json_filename)

            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(result, json_file, indent=4, ensure_ascii=False)

            print(f"JSON saved: {json_path}")

            # -----------------------------
            # Delete uploaded DOCX
            # -----------------------------
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted uploaded file: {file_path}")

            return {
                "message": "Extraction successful",
                "filename": file.filename,
                "file_type": file_type,
                "json_file": json_filename,
                "data": result
            }

        # -----------------------------
        # Other file types
        # -----------------------------
        return {
            "message": f"{file_type} upload successful. Extraction not implemented yet."
        }

    except Exception as e:
        print("\n========== ERROR ==========")
        traceback.print_exc()
        print("===========================\n")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )