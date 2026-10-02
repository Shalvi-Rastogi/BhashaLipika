import json
import os

import pymupdf as fitz

BULLETS = {"•", "▪", "◦", "●", "-", "–", "∙", "·", "○", "■"}


def _color_to_rgb(color):
    if color is None:
        return {"r": 0, "g": 0, "b": 0}
    try:
        return {
            "r": (color >> 16) & 255,
            "g": (color >> 8) & 255,
            "b": color & 255,
        }
    except Exception:
        return {"r": 0, "g": 0, "b": 0}


def _get_font_properties(span):
    flags = span.get("flags", 0)
    name = span.get("font") or ""
    lname = name.lower()
    return {
        "font_name": name,
        "font_size": span.get("size"),
        "bold": bool(flags & 16) or "bold" in lname,
        "italic": bool(flags & 2) or "italic" in lname or "oblique" in lname,
        "color": _color_to_rgb(span.get("color")),
    }


def _make_element(element_id, text, spans, block_number):
    x0 = min(s["bbox"][0] for s in spans)
    y0 = min(s["bbox"][1] for s in spans)
    x1 = max(s["bbox"][2] for s in spans)
    y1 = max(s["bbox"][3] for s in spans)

    return {
        "id": element_id,
        "type": "text",
        "original_text": text,
        "translated_text": "",
        "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
        "font": _get_font_properties(spans[0]),
        "block_number": block_number,
    }


def extract_native_pdf_to_json(file_path, json_path):
    """
    Native PDF se paragraph-level text extract karke JSON banata hai.
    Har block = ek paragraph (bullet alag element).
    """

    document = fitz.open(file_path)

    document_data = {
        "document_name": os.path.basename(file_path),
        "document_type": "pdf",
        "pdf_type": "native",
        "pages": [],
    }

    element_id = 1

    try:
        for page_index, page in enumerate(document):

            page_data = {
                "page_number": page_index + 1,
                "width": page.rect.width,
                "height": page.rect.height,
                "elements": [],
                "images": [],
            }

            page_dict = page.get_text("dict")

            for block in page_dict.get("blocks", []):

                if block.get("type") != 0:
                    continue

                block_number = block.get("number")
                bullet_span = None
                line_spans = []

                for line in block.get("lines", []):
                    spans = [
                        s for s in line.get("spans", [])
                        if s.get("text", "").strip()
                    ]
                    if not spans:
                        continue

                    if (
                        bullet_span is None
                        and not line_spans
                        and spans[0]["text"].strip() in BULLETS
                    ):
                        bullet_span = spans[0]
                        spans = spans[1:]

                    if spans:
                        line_spans.append(spans)

                if bullet_span is not None:
                    page_data["elements"].append(
                        _make_element(
                            element_id,
                            bullet_span["text"].strip(),
                            [bullet_span],
                            block_number,
                        )
                    )
                    element_id += 1

                if line_spans:
                    all_spans = [s for spans in line_spans for s in spans]

                    paragraph = " ".join(
                        "".join(s["text"] for s in spans).strip()
                        for spans in line_spans
                    )
                    paragraph = " ".join(paragraph.split())

                    if paragraph:
                        page_data["elements"].append(
                            _make_element(
                                element_id,
                                paragraph,
                                all_spans,
                                block_number,
                            )
                        )
                        element_id += 1

            document_data["pages"].append(page_data)

    finally:
        document.close()

    output_directory = os.path.dirname(json_path)
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)

    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(document_data, json_file, indent=4, ensure_ascii=False)

    print(f"[PDF] Original JSON created: {json_path}")

    return document_data