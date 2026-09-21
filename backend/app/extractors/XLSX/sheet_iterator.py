import json
import openpyxl
from .text_extractor import extract_cell_text
from .style_extractor import extract_cell_style

def extract_xlsx_to_json(file_path, json_path):
    wb = openpyxl.load_workbook(file_path, data_only=True)
    
    document_data = {
        "document_name": file_path.split('/')[-1].split('\\')[-1],
        "document_type": "xlsx",
        "sheets": []
    }
    
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        sheet_data = {
            "type": "sheet",
            "sheet_name": sheet_name,
            "cells": []
        }
        
        for row in sheet.iter_rows():
            for cell in row:
                text = extract_cell_text(cell)
                if text:
                    style = extract_cell_style(cell)
                    # DOCX ke format jaisa rich structure
                    cell_info = {
                        "type": "cell",
                        "coordinate": cell.coordinate,
                        "row": cell.row,
                        "column": cell.column,
                        "text": text,
                        "runs": [
                            {
                                "text": text,
                                "style": style
                            }
                        ]
                    }
                    sheet_data["cells"].append(cell_info)
        
        document_data["sheets"].append(sheet_data)
            
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(document_data, f, indent=4, ensure_ascii=False)
        
    wb.close()
    return document_data