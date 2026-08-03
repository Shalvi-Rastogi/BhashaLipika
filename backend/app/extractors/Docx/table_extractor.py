from docx.table import Table

from .style_extractor import extract_run_style
from .utils import get_alignment


def _extract_cell_paragraphs(cell):
    """Return the text and formatting of each paragraph in a table cell."""
    paragraphs = []

    for paragraph in cell.paragraphs:
        runs = [
            {
                "text": run.text,
                "style": extract_run_style(run),
            }
            for run in paragraph.runs
            if run.text
        ]

        # Keep empty paragraphs too: they can be meaningful inside a table cell.
        paragraphs.append(
            {
                "text": paragraph.text,
                "runs": runs,
                "paragraph_style": {
                    "style_name": paragraph.style.name if paragraph.style else "Normal",
                    "alignment": get_alignment(paragraph.alignment),
                },
            }
        )

    return paragraphs


def process_table(block, element_id):
    """Convert one DOCX table into the same intermediate element format as text."""
    if not isinstance(block, Table):
        return None

    cells = []
    seen_cells = set()

    for row_index, row in enumerate(block.rows):
        for column_index, cell in enumerate(row.cells):
            # python-docx exposes merged cells more than once in ``row.cells``.
            # Store the actual cell once, while retaining its first grid position.
            cell_key = id(cell._tc)
            if cell_key in seen_cells:
                continue
            seen_cells.add(cell_key)

            cells.append(
                {
                    "row": row_index,
                    "column": column_index,
                    "text": cell.text,
                    "paragraphs": _extract_cell_paragraphs(cell),
                }
            )

    return {
        "id": element_id,
        "type": "table",
        "level": None,
        "order": element_id,
        "rows": len(block.rows),
        "columns": len(block.columns),
        "cells": cells,
    }


def extract_tables(document):
    """Backward-compatible helper for callers that need all tables only."""
    return [
        process_table(table, table_id)
        for table_id, table in enumerate(document.tables, start=1)
    ]
