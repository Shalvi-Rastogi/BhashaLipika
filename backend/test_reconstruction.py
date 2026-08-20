from app.reconstructors.docx_reconstructor import reconstruct_docx


original_docx = "uploads/seminar speaking material.docx"

translated_json = "outputs/seminar speaking material_translated.json"

output_docx = "outputs/seminar speaking material_reconstructed.docx"


reconstruct_docx(
    original_docx,
    translated_json,
    output_docx
)