from docx import Document
from app.extractors.Docx.document_parser import parse_document
import json

doc_path = input("Enter DOCX file path: ")

document = Document(doc_path)

result = parse_document(doc_path, document)

print(json.dumps(result, indent=4))