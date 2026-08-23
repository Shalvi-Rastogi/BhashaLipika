from docx import Document
import json


def reconstruct_docx(
    original_docx_path,
    translated_json_path,
    output_docx_path
):
    """
    Reconstruct a DOCX using translated text from JSON.

    Handles:
    - Paragraphs
    - Headings
    - List items
    - Tables

    Original DOCX is used as the structural base.
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

    # =====================================================
    # PART 1: PARAGRAPH / HEADING / LIST RECONSTRUCTION
    # =====================================================

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
    # Remove empty original paragraphs
    # -----------------------------------------
    original_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if paragraph.text.strip()
    ]

    print(
        "Non-empty original paragraphs:",
        len(original_paragraphs)
    )

    # -----------------------------------------
    # Match translated elements with paragraphs
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

            paragraph.runs[0].text = translated_text

            # Clear remaining runs
            for run in paragraph.runs[1:]:
                run.text = ""

        else:
            paragraph.add_run(translated_text)

    # =====================================================
    # PART 2: TABLE RECONSTRUCTION
    # =====================================================

    print("\n========== TABLE RECONSTRUCTION ==========")

    # Get translated table elements
    table_elements = [
        element
        for element in elements
        if element.get("type") == "table"
    ]

    print("Original tables:", len(document.tables))
    print("Translated tables:", len(table_elements))

    # -----------------------------------------
    # Process each original table
    # -----------------------------------------
    for table_index, table in enumerate(document.tables):

        print(f"\nProcessing Table {table_index}")

        # Find matching translated table
        translated_table = None

        for element in table_elements:

            if element.get("table_index") == table_index:
                translated_table = element
                break

        if translated_table is None:
            print(
                f"No translated data found for table "
                f"{table_index}"
            )
            continue

        translated_cells = [
            cell
            for row in translated_table.get("rows", [])
            for cell in row.get("cells", [])
        ]

        # -----------------------------------------
        # Process rows
        # -----------------------------------------
        for row_index, row in enumerate(table.rows):

            for column_index, cell in enumerate(row.cells):

                translated_text = None

                # ---------------------------------
                # Find corresponding translated cell
                # ---------------------------------
                for translated_cell in translated_cells:

                    if (
                        translated_cell.get("row") == row_index
                        and
                        translated_cell.get("column") == column_index
                    ):
                        translated_text = translated_cell.get(
                            "text",
                            ""
                        )
                        break

                # ---------------------------------
                # Replace cell text
                # ---------------------------------
                if translated_text is not None:

                    print(
                        f"Table {table_index} | "
                        f"Row {row_index} | "
                        f"Column {column_index}"
                    )

                    # Cell usually contains at least
                    # one paragraph
                    if cell.paragraphs:

                        paragraph = cell.paragraphs[0]

                        if paragraph.runs:

                            # Put translated text
                            # into first run
                            paragraph.runs[0].text = (
                                translated_text
                            )

                            # Remove old remaining runs
                            for run in paragraph.runs[1:]:
                                run.text = ""

                        else:
                            paragraph.add_run(
                                translated_text
                            )

                    else:
                        cell.text = translated_text

    # =====================================================
    # SAVE OUTPUT
    # =====================================================

    document.save(output_docx_path)

    print("\n==========================================")
    print("Reconstruction completed.")
    print("Output:", output_docx_path)
    print("==========================================")