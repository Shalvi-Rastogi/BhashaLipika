from docx import Document
import json


def reconstruct_docx(
    original_docx_path,
    translated_json_path,
    output_docx_path
):
    """
    Reconstruct a DOCX using translated text from JSON.

    The original DOCX is used as the structural base.
    Existing paragraph/list formatting is preserved.
    """

    # -----------------------------------------
    # Load original DOCX
    # -----------------------------------------
    document = Document(original_docx_path)

    # -----------------------------------------
    # Load translated JSON
    # -----------------------------------------
    with open(translated_json_path, "r", encoding="utf-8") as file:
        translated_data = json.load(file)

    elements = translated_data.get("elements", [])

    # -----------------------------------------
    # Keep text-based elements
    # -----------------------------------------
    text_elements = [
        element
        for element in elements
        if element.get("type") in [
            "paragraph",
            "heading",
            "list_item"
        ]
    ]

    paragraphs = document.paragraphs

    print("Original paragraphs:", len(paragraphs))
    print("Translated text elements:", len(text_elements))

    # -----------------------------------------
    # Remove empty paragraphs from matching
    # -----------------------------------------
    original_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if paragraph.text.strip()
    ]

    print("Non-empty original paragraphs:", len(original_paragraphs))

    # -----------------------------------------
    # Match translated elements with
    # non-empty original paragraphs
    # -----------------------------------------
    for paragraph, element in zip(
        original_paragraphs,
        text_elements
    ):

        translated_text = element.get("text", "")

        if not translated_text:
            continue

        # -------------------------------------
        # Preserve existing paragraph structure
        # -------------------------------------
        if paragraph.runs:

            # Put translated text into first run
            paragraph.runs[0].text = translated_text

            # Clear remaining runs
            for run in paragraph.runs[1:]:
                run.text = ""

        else:
            # Paragraph has no runs
            paragraph.add_run(translated_text)

    # -----------------------------------------
    # Save reconstructed document
    # -----------------------------------------
    document.save(output_docx_path)

    print("Reconstruction completed.")
    print("Output:", output_docx_path)