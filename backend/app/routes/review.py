import os
import json
import shutil

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from app.database.database import get_db
from app.database.models import Document
from app.reconstructors.xlsx_reconstructor import reconstruct_xlsx
from app.reconstructors.docx_reconstructor import reconstruct_docx
from app.reconstructors.pptx_reconstructor import reconstruct_pptx
from app.reconstructors.PDF.native_pdf_reconstructor import reconstruct_native_pdf
from app.utils.xls_converter import convert_xlsx_to_xls
from app.utils.doc_converter import convert_docx_to_doc


router = APIRouter()


# -----------------------------
# Request Models
# -----------------------------

class CellEdit(BaseModel):
    cell: str
    translated_text: str


class ImageTextEdit(BaseModel):
    sheet_index: int = Field(ge=0)
    image_index: int = Field(ge=0)
    ocr_index: int = Field(ge=0)
    translated_text: str


class DocxTextEdit(BaseModel):
    path: list[str | int]
    translated_text: str


class SaveReviewRequest(BaseModel):
    document_id: int
    edits: list[CellEdit] = Field(default_factory=list)
    image_edits: list[ImageTextEdit] = Field(default_factory=list)
    docx_edits: list[DocxTextEdit] = Field(default_factory=list)
    pptx_edits: list[DocxTextEdit] = Field(default_factory=list)
    pdf_edits: list[DocxTextEdit] = Field(default_factory=list)


def _path_key(container, part):
    if isinstance(container, list):
        if isinstance(part, bool):
            raise TypeError("Boolean values are not valid list indices.")
        return int(part)
    return part


# -----------------------------
# Save Edited Translations
# -----------------------------

