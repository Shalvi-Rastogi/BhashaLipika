from app.extractors.Docx.image_extractor import extract_images_from_docx

result = extract_images_from_docx("uploads/sample_with_image.docx")

print(result)