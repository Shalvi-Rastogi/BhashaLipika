import os
import traceback

from fastapi import APIRouter, UploadFile, File, HTTPException
from docx import Document

from app.extractors.Docx.document_parser import parse_document

router = APIRouter()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        # Save uploaded file
        # -----------------------------
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        print(f" File saved: {file_path}")

        file_type = ALLOWED_EXTENSIONS[extension]
        print(f"Detected file type: {file_type}")

        # -----------------------------
        # DOCX Extraction
        # -----------------------------
        if file_type == "DOCX":

            print(" Opening DOCX document...")
            document = Document(file_path)

            print(" Calling parse_document()...")
            result = parse_document(file_path, document)

            print(" Document parsed successfully!")

            return result

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