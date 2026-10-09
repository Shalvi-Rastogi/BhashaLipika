import os
import posixpath

from docx.oxml.ns import qn

from .document_iterator import iter_block_items
from .paragraph_extractor import process_paragraph
from .table_extractor import process_table
from .image_extractor import extract_images_from_docx
from .textbox_extractor import extract_textboxes_from_docx

VML_IMAGEDATA_TAG = "{urn:schemas-microsoft-com:vml}imagedata"


def _get_block_content_positions(block, document, next_position):
    image_positions = {}
    first_text_position = None

    for node in block._element.iter():
        node_position = next_position

        if node.tag == qn("w:t") and (node.text or "").strip():
            if first_text_position is None:
                first_text_position = node_position
            next_position += 1
            continue

        if node.tag not in {qn("a:blip"), VML_IMAGEDATA_TAG}:
            continue

        relationship_id = (
            node.get(qn("r:embed"))
            or node.get(qn("r:link"))
            or node.get(qn("r:id"))
        )
        relationship = document.part.rels.get(relationship_id)

        if relationship and not relationship.is_external:
            target = relationship.target_ref.replace("\\", "/")
            media_path = (
                target.lstrip("/")
                if target.startswith("/")
                else posixpath.normpath(posixpath.join("word", target))
            )
            image_positions.setdefault(media_path, node_position)

        next_position += 1

    return first_text_position, image_positions, next_position


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
    table_index = 0
    document_position = 0
    image_positions = {}

    for block in iter_block_items(document):
        text_position, block_image_positions, document_position = (
            _get_block_content_positions(
                block,
                document,
                document_position,
            )
        )
        image_positions.update(block_image_positions)

        # Try paragraph/heading
        element = process_paragraph(block, element_id)

        # If not a paragraph, try table
        if element is None:
            element = process_table(block, element_id)

        if element is not None:
            if element["type"] == "table":
                element["table_index"] = table_index
                table_index += 1

            element["review_order"] = (
                text_position
                if text_position is not None
                else document_position
            )
            result["elements"].append(element)
            element_id += 1

        document_position += 1

        # Extract text from Word textboxes/shapes
    textbox_elements = extract_textboxes_from_docx(docx_path)

    for textbox in textbox_elements:
        result["elements"].append({
            "id": element_id,
            "type": "textbox",
            "order": element_id,
            "textbox_id": textbox["id"],
            "text": textbox["text"],
            "paragraphs": textbox["paragraphs"]
        })

        element_id += 1

    # Extract text from images using OCR
    image_elements = extract_images_from_docx(docx_path)

    for image in image_elements:

        # Combine OCR results into one string
        ocr_text = " ".join(item["text"] for item in image["ocr"])

        result["elements"].append({
            "id": element_id,
            "type": "image_text",
            "order": element_id,
            "image_name": image["image_name"],
            "original_media": image["original_media"],
            "image_path": image["image_path"],
            "text": ocr_text,
            "ocr_details": image["ocr"],
            "review_order": image_positions.get(
                image["original_media"],
                document_position + element_id,
            ),
        })

        element_id += 1

    return result