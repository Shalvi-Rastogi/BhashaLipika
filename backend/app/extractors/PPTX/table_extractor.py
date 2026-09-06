def extract_table_data(shape, shape_index):
    """Extracts tabular data from a PowerPoint table shape."""
    table_data = []
    for row in shape.table.rows:
        row_content = []
        for cell in row.cells:
            row_content.append(cell.text_frame.text.strip())
        table_data.append(row_content)
    
    if table_data:
        return {
            "shape_index": shape_index,
            "type": "table",
            "original_data": table_data,
            "translated_data": []
        }
    return None