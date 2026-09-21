import json
import openpyxl
from openpyxl.styles import Font

def reconstruct_xlsx(original_file_path, translated_json_path, output_file_path):
    wb = openpyxl.load_workbook(original_file_path)
    
    with open(translated_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for sheet_data in data.get("sheets", []):
        sheet_name = sheet_data.get("sheet_name")
        
        if sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            
            for cell_info in sheet_data.get("cells", []):
                coord = cell_info.get("coordinate")
                # Pehle translated text lijiye
                new_text = cell_info.get("translated_text", cell_info.get("text", ""))
                
                if coord and new_text:
                    # 1. Text ko update karein
                    sheet[coord].value = new_text
                    
                    # 2. Style ko explicitly wapas lagayein
                    runs = cell_info.get("runs", [])
                    if runs and len(runs) > 0:
                        style = runs[0].get("style", {})
                        
                        font_kwargs = {}
                        if style.get("font_name") is not None:
                            font_kwargs["name"] = style.get("font_name")
                        if style.get("font_size") is not None:
                            font_kwargs["size"] = style.get("font_size")
                        if style.get("bold") is not None:
                            font_kwargs["bold"] = style.get("bold")
                        if style.get("italic") is not None:
                            font_kwargs["italic"] = style.get("italic")
                        if style.get("strike") is not None:
                            font_kwargs["strikethrough"] = style.get("strike")
                        if style.get("underline"):
                            font_kwargs["underline"] = "single"
                            
                        # Agar JSON me style parameters hain toh Font object apply karo
                        if font_kwargs:
                            # Current color preserve karne ki koshish
                            current_font = sheet[coord].font
                            if current_font and current_font.color:
                                font_kwargs["color"] = current_font.color
                                
                            sheet[coord].font = Font(**font_kwargs)
                            
    wb.save(output_file_path)
    wb.close()