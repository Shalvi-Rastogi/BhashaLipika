import os
import win32com.client as win32

def convert_rtf_to_docx(rtf_path: str, output_dir: str) -> str:
    """RTF file ko DOCX me convert karta hai"""
    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    
    rtf_path = os.path.abspath(rtf_path)
    filename = os.path.basename(rtf_path)
    stem = os.path.splitext(filename)[0]
    
    docx_path = os.path.abspath(os.path.join(output_dir, f"{stem}.docx"))
    
    try:
        doc = word.Documents.Open(rtf_path)
        doc.SaveAs2(docx_path, FileFormat=16) # 16 is for DOCX
        doc.Close()
    except Exception as e:
        print(f"Error converting RTF to DOCX: {e}")
        raise e
    finally:
        word.Quit()
        
    return docx_path


def convert_docx_to_rtf(docx_path: str, output_dir: str) -> str:
    """Translated DOCX file ko wapas RTF me convert karta hai"""
    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    
    docx_path = os.path.abspath(docx_path)
    filename = os.path.basename(docx_path)
    stem = os.path.splitext(filename)[0]
    
    rtf_path = os.path.abspath(os.path.join(output_dir, f"{stem}.rtf"))
    
    try:
        doc = word.Documents.Open(docx_path)
        doc.SaveAs2(rtf_path, FileFormat=6) # 6 is for RTF
        doc.Close()
    except Exception as e:
        print(f"Error converting DOCX to RTF: {e}")
        raise e
    finally:
        word.Quit()
        
    return rtf_path