from docx.table import Table

from .style_extractor import extract_run_style
from .utils import get_alignment


def _extract_cell_paragraphs(cell):
    """
    Extract all paragraphs inside a table cell,
    including paragraph formatting and run formatting.
    """

    paragraphs = []

    for paragraph_index, paragraph in enumerate(cell.paragraphs):

        runs = []

        for run_index, run in enumerate(paragraph.runs):

            # Keep empty runs out of translated text
            if not run.text:
                continue

            runs.append(
                {
                    "run_index": run_index,
                    "text": run.text,
                    "style": extract_run_style(run),
                }
            )

        paragraphs.append(
            {
                "paragraph_index": paragraph_index,
                "text": paragraph.text,
                "runs": runs,
                "paragraph_style": {
                    "style_name": (
                        paragraph.style.name
                        if paragraph.style
                        else "Normal"
                    ),
                    "alignment": get_alignment(
                        paragraph.alignment
                    ),
                },
            }
        )

    return paragraphs


def _extract_cell(cell, row_index, column_index):
    """
    Extract one table cell.
    """

    paragraphs = _extract_cell_paragraphs(cell)

    return {
        "cell_index": column_index,
        "row": row_index,
        "column": column_index,

        # This is the text that translation API can use
        "text": cell.text,

        # Keep original text for reconstruction/debugging
        "original_text": cell.text,

        # Preserve paragraph/run structure
        "paragraphs": paragraphs,
    }


def process_table(block, element_id):
    """
    Convert one DOCX table into structured JSON.

    Structure:

        table
          └── rows
                └── cells
                      └── paragraphs
                            └── runs
    """

    if not isinstance(block, Table):
        return None

    rows = []

    for row_index, row in enumerate(block.rows):

        row_data = {
            "row_index": row_index,
            "cells": []
        }

        for column_index, cell in enumerate(row.cells):

            cell_data = _extract_cell(
                cell,
                row_index,
                column_index
            )

            row_data["cells"].append(cell_data)

        rows.append(row_data)

    return {
        "id": element_id,
        "type": "table",
        "level": None,
        "order": element_id,

        "rows_count": len(block.rows),
        "columns_count": len(block.columns),

        "rows": rows,
    }


def extract_tables(document):
    """
    Backward-compatible helper for callers
    that need all tables only.
    """

    tables = []

    for table_id, table in enumerate(
        document.tables,
        start=1
    ):

        table_data = process_table(
            table,
            table_id
        )

        if table_data is not None:
            tables.append(table_data)

    return tables