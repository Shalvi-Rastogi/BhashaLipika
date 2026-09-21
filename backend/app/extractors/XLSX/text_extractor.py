from .utils import is_text_cell

def extract_cell_text(cell):
    # Hum sirf strings ko extract karenge taaki numbers ya dates disturb na hon
    if is_text_cell(cell):
        return str(cell.value).strip()
    return ""