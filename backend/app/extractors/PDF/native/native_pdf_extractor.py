import json
import os
import fitz


def _color_to_rgb(color):
    """
    Convert PyMuPDF integer color into RGB values.
    """

    if color is None:
        return {
            "r": 0,
            "g": 0,
            "b": 0
        }

    try:
        return {
            "r": (color >> 16) & 255,
            "g": (color >> 8) & 255,
            "b": color & 255
        }

    except Exception:
        return {
            "r": 0,
            "g": 0,
            "b": 0
        }


def _get_font_properties(span):
    """
    Extract basic font properties from a PDF text span.
    """

    flags = span.get("flags", 0)

    return {
        "font_name": span.get("font"),
        "font_size": span.get("size"),
        "bold": bool(flags & 16),
        "italic": bool(flags & 2),
        "color": _color_to_rgb(
            span.get("color")
        )
    }


def extract_native_pdf_to_json(
    file_path,
    json_path
):
    """
    Extract text, position and basic formatting
    information from a native/text-based PDF.

    Output:
        One original JSON file.
    """

    document = fitz.open(file_path)

    document_data = {
        "document_name": os.path.basename(file_path),
        "document_type": "pdf",
        "pdf_type": "native",
        "pages": []
    }

    element_id = 1

    try:

        for page_index, page in enumerate(document):

            page_data = {
                "page_number": page_index + 1,
                "width": page.rect.width,
                "height": page.rect.height,
                "elements": []
            }

            page_dict = page.get_text(
                "dict"
            )

            for block in page_dict.get(
                "blocks",
                []
            ):

                # -----------------------------------------
                # Ignore image-only blocks
                # -----------------------------------------

                if block.get("type") != 0:
                    continue

                for line in block.get(
                    "lines",
                    []
                ):

                    for span in line.get(
                        "spans",
                        []
                    ):

                        text = span.get(
                            "text",
                            ""
                        )

                        if not text.strip():
                            continue

                        bbox = span.get(
                            "bbox",
                            [0, 0, 0, 0]
                        )

                        font_properties = (
                            _get_font_properties(
                                span
                            )
                        )

                        element = {
                            "id": element_id,
                            "type": "text",

                            "original_text": text,

                            "translated_text": "",

                            "bbox": [
                                round(float(bbox[0]), 2),
                                round(float(bbox[1]), 2),
                                round(float(bbox[2]), 2),
                                round(float(bbox[3]), 2)
                            ],

                            "font": font_properties,

                            "block_number": block.get(
                                "number"
                            ),

                            "line_number": line.get(
                                "dir"
                            )
                        }

                        page_data[
                            "elements"
                        ].append(
                            element
                        )

                        element_id += 1

            document_data[
                "pages"
            ].append(
                page_data
            )

    finally:
        document.close()

    # ---------------------------------------------
    # Save JSON
    # ---------------------------------------------

    os.makedirs(
        os.path.dirname(json_path),
        exist_ok=True
    )

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as json_file:

        json.dump(
            document_data,
            json_file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"[PDF] Original JSON created: {json_path}"
    )

    return document_data