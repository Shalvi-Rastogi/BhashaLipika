import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from app.database.database import get_db
from app.database.models import Document


router = APIRouter()


# -----------------------------
# Request models
# -----------------------------

class CellEdit(BaseModel):
    cell: str
    translated_text: str


class SaveReviewRequest(BaseModel):
    document_id: int
    edits: list[CellEdit]


# -----------------------------
# Save edited translations
# -----------------------------

@router.post("/review/save")
def save_review(
    request: SaveReviewRequest,
    db: Session = Depends(get_db)
):

    # Find document
    document = (
        db.query(Document)
        .filter(Document.id == request.document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    if document.file_type.lower() != "xlsx":
        raise HTTPException(
            status_code=400,
            detail="Review editing currently supports XLSX files."
        )

    if not document.output_filename:
        raise HTTPException(
            status_code=404,
            detail="Reconstructed file not found."
        )

    # Locate reconstructed file
    output_path = os.path.join(
        "outputs",
        document.output_filename
    )

    if not os.path.exists(output_path):
        raise HTTPException(
            status_code=404,
            detail="Reconstructed document does not exist."
        )

    try:
        # Open reconstructed Excel file
        workbook = load_workbook(output_path)

        # Currently review page works with the first sheet
        worksheet = workbook[workbook.sheetnames[0]]

        # Apply user's edits
        for edit in request.edits:
            worksheet[edit.cell] = edit.translated_text

        # Save changes
        workbook.save(output_path)

        return {
            "message": "Changes saved successfully.",
            "document_id": document.id,
            "filename": document.output_filename
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save changes: {str(e)}"
        )


# -----------------------------
# Download final document
# -----------------------------

@router.get("/review/download/{document_id}")
def download_final_document(
    document_id: int,
    db: Session = Depends(get_db)
):

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    if not document.output_filename:
        raise HTTPException(
            status_code=404,
            detail="Final document not found."
        )

    output_path = os.path.join(
        "outputs",
        document.output_filename
    )

    if not os.path.exists(output_path):
        raise HTTPException(
            status_code=404,
            detail="Final document does not exist."
        )

    return FileResponse(
        path=output_path,
        filename=document.output_filename,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        )
    )