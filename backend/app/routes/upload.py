import os
from fastapi import APIRouter, UploadFile, File, HTTPException

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
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Internal use only
    file_type = ALLOWED_EXTENSIONS[extension]
    print(f"Detected file type: {file_type}")

    # Later you'll call the correct extraction function here
    # if file_type == "PDF":
    #     extract_pdf(file_path)
    # elif file_type == "DOCX":
    #     extract_docx(file_path)

    return {
        "message": "File uploaded successfully"
    }