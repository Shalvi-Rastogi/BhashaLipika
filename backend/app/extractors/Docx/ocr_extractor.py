import threading

import easyocr

reader = easyocr.Reader(['en'], gpu=False)
_reader_cache = {("en",): reader}
_reader_lock = threading.Lock()


def _get_reader(languages):
    if languages is None:
        languages = ("en",)
    elif isinstance(languages, str):
        languages = (languages,)
    else:
        languages = tuple(languages)

    languages = tuple(dict.fromkeys(languages))
    if not languages:
        languages = ("en",)

    with _reader_lock:
        if languages not in _reader_cache:
            _reader_cache[languages] = easyocr.Reader(
                list(languages),
                gpu=False,
                verbose=False
            )
        return _reader_cache[languages]


def extract_text_from_image(image_path, languages=None):
    image_reader = _get_reader(languages)

    try:
        results = image_reader.readtext(image_path)

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