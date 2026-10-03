import json
import os

import pymupdf as fitz
from app.extractors.PDF.native.native_pdf_image_extractor import (
    extract_native_pdf_images
)

BULLETS = {"•", "▪", "◦", "●", "-", "–", "∙", "·", "○", "■"}


# =========================================================
# BASIC HELPERS
# =========================================================

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


# =========================================================
# UNDERLINE / SEGMENT HELPERS (text paragraphs)
# =========================================================

def _underline_lines(page):
    """Page par drawn patli horizontal lines/rects (underline candidates)."""
    found = []
    try:
        drawings = page.get_drawings()
    except Exception:
        return found
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 1.0:
                    found.append((min(p1.x, p2.x), max(p1.x, p2.x), (p1.y + p2.y) / 2))
            elif item[0] == "re":
                r = item[1]
                if r.height < 2.5 and r.width > 2:
                    found.append((r.x0, r.x1, (r.y0 + r.y1) / 2))
    return found


def _is_underlined(span, lines):
    x0, _, x1, y1 = span["bbox"]
    size = span.get("size") or 10
    base = span.get("origin", (0, y1))[1]
    width = x1 - x0
    if width <= 0:
        return False
    for lx0, lx1, ly in lines:
        if base - 1 <= ly <= base + size * 0.3:
            if (min(x1, lx1) - max(x0, lx0)) / width >= 0.5:
                return True
    return False


def _span_font(span, underlines):
    font = _get_font_properties(span)
    font["underline"] = _is_underlined(span, underlines)
    return font


def _style_key(font):
    c = font["color"]
    return (font["bold"], font["italic"], font["underline"], c["r"], c["g"], c["b"])


def _clean(text):
    return " ".join(text.split())


def _build_segments(line_spans, underlines):
    """Paragraph ko (label + baaki) style-segments me todta hai."""
    runs = []
    for spans in line_spans:
        for i, s in enumerate(spans):
            t = s["text"] + (" " if i == len(spans) - 1 else "")
            font = _span_font(s, underlines)
            k = _style_key(font)
            if runs and runs[-1]["key"] == k:
                runs[-1]["text"] += t
            else:
                runs.append({"text": t, "font": font, "key": k})

    if len(runs) == 1:
        return [{"text": _clean(runs[0]["text"]), "translated_text": "", "font": runs[0]["font"]}]

    lead, rest = runs[0], runs[1:]

    weight = {}
    for r in rest:
        weight[r["key"]] = weight.get(r["key"], 0) + len(r["text"].strip())
    dom_key = max(weight, key=weight.get)
    dom_font = next(r["font"] for r in rest if r["key"] == dom_key)
    rest_text = _clean(" ".join(r["text"] for r in rest))

    if lead["key"] == dom_key or not rest_text:
        full = _clean(" ".join(r["text"] for r in runs))
        return [{"text": full, "translated_text": "", "font": dom_font}]

    return [
        {"text": _clean(lead["text"]), "translated_text": "", "font": lead["font"]},
        {"text": rest_text, "translated_text": "", "font": dom_font},
    ]


def _split_inline_bullet(span):
    """'• text' wale span ko (bullet span, text span) me todo."""
    t = span["text"].lstrip()
    if len(t) > 1 and t[0] in BULLETS and t[1] == " ":
        x0, y0, x1, y1 = span["bbox"]
        size = span.get("size") or 10
        bullet = dict(span, text=t[0], bbox=(x0, y0, x0 + size * 0.5, y1))
        rest = dict(span, text=t[1:].strip(), bbox=(x0 + size * 0.6, y0, x1, y1))
        return bullet, rest
    return None, span


def _make_element(element_id, text, spans, block_number, font, segments=None):
    x0 = min(s["bbox"][0] for s in spans)
    y0 = min(s["bbox"][1] for s in spans)
    x1 = max(s["bbox"][2] for s in spans)
    y1 = max(s["bbox"][3] for s in spans)

    el = {
        "id": element_id,
        "type": "text",
        "original_text": text,
        "translated_text": "",
        "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
        "font": font,
        "block_number": block_number,
    }
    if segments:
        el["segments"] = segments
    return el


# =========================================================
# TABLE CODE (Shalvi) - UNCHANGED
# =========================================================

def _infer_cell_alignment(cell_bbox, matching_spans):
    if not matching_spans:
        return "left"

    text_left = min(span["bbox"][0] for span in matching_spans)
    text_right = max(span["bbox"][2] for span in matching_spans)
    left_margin = max(0, text_left - cell_bbox[0])
    right_margin = max(0, cell_bbox[2] - text_right)
    font_size = max(span.get("size", 0) for span in matching_spans)
    tolerance = max(2.0, font_size * 0.5)

    if abs(left_margin - right_margin) <= tolerance:
        return "center"
    return "left" if left_margin < right_margin else "right"


