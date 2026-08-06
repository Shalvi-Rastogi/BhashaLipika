from docx import Document
from app.extractors.Docx.document_parser import parse_document
import json
import os

doc_path = input("Enter DOCX file path: ")

document = Document(doc_path)

result = parse_document(doc_path, document)

# Create outputs folder
os.makedirs("outputs", exist_ok=True)

# Create JSON filename from DOCX filename
json_filename = os.path.splitext(os.path.basename(doc_path))[0] + ".json"
json_path = os.path.join("outputs", json_filename)

# Save JSON
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=4, ensure_ascii=False)

print(f"Unified JSON saved successfully at: {json_path}")