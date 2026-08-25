import easyocr

reader = easyocr.Reader(['en'], gpu=False)


def extract_text_from_image(image_path):
    try:
        results = reader.readtext(image_path)

        extracted = []

        for result in results:

            # EasyOCR bounding box
            bbox = result[0]

            extracted.append({
                "text": str(result[1]),
                "confidence": float(result[2]),

                # Convert NumPy int32 → normal Python int
                "bbox": [
                    [int(point[0]), int(point[1])]
                    for point in bbox
                ]
            })

        return extracted

    except Exception as e:
        print(f"OCR failed for {image_path}: {e}")
        return []