@router.post("/review/save")
def save_review(
    request: SaveReviewRequest,
    db: Session = Depends(get_db)
):

    # Find document in database
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

    file_type = document.file_type.lower()
    
    if file_type not in {"doc", "docx", "xls", "xlsx", "ppt", "pptx", "pdf"}:
        raise HTTPException(
            status_code=400,
            detail="Review editing supports DOC, DOCX, XLS, XLSX, PPT, PPTX, and PDF files."
        )

    if not document.output_filename:
        raise HTTPException(
            status_code=404,
            detail="Reconstructed file not found."
        )

    # Path of the original reconstructed file (safe from overwriting)
    original_output_path = os.path.join("outputs", document.output_filename)

    if not os.path.exists(original_output_path):
        raise HTTPException(
            status_code=404,
            detail="Reconstructed document does not exist."
        )

    # Generate new filename appended with '_reviewed'
    name, ext = os.path.splitext(document.output_filename)
    reviewed_filename = f"{name}_reviewed{ext}"
    reviewed_output_path = os.path.join("outputs", reviewed_filename)

    try:
        # ---------------------------------------------
        # <-- BLOCK FOR DOC / DOCX -->
        # ---------------------------------------------
        if file_type in {"doc", "docx"}:
            filename_stem = os.path.splitext(
                os.path.basename(document.original_filename)
            )[0]
            language_pair = (
                f"{document.source_language}_to_"
                f"{document.target_language}"
            )
            translated_json_path = os.path.join(
                "outputs",
                f"{filename_stem}_translated_{language_pair}.json",
            )
            if not os.path.exists(translated_json_path):
                translated_json_path = os.path.join(
                    "outputs",
                    f"{filename_stem}_translated_{document.target_language}.json",
                )
            original_docx_path = os.path.join(
                "uploads",
                f"{filename_stem}.docx",
            )

            if not os.path.exists(translated_json_path):
                raise HTTPException(status_code=404, detail="Translated Word document data was not found.")
            if not os.path.exists(original_docx_path):
                raise HTTPException(status_code=404, detail="Original Word document was not found.")

            with open(translated_json_path, "r", encoding="utf-8") as data_file:
                translated_data = json.load(data_file)

            for edit in request.docx_edits:
                target = translated_data
                try:
                    if not edit.path:
                        raise ValueError("Empty edit path.")
                    for part in edit.path[:-1]:
                        target = target[_path_key(target, part)]
                    final_part = _path_key(target, edit.path[-1])
                    if isinstance(target, dict) and final_part == "translated_text":
                        current_value = target.get(final_part, "")
                    else:
                        current_value = target[final_part]
                except (IndexError, KeyError, TypeError, ValueError):
                    raise HTTPException(status_code=400, detail="Invalid Word document text path.")

                # Allow None values to be replaced by new text string
                if current_value is not None and not isinstance(current_value, str):
                    raise HTTPException(status_code=400, detail="Word document edit must target a text value.")
                target[final_part] = edit.translated_text

                if "runs" in edit.path:
                    runs_index = edit.path.index("runs")
                    paragraph = translated_data
                    for part in edit.path[:runs_index]:
                        paragraph = paragraph[_path_key(paragraph, part)]
                    if isinstance(paragraph, dict) and isinstance(paragraph.get("runs"), list):
                        paragraph["text"] = "".join(
                            run.get("text", "") for run in paragraph["runs"] if isinstance(run, dict)
                        )

            with open(translated_json_path, "w", encoding="utf-8") as data_file:
                json.dump(translated_data, data_file, ensure_ascii=False, indent=4)

            # Reconstruct into the new '_reviewed' file
            reconstruct_docx(
                original_docx_path,
                translated_json_path,
                reviewed_output_path,
            )

            if file_type == "doc":
                conversion_dir = os.path.join("outputs", f".review_doc_{document.id}")
                shutil.rmtree(conversion_dir, ignore_errors=True)
                os.makedirs(conversion_dir, exist_ok=True)
                try:
                    converted_path = convert_docx_to_doc(reviewed_output_path, conversion_dir)
                    os.replace(converted_path, reviewed_output_path)
                finally:
                    shutil.rmtree(conversion_dir, ignore_errors=True)

        # ---------------------------------------------
        # <-- BLOCK FOR PPT / PPTX -->
        # ---------------------------------------------
        elif file_type in {"ppt", "pptx"}:
            filename_stem = os.path.splitext(os.path.basename(document.original_filename))[0]
            language_pair = f"{document.source_language}_to_{document.target_language}"
            translated_json_path = os.path.join("outputs", f"{filename_stem}_translated_{language_pair}.json")
            if not os.path.exists(translated_json_path):
                translated_json_path = os.path.join("outputs", f"{filename_stem}_translated_{document.target_language}.json")
            
            original_pptx_path = os.path.join("uploads", os.path.basename(document.original_filename))

            if not os.path.exists(translated_json_path):
                raise HTTPException(status_code=404, detail="Translated Presentation data was not found.")
            if not os.path.exists(original_pptx_path):
                raise HTTPException(status_code=404, detail="Original Presentation was not found.")

            with open(translated_json_path, "r", encoding="utf-8") as data_file:
                translated_data = json.load(data_file)

            for edit in request.pptx_edits:
                target = translated_data
                try:
                    if not edit.path:
                        raise ValueError("Empty edit path.")
                    for part in edit.path[:-1]:
                        target = target[_path_key(target, part)]
                    final_part = _path_key(target, edit.path[-1])
                    if isinstance(target, dict) and final_part == "translated_text":
                        current_value = target.get(final_part, "")
                    else:
                        current_value = target[final_part]
                except (IndexError, KeyError, TypeError, ValueError):
                    raise HTTPException(status_code=400, detail="Invalid Presentation text path.")

                if current_value is not None and not isinstance(current_value, str):
                    raise HTTPException(status_code=400, detail="Presentation edit must target a text value.")
                target[final_part] = edit.translated_text

                if "runs" in edit.path:
                    runs_index = edit.path.index("runs")
                    paragraph = translated_data
                    for part in edit.path[:runs_index]:
                        paragraph = paragraph[_path_key(paragraph, part)]
                    if isinstance(paragraph, dict) and isinstance(paragraph.get("runs"), list):
                        paragraph["text"] = "".join(
                            run.get("text", "") for run in paragraph["runs"] if isinstance(run, dict)
                        )

            with open(translated_json_path, "w", encoding="utf-8") as data_file:
                json.dump(translated_data, data_file, ensure_ascii=False, indent=4)

            # Reconstruct into the new '_reviewed' file
            reconstruct_pptx(
                original_pptx_path,
                translated_json_path,
                reviewed_output_path,
            )

        # ---------------------------------------------
        # <-- BLOCK FOR PDF -->
        # ---------------------------------------------
        elif file_type == "pdf":
            filename_stem = os.path.splitext(os.path.basename(document.original_filename))[0]
            language_pair = f"{document.source_language}_to_{document.target_language}"
            translated_json_path = os.path.join("outputs", f"{filename_stem}_translated_{language_pair}.json")
            if not os.path.exists(translated_json_path):
                translated_json_path = os.path.join("outputs", f"{filename_stem}_translated_{document.target_language}.json")
            
            # Use exact original filename to avoid extension case mismatch
            original_pdf_path = os.path.join("uploads", os.path.basename(document.original_filename))

            if not os.path.exists(translated_json_path):
                raise HTTPException(status_code=404, detail="Translated PDF data was not found.")
            if not os.path.exists(original_pdf_path):
                raise HTTPException(status_code=404, detail="Original PDF was not found.")

            with open(translated_json_path, "r", encoding="utf-8") as data_file:
                translated_data = json.load(data_file)

            # Safely capture edits regardless of what payload key the frontend used
            edits_to_process = request.pdf_edits + request.docx_edits + request.pptx_edits
            print(f"\n[DEBUG PDF] Received {len(edits_to_process)} text edits from frontend.")

            for edit in edits_to_process:
                target = translated_data
                try:
                    if not edit.path:
                        continue
                    for part in edit.path[:-1]:
                        target = target[_path_key(target, part)]
                    final_part = _path_key(target, edit.path[-1])
                    
                    if isinstance(target, dict) and final_part == "translated_text":
                        current_value = target.get(final_part, "")
                    else:
                        current_value = target[final_part]
                except (IndexError, KeyError, TypeError, ValueError):
                    print(f"[DEBUG PDF] Skipping invalid path: {edit.path}")
                    continue

                if current_value is not None and not isinstance(current_value, str):
                    continue
                
                # Apply the new text
                target[final_part] = edit.translated_text

                # CRITICAL FIX: If we edited the main block text, we MUST delete the old segments!
                # Otherwise, the PDF reconstructor will ignore our new text and render the old segments!
                if isinstance(target, dict) and final_part == "translated_text":
                    if "segments" in target:
                        del target["segments"]
                        print(f"[DEBUG PDF] Deleted old 'segments' for block to force new text render.")

            with open(translated_json_path, "w", encoding="utf-8") as data_file:
                json.dump(translated_data, data_file, ensure_ascii=False, indent=4)

            # Reconstruct into the new '_reviewed' file
            print(f"[DEBUG PDF] Reconstructing into {reviewed_output_path}...")
            reconstruct_native_pdf(
                original_pdf_path,
                translated_json_path,
                reviewed_output_path,
                target_language=document.target_language
            )
            print("[DEBUG PDF] PDF successfully reconstructed and saved!\n")

        # ---------------------------------------------
        # <-- BLOCK FOR XLS / IMAGES -->
        # ---------------------------------------------
        elif request.image_edits or file_type == "xls":
            filename_stem = os.path.splitext(os.path.basename(document.original_filename))[0]
            language_pair = f"{document.source_language}_to_{document.target_language}"
            translated_json_path = os.path.join("outputs", f"{filename_stem}_translated_{language_pair}.json")
            if not os.path.exists(translated_json_path):
                translated_json_path = os.path.join("outputs", f"{filename_stem}_translated_{document.target_language}.json")
            
            if file_type == "xls":
                original_path = os.path.join("uploads", f"xls_to_xlsx_{document.id}", f"{filename_stem}.xlsx")
            else:
                original_path = os.path.join("uploads", os.path.basename(document.original_filename))

            if not os.path.exists(translated_json_path):
                raise HTTPException(status_code=404, detail="Translated workbook data was not found.")
            if not os.path.exists(original_path):
                raise HTTPException(status_code=404, detail="Original workbook was not found.")

            with open(translated_json_path, "r", encoding="utf-8") as data_file:
                workbook_data = json.load(data_file)

            sheets = workbook_data.get("sheets", [])
            for edit in request.edits:
                first_sheet_cells = sheets[0].get("cells", []) if sheets else []
                matching_cell = next(
                    (cell for cell in first_sheet_cells if cell.get("coordinate") == edit.cell),
                    None,
                )
                if matching_cell is not None:
                    matching_cell["translated_text"] = edit.translated_text

            for edit in request.image_edits:
                if edit.sheet_index >= len(sheets):
                    raise HTTPException(status_code=400, detail="Invalid worksheet in image edit.")
                images = sheets[edit.sheet_index].get("images", [])
                if edit.image_index >= len(images):
                    raise HTTPException(status_code=400, detail="Invalid image in review edit.")
                ocr_data = images[edit.image_index].get("ocr_data", [])
                if edit.ocr_index >= len(ocr_data):
                    raise HTTPException(status_code=400, detail="Invalid image text in review edit.")
                ocr_data[edit.ocr_index]["translated_text"] = edit.translated_text
                images[edit.image_index]["translated_text"] = "\n".join(
                    item.get("translated_text", "") for item in ocr_data
                )

            with open(translated_json_path, "w", encoding="utf-8") as data_file:
                json.dump(workbook_data, data_file, ensure_ascii=False, indent=4)

            # Reconstruct into the new '_reviewed' file
            reconstruct_xlsx(
                original_file_path=original_path,
                translated_json_path=translated_json_path,
                output_file_path=reviewed_output_path,
            )

            if file_type == "xls":
                conversion_dir = os.path.join("outputs", f".review_xls_{document.id}")
                shutil.rmtree(conversion_dir, ignore_errors=True)
                os.makedirs(conversion_dir, exist_ok=True)
                try:
                    converted_path = convert_xlsx_to_xls(reviewed_output_path, conversion_dir)
                    os.replace(converted_path, reviewed_output_path)
                finally:
                    shutil.rmtree(conversion_dir, ignore_errors=True)
        else:
            # Check latest file to edit (either reviewed or original)
            latest_path = reviewed_output_path if os.path.exists(reviewed_output_path) else original_output_path
            workbook = load_workbook(latest_path)
            worksheet = workbook[workbook.sheetnames[0]]

            for edit in request.edits:
                worksheet[edit.cell] = edit.translated_text

            # Always save into the reviewed file
            workbook.save(reviewed_output_path)

        return {
            "message": "Changes saved successfully.",
            "document_id": document.id,
            "filename": reviewed_filename
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save changes: {str(e)}"
        )


# -----------------------------
# Download Final Document
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

    # Check if the user has created an edited "_reviewed" file
    name, ext = os.path.splitext(document.output_filename)
    reviewed_filename = f"{name}_reviewed{ext}"
    
    original_output_path = os.path.join("outputs", document.output_filename)
    reviewed_output_path = os.path.join("outputs", reviewed_filename)

    # Serve the reviewed file if it exists; otherwise serve the original AI output
    if os.path.exists(reviewed_output_path):
        target_path = reviewed_output_path
        target_filename = reviewed_filename
    elif os.path.exists(original_output_path):
        target_path = original_output_path
        target_filename = document.output_filename
    else:
        raise HTTPException(
            status_code=404,
            detail="Final document does not exist."
        )

    extension_media_types = {
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pdf": "application/pdf",
    }
    extension = os.path.splitext(target_filename)[1].lower()
    media_type = extension_media_types.get(
        extension,
        "application/octet-stream",
    )

    return FileResponse(
        path=target_path,
        filename=target_filename,
        media_type=media_type,
    )