def is_text_cell(cell):
    """Check if the cell contains actual text/string, not numbers or dates."""
    # openpyxl me 's' ka matlab string hota hai
    if cell.data_type == 's' and cell.value:
        return True
    return False