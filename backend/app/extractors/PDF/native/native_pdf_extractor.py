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
            }

            page_dict = page.get_text("dict")
            table_elements, table_bounds = _extract_tables(
                page, page_dict, element_id
            )
            page_data["elements"].extend(table_elements)
            element_id += len(table_elements)

            for block in page_dict.get("blocks", []):

                if block.get("type") != 0:
                    continue

                block_bbox = block.get("bbox")
                if block_bbox and any(
                    table_bbox[0] <= (block_bbox[0] + block_bbox[2]) / 2 <= table_bbox[2]
                    and table_bbox[1] <= (block_bbox[1] + block_bbox[3]) / 2 <= table_bbox[3]
                    for table_bbox in table_bounds
                ):
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