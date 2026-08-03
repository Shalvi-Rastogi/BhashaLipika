import os

from .document_iterator import iter_block_items
from .paragraph_extractor import process_paragraph
from .table_extractor import process_table


def parse_document(docx_path, document):
    """
    Parse the complete DOCX document and build
    the intermediate JSON representation.
    """

    result = {
        "document_name": os.path.basename(docx_path),
        "document_type": "docx",
        "elements": []
    }

    element_id = 1

    print("Starting document parsing...")

    for block in iter_block_items(document):

        print(f"\nProcessing block {element_id}: {type(block)}")

        # Try paragraph/heading
        element = process_paragraph(block, element_id)

        if element is not None:
            print(f" Paragraph/Heading extracted: {element['type']}")
        else:
            print(" Not a paragraph. Trying table...")
            element = process_table(block, element_id)

            if element is not None:
                print(" Table extracted successfully.")
            else:
                print(" Unknown block.")

        if element is not None:
            result["elements"].append(element)
            element_id += 1

    print("\nDocument parsing completed.")

    return result