def _text_from_spans(spans):
    ordered = sorted(
        spans,
        key=lambda span: (
            span.get("origin", (0, span["bbox"][1]))[1],
            span["bbox"][0],
        ),
    )
    lines = []

    for span in ordered:
        baseline = span.get("origin", (0, span["bbox"][1]))[1]
        if not lines or abs(lines[-1][0] - baseline) > max(
            1.5, float(span.get("size") or 0) * 0.25
        ):
            lines.append((baseline, []))
        lines[-1][1].append(span)

    text_lines = []
    for _, line_spans in lines:
        line_spans.sort(key=lambda span: span["bbox"][0])
        pieces = []
        previous_right = None
        for span in line_spans:
            value = span.get("text", "").strip()
            if not value:
                continue
            gap = (
                span["bbox"][0] - previous_right
                if previous_right is not None
                else 0
            )
            if pieces and gap > max(1.0, float(span.get("size") or 0) * 0.15):
                pieces.append(" ")
            pieces.append(value)
            previous_right = span["bbox"][2]
        if pieces:
            text_lines.append("".join(pieces))

    return " ".join(" ".join(text_lines).split())


def _is_likely_borderless_table(table, spans):
    table_rect = fitz.Rect(table.bbox)
    cell_rects = [
        fitz.Rect(cell_bbox)
        for row in table.rows
        for cell_bbox in row.cells
        if cell_bbox
    ]
    table_spans = [
        span
        for span in spans
        if table_rect.contains(
            fitz.Point(
                (span["bbox"][0] + span["bbox"][2]) / 2,
                (span["bbox"][1] + span["bbox"][3]) / 2,
            )
        )
    ]
    if table.col_count < 2 or len(table_spans) < 4 or not cell_rects:
        return False

    contained = 0
    for span in table_spans:
        span_rect = fitz.Rect(span["bbox"])
        tolerance = max(2.0, float(span.get("size") or 0) * 0.35)
        if any(
            (cell_rect + (-tolerance, -tolerance, tolerance, tolerance)).contains(
                span_rect
            )
            for cell_rect in cell_rects
        ):
            contained += 1

    return contained / len(table_spans) >= 0.8


def _extract_tables(page, page_dict, element_id):
    spans = [
        span
        for block in page_dict.get("blocks", [])
        if block.get("type") == 0
        for line in block.get("lines", [])
        for span in line.get("spans", [])
        if span.get("text", "").strip()
    ]
    used_text_strategy = False
    try:
        tables = page.find_tables().tables
        if not tables:
            tables = page.find_tables(strategy="text").tables
            used_text_strategy = True
    except Exception:
        tables = []

    if used_text_strategy:
        tables = [
            table
            for table in tables
            if _is_likely_borderless_table(table, spans)
        ]

    elements = []
    table_bounds = []

    for table in tables:
        table_bbox = [round(float(value), 2) for value in table.bbox]
        table_bounds.append(table_bbox)
        table_rect = page.rect.__class__(table_bbox)
        nested_bounds = []
        for child_table in tables:
            if child_table is table:
                continue
            child_bbox = [round(float(value), 2) for value in child_table.bbox]
            child_rect = page.rect.__class__(child_bbox)
            if (
                table_rect.contains(child_rect)
                and child_rect.width * child_rect.height
                < table_rect.width * table_rect.height
            ):
                nested_bounds.append(child_bbox)

        extracted_rows = table.extract()
        source_rows = table.rows
        cell_boxes = [
            [round(float(value), 2) for value in cell_bbox]
            for row in source_rows
            for cell_bbox in row.cells
            if cell_bbox
        ]
        column_boundaries = sorted(
            {table_bbox[0], table_bbox[2]}
            | {box[0] for box in cell_boxes}
            | {box[2] for box in cell_boxes}
        )
        row_boundaries = sorted(
            {table_bbox[1], table_bbox[3]}
            | {box[1] for box in cell_boxes}
            | {box[3] for box in cell_boxes}
        )

        def boundary_index(value, boundaries):
            return min(
                range(len(boundaries)),
                key=lambda index: abs(boundaries[index] - value),
            )

        rows = []

        for source_row_index, row_text in enumerate(extracted_rows):
            if not any((text or "").strip() for text in row_text):
                continue

            row_index = len(rows)
            cells = []
            source_cells = (
                source_rows[source_row_index].cells
                if source_row_index < len(source_rows)
                else []
            )
            for column_index, cell_bbox in enumerate(source_cells):
                if not cell_bbox:
                    continue

                cell_box = (
                    [round(float(value), 2) for value in cell_bbox]
                )
                text = row_text[column_index] if column_index < len(row_text) else ""
                first_column = boundary_index(cell_box[0], column_boundaries)
                last_column = boundary_index(cell_box[2], column_boundaries)
                first_row = boundary_index(cell_box[1], row_boundaries)
                last_row = boundary_index(cell_box[3], row_boundaries)
                matching_spans = []

                cell_rect = page.rect.__class__(cell_bbox)
                matching_spans = [
                    span
                    for span in spans
                    if cell_rect.intersects(span.get("bbox", (0, 0, 0, 0)))
                    and not any(
                        nested_bbox[0]
                        <= (span["bbox"][0] + span["bbox"][2]) / 2
                        <= nested_bbox[2]
                        and nested_bbox[1]
                        <= (span["bbox"][1] + span["bbox"][3]) / 2
                        <= nested_bbox[3]
                        for nested_bbox in nested_bounds
                    )
                ]
                contains_nested_table = any(
                    cell_rect.contains(page.rect.__class__(nested_bbox))
                    for nested_bbox in nested_bounds
                )
                if contains_nested_table:
                    text = _text_from_spans(matching_spans)
                text_alignment = _infer_cell_alignment(
                    cell_bbox, matching_spans
                )

                cell = {
                    "row": row_index,
                    "column": column_index,
                    "bbox": cell_box,
                    "original_text": text or "",
                    "translated_text": "",
                    "rowspan": max(1, last_row - first_row),
                    "colspan": max(1, last_column - first_column),
                    "text_alignment": text_alignment,
                }
                if matching_spans:
                    cell["font"] = _get_font_properties(matching_spans[0])
                cells.append(cell)

            rows.append({"row_index": row_index, "cells": cells})

        if any(cell["original_text"].strip() for row in rows for cell in row["cells"]):
            elements.append(
                {
                    "id": element_id,
                    "type": "table",
                    "bbox": table_bbox,
                    "rows_count": table.row_count,
                    "columns_count": table.col_count,
                    "rows": rows,
                }
            )
            element_id += 1

    return elements, table_bounds


