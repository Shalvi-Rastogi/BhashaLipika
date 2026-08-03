import os

from .document_iterator import iter_block_items
from .paragraph_extractor import process_paragraph
from .image_extractor import extract_images_from_docx

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
        # Extract text from images using OCR
    image_elements = extract_images_from_docx(docx_path)
    print("OCR Images:", image_elements)

    for image in image_elements:
        # Combine OCR results into one string
        ocr_text = " ".join(item["text"] for item in image["ocr"])  

        result["elements"].append({
            "id": element_id,
            "type": "image_text",
            "order": element_id,
            "image_name": image["image_name"],
            "text": image["ocr"],
            "ocr_details": image["ocr"]
        })

        element_id += 1
    return result