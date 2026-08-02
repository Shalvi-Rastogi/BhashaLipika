import os

from .document_iterator import iter_block_items
from .paragraph_extractor import process_paragraph


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

    for block in iter_block_items(document):

        element = process_paragraph(block, element_id)

        if element is not None:
            result["elements"].append(element)
            element_id += 1

    return result