# =========================================================
# MAIN EXTRACTOR
# =========================================================

def extract_native_pdf_to_json(file_path, json_path):
    document = fitz.open(file_path)

    image_output_directory = os.path.join(
        os.path.dirname(json_path),
        f"{os.path.splitext(os.path.basename(json_path))[0]}_images"
    )

    all_images = extract_native_pdf_images(
        document,
        image_output_directory
    )

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
            underlines = _underline_lines(page)

            # ---- TABLES ----
            table_elements, table_bounds = _extract_tables(
                page, page_dict, element_id
            )
            page_data["elements"].extend(table_elements)
            element_id += len(table_elements)

            # ---- TEXT ----
            for block in page_dict.get("blocks", []):

                if block.get("type") != 0:
                    continue

                block_bbox = block.get("bbox")
                if block_bbox and any(
                    tb[0] <= (block_bbox[0] + block_bbox[2]) / 2 <= tb[2]
                    and tb[1] <= (block_bbox[1] + block_bbox[3]) / 2 <= tb[3]
                    for tb in table_bounds
                ):
                    continue

                block_number = block.get("number")

                # har bullet-line se naya paragraph
                paragraphs = []
                current = None

                for line in block.get("lines", []):
                    spans = [
                        s for s in line.get("spans", [])
                        if s.get("text", "").strip()
                    ]
                    if not spans:
                        continue

                    first = spans[0]
                    bullet = None

                    if first["text"].strip() in BULLETS:
                        bullet, spans = first, spans[1:]
                    else:
                        b, rest = _split_inline_bullet(first)
                        if b is not None:
                            bullet, spans = b, [rest] + spans[1:]

                    if bullet is not None or current is None:
                        current = {"bullet": bullet, "lines": []}
                        paragraphs.append(current)

                    if spans:
                        current["lines"].append(spans)

                for para in paragraphs:
                    if para["bullet"] is not None:
                        bs = para["bullet"]
                        page_data["elements"].append(
                            _make_element(
                                element_id,
                                bs["text"].strip(),
                                [bs],
                                block_number,
                                _span_font(bs, underlines),
                            )
                        )
                        element_id += 1
                    if not para["lines"]:
                        continue

                    segments = _build_segments(para["lines"], underlines)
                    full_text = _clean(" ".join(s["text"] for s in segments))
                    if not full_text:
                        continue

                    all_spans = [s for spans in para["lines"] for s in spans]
                    page_data["elements"].append(
                        _make_element(
                            element_id,
                            full_text,
                            all_spans,
                            block_number,
                            segments[-1]["font"],
                            segments,
                        )
                    )
                    element_id += 1

            page_data["images"] = [
                image
                for image in all_images
                if image["page_number"] == page_index + 1
            ]

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