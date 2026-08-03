import easyocr

reader = easyocr.Reader(['en'])

def extract_text_from_image(image_path):
    try:
        results = reader.readtext(image_path)

        extracted = []

        for result in results:
            extracted.append({
                "text": result[1],
                "confidence": result[2]
            })

        return extracted

    except Exception as e:
        print(f"OCR failed for {image_path}: {e}")
        return []