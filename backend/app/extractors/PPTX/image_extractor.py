import os
from app.extractors.Docx.ocr_extractor import extract_text_from_image


# def extract_image(shape, shape_index, slide_number, output_dir):
#     """Extract image from PPT and run OCR on the image."""

#     try:
#         image = shape.image
#         image_bytes = image.blob
#         image_ext = image.ext

#         image_filename = f"slide_{slide_number}_shape_{shape_index}.{image_ext}"
#         image_path = os.path.join(output_dir, image_filename)

#         # Save image
#         with open(image_path, "wb") as f:
#             f.write(image_bytes)

#         # Run OCR
#         ocr_results = extract_text_from_image(image_path)

#         # Extract detected text
#         extracted_text = "\n".join(
#             item["text"] for item in ocr_results if item.get("text")
#         )

#         return {
#             "shape_index": shape_index,
#             "type": "image",
#             "image_path": image_path,

#             # OCR information
#             "original_text": extracted_text,
#             "ocr_data": ocr_results,

#             # Will be filled after translation
#             "translated_text": ""
#         }

#     except Exception as e:
#         print(
#             f"Error extracting image at slide "
#             f"{slide_number}, shape {shape_index}: {e}"
#         )
#         return None
def extract_image(shape, shape_index, slide_number, output_dir):
    """Extract image from PPT and run OCR on the image."""

    try:
        image = shape.image
        image_bytes = image.blob
        image_ext = image.ext

        image_filename = f"slide_{slide_number}_shape_{shape_index}.{image_ext}"
        image_path = os.path.join(output_dir, image_filename)

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        print(f"[PPTX IMAGE SAVED] {image_path}")

        ocr_results = extract_text_from_image(image_path)

        print(f"[PPTX IMAGE SAVED] {image_path}")
        print(f"[PPTX OCR RESULTS] {ocr_results}")

        print(f"[PPTX OCR RESULTS] {ocr_results}")

        extracted_text = "\n".join(
            item["text"] for item in ocr_results if item.get("text")
        )

        return {
            "shape_index": shape_index,
            "type": "image",
            "image_path": image_path,
            "original_text": extracted_text,
            "ocr_data": ocr_results,
            "translated_text": ""
        }

    except Exception as e:
        print(
            f"Error extracting image at slide "
            f"{slide_number}, shape {shape_index}: {e}"
        )
        return None